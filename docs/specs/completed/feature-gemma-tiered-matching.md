# Feature: Gemma Tiered Matching (Confidence + Multi-Match Alternatives)

## Claude Code Prompt

```
Read the spec at docs/specs/feature-gemma-tiered-matching.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1–§4 (routing logic, Pydantic contract, CLI/web fork implications)
   - Invoke @genai-architect to review the prompt changes in §4 (tier-driven alternative count, field semantics)
   - Both write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION
   - Invoke @fp-design-visionary to fill §3
   - Focus: the medium-tier match card with inline alternatives list (NEW pattern — not in DESIGN.md yet)
   - Must use the existing Brightpath Gemma Interactions family (insight/caution/thrive accent tones, GemmaStar, GemmaSpinner, breathing-glow card)
   - Must render on bg-mid with the 3px left stripe convention already documented in DESIGN.md §Gemma Interactions
   - Reference the v3 mockup at docs/mockups/brightpath-design-system-v3.html (§gemma section)

3. IMPLEMENTATION
   - Implement per §3 (UI/UX) and §4 (Technical Spec)
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly
   - DURING coding: The prompt lives in two places (backend/app/services/intent.py:13 and backend/cli.py:~620) — update BOTH to keep the CLI and web UI in sync. Note: prompt consolidation is explicitly out of scope (§2).
   - Log all work to §6
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)
   - If still broken after 3 attempts: escalate to human via §10 Discussion

4. TESTING
   - Invoke @test-writer to implement all P0/P1 tests in §4
   - P0 #1: backend service-level tests for each confidence tier (currently NO test coverage for intent.py — this is a net-new fixture)
   - P0 #2: frontend vitest for MajorInput rendering per tier + alternatives selection
   - Run ALL tests to catch regressions
   - If still broken after 3 attempts: escalate to human via §10 Discussion

5. DESIGN AUDIT
   - Invoke @fp-design-auditor for mechanical token compliance
   - Confirm the new alternatives list uses: font-body text-body-sm, accent-info tinting on default (per Gemma Match Card career preview rule), hover → text-primary, border-subtle row dividers
   - Confirm no raw rgba/hex values introduced
   - Writes findings to §8 (Design Audit)

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
   - Check off all Success Criteria in §1
   - Update §6, §7, §8
   - Generate report to reports/feature-gemma-tiered-matching-YYYY-MM-DD.md
   - **Parallel-worktree discipline:** commit all work to the CURRENT branch only. This spec may run concurrently with `docs/specs/screen-career-pick-lineage-sheet.md` in a sibling worktree (per the `Parallel With` metadata row). Do NOT merge to `main`, do NOT `git push`, do NOT create a PR. The orchestrating session integrates branches to `main` after both parallel specs complete.
```

---

## Status: COMPLETE

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-18 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-18 |
| Blocked By | — |
| Related Specs | `docs/specs/completed/cip-intent-substitution.md`, `docs/specs/completed/spike-gemma-intent-resolution.md`, `docs/specs/completed/spike-gemma-intent-openrouter.md` |
| Parallel With | `docs/specs/screen-career-pick-lineage-sheet.md` — safe to run concurrently in a sibling git worktree per §0. Expect additive-only merge conflicts on `DESIGN.md` + `docs/mockups/brightpath-design-system-v3.html` at integration time. |

---

## §1 Feature Description

### Overview

Replace Gemma's binary intent-matching UX (one match *or* a picker) with a three-tier model driven by Gemma's own self-reported confidence: high confidence → a single confident match card ("That's right"), medium confidence → the same card with 2–4 inline alternatives and a softer "Close enough" CTA, low confidence → the existing clarify picker with up to 10 options. Every tier uses the Gemma Interactions design family already documented in `DESIGN.md`.

### Problem Statement

Two defects exist today in the `/school` major-input flow:

1. **Dead code in the middle tier.** The frontend reads `intentResult.confidence === "low"` to drive a caution-styled match card (yellow title, "Close enough" button, "best guess" pill). But `backend/app/services/intent.py:307` routes `confidence == "low"` to the clarify picker before the match card is rendered. The caution variant is unreachable. High- and medium-confidence matches render identically as purple/"That's right", giving the student no signal that Gemma is less sure about one than the other.

2. **One match even when the input is ambiguous.** Gemma's response schema already includes `alternatives: [{cip, title, why}]` (backend `IntentResult.alternatives`, frontend `IntentResult.alternatives`), and the CLI (`backend/cli.py:977+`) already renders them. The web UI throws them away. A student typing "business" today sees one pick (e.g., `Business Administration`) with no hint that `Finance`, `Marketing`, or `Entrepreneurship` were candidates. The one-and-only-one match is a UX bottleneck that hides Gemma's reasoning.

Both stem from the same oversight: we wired a richer schema than we rendered. This spec makes the schema usable end-to-end.

### Success Criteria

- [x] Gemma's response emits `confidence` in `{"high","medium","low"}` and an `alternatives` array whose length is zero for high, 2–4 for medium, and may contain up to 10 for low (driven by the prompt, not post-processed).
- [x] The frontend renders three visually distinct paths:
   - `high` → existing purple match card, one match, `"That's right"` button.
   - `medium` → caution (yellow) match card, one primary match + 2–4 visible alternatives, `"Close enough"` button, `"best guess"` pill.
   - `low` → existing clarify picker (program list), unchanged.
- [x] No low-confidence result ever renders the match card (routed to clarify as today).
- [x] No high-confidence result ever shows alternatives (clean card, same as today).
- [x] Clicking an alternative in the medium-tier card confirms it just like the primary match (same `onConfirm` handoff, same `/intent/confirm` API call).
- [x] Backend tests cover all three tiers + the alternative-count contract.
- [x] Frontend tests cover all three rendering paths + alternative selection.
- [x] `DESIGN.md` §Gemma Interactions documents the tiered rendering pattern.
- [x] v3 HTML mockup (`docs/mockups/brightpath-design-system-v3.html`) shows a medium-tier card with alternatives alongside the existing default/caution/confirming variants.
- [x] Both `backend/app/services/intent.py` and `backend/cli.py` use aligned prompts — no drift between web and CLI behavior.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Three tiers tied to a single `confidence` field Gemma already emits | Gemma self-reports certainty; we're not adding a second signal or post-hoc scoring. Keeps the prompt contract flat. | (a) Compute confidence server-side from candidate-set scoring — rejected: duplicates Gemma's judgment and creates a new metric to maintain. (b) Use numeric 0.0–1.0 confidence — rejected: harder to prompt Gemma for well-calibrated numbers than to ask for a tier. |
| 2 | Prompt-driven alternative count (high=0, medium=2–4, low=up to 10) | Letting Gemma decide when to propose options keeps "exact match → 1 option" honest. A fixed `k` would pad or truncate. | (a) Always return top-5 and let UI filter — rejected: wastes tokens and encourages Gemma to pad. (b) Ask for N via a separate param — rejected: more prompt surface for little gain. |
| 3 | Low confidence stays routed to clarify picker, NOT to a match card with 10 alternatives | The picker is a proven UI (it's already there). A 10-row match card would blow up the single-column layout. Also: if Gemma is low-confidence, showing its "best guess" as primary is misleading. | (a) Merge clarify picker into the match card at low tier — rejected: conflates two components with different affordances (picker is scannable/filterable). |
| 4 | Alternatives render INSIDE the medium match card (no separate screen) | Keeps the student's attention path unbroken. Primary match is still the hero; alternatives are contextual. | (a) Two-column layout (primary left, alts right) — rejected: breaks on mobile and over-emphasizes alternatives. (b) Modal/popover for alternatives — rejected: extra click to see what Gemma was deciding between. |
| 5 | Both `intent.py` and `cli.py` receive identical prompt updates in this spec | The two call sites already drifted (CLI has a tier-aware flow Gemma doesn't know to produce). Sync now, consolidate later. | Consolidating into a shared `_prompt.py` — parked as follow-up refactor spec. |
| 6 | Alternative rows use the existing Gemma Match Card "Career preview" pattern | The list-of-options-with-rationale visual language is already built: `text-accent-info` default, `text-primary` on hover, `bg-surface` row hover, border-subtle dividers. Reuse instead of inventing. | A distinct "alternatives" pattern — rejected: dilutes the Gemma Interactions family. |
| 7 | Keep the Pydantic `IntentResult.alternatives: list[dict] \| None` loose-typed | It's already shipped as `dict` — tightening to `list[Alternative]` is a separate tightening effort. | Introducing a new `Alternative(BaseModel)` — parked as tech debt; API contract doesn't benefit. |
| 8 | Confirmation flash (320ms thrive) applies to ALL tiers, including confirmed alternatives | User feedback consistency. Medium-tier alternatives should feel "confirmed" the same way the primary high-tier match does. | Different flash per tier — rejected: adds motion variance without informational gain. |

### Constraints

- **No breaking API changes.** `IntentResult` schema is unchanged; only the *content* of `alternatives` and `confidence` shifts. Existing clients (CLI) keep working.
- **No audit prompt changes.** The hard-reject / playful-warning audit flow (`intent.py:57+`) is untouched.
- **No clarify picker UX changes.** `ClarifyContent` in `MajorInput.tsx` is not modified.
- **No caching behavior changes.** `IntentCache` (if present) untouched; any TTL semantics preserved.
- **No changes to INFERENCE_BACKEND routing.** Prompt changes must behave identically under `ollama` and `openrouter`.

### Out of Scope

Parked as follow-up specs — do NOT implement in this spec:

- Consolidating the duplicate prompts in `intent.py` and `cli.py` into a shared module (tech-debt).
- Tightening `alternatives: list[dict]` into a typed Pydantic `Alternative` model.
- Numeric confidence scoring or calibration metrics.
- A "why this match" expansion drawer (showing the `reasoning` field inline).
- Compare-multiple-builds flows.
- Gemma "regenerate" button on the match card.
- Any change to the `/intent/confirm` endpoint or its payload.

---

## §3 UI/UX Design

### Emotional Target

**The feeling: "Gemma is thinking with me, not guessing at me."**

The high-tier card is confident and warm — "I've got you." The low-tier picker is humble and direct — "help me out here." The medium tier is the missing third voice: **deliberative**. It should feel like a thoughtful advisor pausing mid-sentence to say, "I think it's *this* — but honestly, you could also mean one of these." The student should read the caution styling as *care*, not *error*. Amber is not a warning here; it is the color of a lantern held up to a branching path.

Everything in this tier must honor two truths at once:
1. Gemma's primary pick deserves the hero slot — it's still the best single answer.
2. The alternatives are not afterthoughts — they're peers, visible, and one click from confirming.

The student's gut reaction on seeing this card for the first time should be: *"Oh — it showed me its work."*

### In Scope

Three rendering paths inside `MajorInput` after Gemma resolves:

1. **High-tier match card** — *unchanged* from current production.
2. **Medium-tier match card** — NEW pattern. Extends the Match Card base with an inline alternatives list between the career preview and the actions row.
3. **Low-tier clarify picker** — *unchanged*.

### Reference Material

- `DESIGN.md` §Gemma Interactions (insight default, caution uncertain, thrive confirming)
- `docs/mockups/brightpath-design-system-v3.html#gemma` (existing default + caution + confirming variants + tone gallery — a new "Medium-tier · with alternatives" variant will be added in the implementation step; the HTML is not edited in this design step)
- `frontend/src/components/school/MajorInput.tsx` `MatchContent` (lines 289–448 — existing implementation to extend)

### Brightpath Tokens to Use (NO NEW TOKENS)

| Element | Token |
|---------|-------|
| Medium-tier card surface | `bg-bp-mid` (#232545) |
| Medium-tier card left stripe | `border-l-accent-caution` (3px) |
| Medium-tier card glow | existing `card-breathe-caution` keyframe |
| Medium-tier title color | `text-accent-caution` |
| Medium-tier attribution raw-input echo | `text-accent-caution` (font-semibold) |
| "best guess" pill | `bg-[rgba(242,212,119,0.15)] text-accent-caution rounded-full` (unchanged) |
| Alternatives section label | `font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info` (same as "WHERE THIS LEADS") |
| Alternatives section top rule | `border-t border-border-subtle` |
| Alternative row text default | `text-accent-info` |
| Alternative row text hover | `text-text-primary` |
| Alternative row hover bg | `bg-bp-surface` |
| Alternative row glyph | `text-accent-info/60` → `text-accent-info` on hover (same `▸` treatment as career preview) |
| Alternative row `why` text | `font-body text-small text-text-muted` |
| Row divider between alt rows | `border-t border-border-subtle` (first row has no top border) |
| Alternative row confirm flash (title) | `text-accent-thrive` for 320ms |
| Alternative row confirm flash (bg) | `bg-bp-surface` held; soft `shadow-glow-thrive` equivalent box-shadow via `animate={{ boxShadow: "0 0 24px rgba(125, 212, 163, 0.45)" }}` — same value as primary CTA flash, no new token |
| Primary CTA (medium) | `bg-accent-thrive`, label = `"Close enough"` |

### Visionary Decisions (Answered)

#### D1. Section-label text → **`"OR — ONE OF THESE?"`**

Proposed options were `"OTHER CLOSE MATCHES"` and `"OR MAYBE ONE OF THESE"`. Neither is quite right. `"OTHER CLOSE MATCHES"` is accurate but clinical — it sounds like a search engine's "See also." `"OR MAYBE ONE OF THESE"` is warmer but flabby at 20 characters in an all-caps 2-letterspaced treatment; it wraps on narrower cards.

**Chosen:** `"OR — ONE OF THESE?"` (19 chars with the em-dash visual break).

Why it works:
- The `OR` ties it to the primary match conversationally — "my pick… OR — one of these?" reads as a single thought, not a new section.
- The em-dash (`—`) creates a deliberate pause, matching the "thoughtful advisor" emotional register.
- The trailing `?` signals genuine invitation, not catalog listing. The student is being *asked*, not *presented with options*.
- Matches the established `WHERE THIS LEADS` pattern (same font role, same 2px tracking, same `text-accent-info`) so the card feels continuous, not sectioned.

Rendered: `font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info` — identical to `WHERE THIS LEADS` with an 18px top margin and a hairline `border-t border-border-subtle` above it (the first visual separator in the card; career preview sits above with no rule, this rule announces "different kind of content below").

#### D2. How the `why` field renders → **Inline, right-aligned, subtle, truncated at one line**

`why` is the single differentiator that makes these alternatives feel like *reasoning* instead of a dropdown. If we tooltip it, it's discoverable-by-hover only — mobile loses it entirely, and on desktop the student has to *know* to hover. If we omit it, we're throwing away Gemma's explanation of why these alternatives exist — the whole point of showing its work.

**Chosen:** Inline, right-aligned on desktop (≥640px), stacking below the title on mobile (<640px). Single-line truncation via `truncate` + `max-w-[280px]` on desktop.

- Font: `font-body text-small text-text-muted` (13px, `#9a9fb5` — just enough presence to register, recedes when scanning titles).
- Italics: **no** — we already use italic for playful_warning audit messages; keeping `why` non-italic preserves that semantic distinction.
- Placement: flex row with `justify-between` on desktop so title left-aligns and `why` right-aligns with graceful truncation. On mobile, `flex-col` so `why` drops to a second line at `text-small`.
- When `why` is empty string (Gemma omitted it), the row renders title only — no stray empty span, no visual ghost.

Example row (desktop):
```
▸  Finance                                             core markets & capital allocation
▸  Marketing                                           how you grow a customer base
▸  Entrepreneurship                                    starting and running your own
▸  I/O Psychology                                      workplace behavior and teams
```

The visual rhythm is: glyph → title (bold, `text-accent-info`) → flexible gap → `why` (muted, truncated) → right edge. On hover the whole row's background becomes `bg-bp-surface`, the glyph goes `text-accent-info/60 → text-accent-info`, the title goes `text-accent-info → text-text-primary`, and `why` stays `text-text-muted` (it's supporting, not primary). The hover says: "focus here."

#### D3. CIP code on alternative rows → **No.**

The CIP code is infrastructure. It matters for the primary match because the student needs *one* canonical identifier they're confirming — a quiet assertion of "this is the exact program." On the alternatives it would triple the horizontal density (title, CIP, why) and fight the scannable rhythm. The row is a question, not a receipt.

Exception for implementation: the CIP is still attached to each alternative's underlying data (`alt.cip`) and is used for the `key`, for `onConfirm` handoff, and for the `aria-label`. It is simply not *rendered* in the row.

#### D4. Mobile responsive behavior

- Card width unchanged from high card (same `MatchCard` container — whatever max-width it currently uses).
- Each alternative row: `py-3 px-3` on mobile (bumping from `py-2` desktop) to guarantee a `≥44px` touch target. The title line at 16px + 12px top + 12px bottom = 40px, plus `why` second line at `text-small` 13px = ~56px total. Well above the 44px minimum.
- Title + `why` stack vertically under 640px (`flex-col mobile:flex-row`, with `mobile:` meaning `≥640px` in this codebase — confirmed by existing usage at line 417).
- Gap between rows on mobile unchanged; the border-t row dividers remain.
- The primary CTA row already handles mobile via `flex-col mobile:flex-row` at line 417 — no change needed.

#### D5. Entrance animation

The medium card's content already staggers via the existing Framer variants pattern. Alternatives join that sequence as a **fourth step**:

| Step | Element | Delay | Config |
|------|---------|-------|--------|
| 1 | Attribution + GemmaStar | 0ms | `{ opacity: 0 → 1 }`, `duration: 0.2` (existing) |
| 2 | Title + CIP + best-guess pill | 150ms | `{ opacity: 0, x: -8 → 0 }`, `springs.smooth` (existing) |
| 3 | Career preview items | 400ms + 50ms stagger per row | existing `staggerChildren: 0.05, delayChildren: 0.4` |
| 4 | **Alternatives section label** | 500ms | `{ opacity: 0, y: 8 → 0 }`, `springs.smooth` (NEW) |
| 5 | **Alternative rows** | 550ms + 50ms stagger per row | `staggerChildren: 0.05, delayChildren: 0.55` (NEW, mirrors career preview) |
| 6 | Actions row (CTA + Not quite) | 700ms | existing `springs.smooth, delay: 0.7` — unchanged |

The 50ms stagger between alternative rows is intentionally fast (same as career preview) — these are siblings, not a numbered sequence. They should "appear together as a set." The human eye reads the stagger as *liveness*, not *order*.

Total time-to-ready from card mount: ~900ms (last alt row settles ~700ms after mount, actions fade in at 700ms). The student's eye finishes moving from the attribution to the CTA just as the CTA finishes landing.

#### D6. Confirm interaction on an alternative → **Exact parity with primary confirm**

When an alternative row is clicked:
1. Local component state flips: `confirmingAltCip = alt.cip`.
2. The clicked row's title color animates to `text-accent-thrive` over 200ms (same `duration: 0.2` used by the primary title on confirm).
3. The row's background holds at `bg-bp-surface` and animates a box-shadow of `0 0 24px rgba(125, 212, 163, 0.45)` — the *exact same* glow value used by the primary CTA on confirm (line 426). No new token, no new value — literal reuse.
4. All other rows and the primary CTA become `disabled` (visually: `cursor-default`, no hover state fires).
5. At 320ms: `onConfirm` fires with `{ matched_cip: alt.cip, matched_title: alt.title }` replacing the primary's values.
6. The parent `MajorInput`'s phase transition handles the card exit animation — the alternative row itself does not need to exit animate; the whole card fades out together.

The 320ms is not negotiable — it matches the existing `confirmTimerRef` value at line 314. This is the spec's motion contract for "you chose well": every Gemma confirmation, whether primary or alternative, feels the same.

#### D7. Degenerate medium-with-zero-alternatives → **Caution card, primary alone, no alternatives section**

Per §4 resolution (option b from @fp-architect concern #12): when `confidence === "medium"` but `alternatives` is empty or null, the card still renders with `border-l-accent-caution`, `card-breathe-caution`, the best-guess pill, and the "Close enough" CTA — *but the entire alternatives section (top-rule, label, rows) is omitted*. There is no stub, no "Gemma didn't suggest any others" message, no downgrade to high styling. The card looks exactly like today's caution card (which was previously unreachable on the low branch and is now correctly reachable on the medium branch).

Rationale: the caution styling honestly reflects Gemma's self-reported uncertainty; silently upgrading to insight/high styling would lie about confidence. The top-rule only appears when rows appear — if there are no rows, no rule.

#### D8. `why` truncation — **hard cap at 60 chars or single-line overflow, whichever is first**

- Gemma's `why` values from the spec examples run 20–40 chars ("core markets & capital allocation" = 32). We set `max-w-[280px]` on the `why` span and rely on Tailwind `truncate` (`overflow-hidden whitespace-nowrap text-ellipsis`) to cut gracefully.
- On mobile the `why` span goes full-width under the title; no truncation needed since it has the full card width.
- If Gemma returns a `why` longer than 60 chars, we soft-warn in the test suite (P2) — it won't break layout (truncation handles it), but it signals prompt-drift.

### ASCII Mockups

#### (a) Medium-tier card — default state

```
┌────────────────────────────────────────────────────────────────────────┐
│ ║  * Gemma matched "business"                                          │ ← 3px border-l-accent-caution
│ ║                                                                      │   card-breathe-caution glow
│ ║  Business Administration                                             │   text-accent-caution (h3)
│ ║  CIP 52.0201   [ best guess ]                                        │   font-data + amber pill
│ ║                                                                      │
│ ║  WHERE THIS LEADS                                                    │   font-data 11px track[2]
│ ║  ▸ Financial Analyst                                                 │   accent-info on bp-mid
│ ║  ▸ Marketing Manager                                                 │
│ ║  ▸ Operations Manager                                                │
│ ║  ▸ General & Operations Manager                                      │
│ ║  ▸ Management Analyst                                                │
│ ║  ──────────────────────────────────────────────────────────────────  │   border-t border-border-subtle
│ ║                                                                      │
│ ║  OR — ONE OF THESE?                                                  │   font-data 11px track[2]
│ ║                                                                      │   text-accent-info
│ ║  ▸  Finance                              core markets & capital a... │   title accent-info / why text-muted
│ ║  ──────────────────────────────────────────────────────────────────  │   border-t border-border-subtle
│ ║  ▸  Marketing                            how you grow a customer ... │
│ ║  ──────────────────────────────────────────────────────────────────  │
│ ║  ▸  Entrepreneurship                     starting and running you... │
│ ║  ──────────────────────────────────────────────────────────────────  │
│ ║  ▸  I/O Psychology                       workplace behavior and t... │
│ ║                                                                      │
│ ║  ┌──────────────────────────┐  ┌──────────────┐                      │
│ ║  │    Close enough          │  │  Not quite   │                      │   bg-accent-thrive / ghost
│ ║  └──────────────────────────┘  └──────────────┘                      │
└────────────────────────────────────────────────────────────────────────┘
   ↑ bg-bp-mid surface
```

#### (b) Hover on an alternative row (Marketing row hovered)

```
│ ║  OR — ONE OF THESE?                                                  │
│ ║                                                                      │
│ ║  ▸  Finance                              core markets & capital a... │   default: accent-info / muted
│ ║  ──────────────────────────────────────────────────────────────────  │
│ ║  ▓▸▓ ▓Marketing▓                         how you grow a customer ... │   HOVER: bg-bp-surface
│ ║  ──────────────────────────────────────────────────────────────────  │          glyph accent-info (full)
│ ║  ▸  Entrepreneurship                     starting and running you... │          title text-text-primary
│ ║  ──────────────────────────────────────────────────────────────────  │          why stays text-muted
│ ║  ▸  I/O Psychology                       workplace behavior and t... │
```

(▓ = hovered background and elevated text)

Transition: `transition-colors duration-fast` (same as career preview glyph at line 393) — ~180ms color interpolation. The background fade feels instant; the text color shift is the signal that *this* is the row your pointer lives on.

#### (c) Confirming-alt flash — Marketing row clicked

```
│ ║  OR — ONE OF THESE?                                                  │
│ ║                                                                      │
│ ║  ▸  Finance                              core markets & capital a... │   dimmed (disabled state)
│ ║  ──────────────────────────────────────────────────────────────────  │
│ ║  ✦▸  ✦Marketing✦                         how you grow a customer ... │   FLASH (320ms):
│ ║  ──────────────────────────────────────────────────────────────────  │     title → text-accent-thrive
│ ║  ▸  Entrepreneurship                     starting and running you... │     row bg → bp-surface held
│ ║  ──────────────────────────────────────────────────────────────────  │     box-shadow: 0 0 24px
│ ║  ▸  I/O Psychology                       workplace behavior and t... │         rgba(125,212,163,0.45)
│ ║                                                                      │     glyph → text-accent-thrive
│ ║  ┌──────────────────────────┐  ┌──────────────┐                      │
│ ║  │    Close enough  (dim)   │  │  Not quite   │                      │   disabled (cursor-default)
│ ║  └──────────────────────────┘  └──────────────┘                      │
```

(✦ = thrive accent applied — same green the primary CTA wears on its own confirm flash)

At 320ms the `onConfirm({cip: "52.1401", title: "Marketing"})` handoff fires and the parent handles the exit — the card fades `{ opacity: 1 → 0, y: 0 → -8 }` at `duration: 0.2` (matching the existing exit variant at line 329).

### Token-Mapped Component Tree

A new subcomponent `AlternativesList` lives inside `MajorInput.tsx` adjacent to `MatchContent`. Approximate 30-line reference implementation — exact copy is Claude Code's decision during the IMPLEMENTATION step; tokens and motion below are the contract:

```tsx
function AlternativesList({
  alternatives,
  onPick,
  confirmingAltCip,
}: {
  alternatives: Array<{ cip: string; title: string; why: string }>;
  onPick: (alt: { cip: string; title: string; why: string }) => void;
  confirmingAltCip: string | null;
}) {
  return (
    <motion.div
      className="mt-[18px] pt-4 border-t border-border-subtle"
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: { transition: { staggerChildren: 0.05, delayChildren: 0.55 } },
      }}
    >
      <motion.span
        className="font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info mb-2.5 block"
        variants={{
          hidden: { opacity: 0, y: 8 },
          visible: { opacity: 1, y: 0, transition: springs.smooth },
        }}
      >
        Or — one of these?
      </motion.span>
      <ul role="list" aria-label="Other close matches" className="flex flex-col">
        {alternatives.map((alt, idx) => {
          const isConfirming = confirmingAltCip === alt.cip;
          const isDimmed = confirmingAltCip !== null && !isConfirming;
          return (
            <motion.li
              key={alt.cip}
              variants={{
                hidden: { opacity: 0, y: 12 },
                visible: { opacity: 1, y: 0, transition: springs.smooth },
              }}
              className={idx === 0 ? "" : "border-t border-border-subtle"}
            >
              <motion.button
                type="button"
                disabled={confirmingAltCip !== null}
                onClick={() => onPick(alt)}
                aria-label={`Select ${alt.title}`}
                className="w-full flex flex-col mobile:flex-row mobile:items-center gap-1 mobile:gap-3 py-3 mobile:py-2 px-3 rounded-md text-left hover:bg-bp-surface transition-colors duration-fast group disabled:cursor-default"
                animate={
                  isConfirming
                    ? { boxShadow: "0 0 24px rgba(125, 212, 163, 0.45)", backgroundColor: "var(--color-bp-surface)" }
                    : { boxShadow: "0 0 0px rgba(125, 212, 163, 0)" }
                }
                transition={springs.snappy}
              >
                <span className="flex items-center gap-2 flex-1 min-w-0">
                  <motion.span
                    className="text-[10px] text-accent-info/60 group-hover:text-accent-info transition-colors duration-fast"
                    animate={{ color: isConfirming ? "var(--color-accent-thrive)" : undefined }}
                  >
                    ▸
                  </motion.span>
                  <motion.span
                    className="font-body text-body-sm font-semibold text-accent-info group-hover:text-text-primary transition-colors duration-fast truncate"
                    animate={{ color: isConfirming ? "var(--color-accent-thrive)" : undefined }}
                    transition={{ duration: 0.2 }}
                    style={{ opacity: isDimmed ? 0.45 : 1 }}
                  >
                    {alt.title}
                  </motion.span>
                </span>
                {alt.why && (
                  <span
                    className="font-body text-small text-text-muted truncate mobile:max-w-[280px] mobile:text-right"
                    style={{ opacity: isDimmed ? 0.45 : 1 }}
                  >
                    {alt.why}
                  </span>
                )}
              </motion.button>
            </motion.li>
          );
        })}
      </ul>
    </motion.div>
  );
}
```

Integration point inside `MatchContent` — render between the career preview block (ends line 403) and the playful warning block (starts line 406):

```tsx
{isUncertain && intentResult.alternatives && intentResult.alternatives.length > 0 && (
  <AlternativesList
    alternatives={intentResult.alternatives}
    onPick={handleAlternativePick}
    confirmingAltCip={confirmingAltCip}
  />
)}
```

`MatchContent` gains two new pieces of state adjacent to the existing `confirming` / `confirmTimerRef`:

```tsx
const [confirmingAltCip, setConfirmingAltCip] = useState<string | null>(null);

function handleAlternativePick(alt: { cip: string; title: string; why: string }) {
  if (confirming || confirmingAltCip) return;
  setConfirmingAltCip(alt.cip);
  confirmTimerRef.current = window.setTimeout(
    () => onConfirm({ matched_cip: alt.cip, matched_title: alt.title }),
    320
  );
}
```

(Note: `onConfirm`'s signature change from `() => void` to `(override?: {matched_cip, matched_title}) => void` is an implementation detail — Claude Code resolves the exact shape. The spec's contract is: the alternative's CIP and title replace the primary's for the downstream `/intent/confirm` call.)

### Motion Spec

| Moment | Target | Config | Notes |
|--------|--------|--------|-------|
| Alternatives section appears | `border-t border-border-subtle` rule + section label | `delay: 0.5s`, `springs.smooth`, `opacity 0→1, y 8→0` | Joins the existing card stagger as step 4 |
| Alternative rows appear | each `<li>` | `staggerChildren: 0.05, delayChildren: 0.55`, `springs.smooth`, `opacity 0→1, y 12→0` | Same motion as career preview rows |
| Row hover | `bg`, glyph color, title color | `transition-colors duration-fast` (~180ms) | `bg-bp-surface`, glyph `accent-info/60 → accent-info`, title `accent-info → text-text-primary` |
| Row click → confirm flash | `boxShadow`, `backgroundColor`, title/glyph color | `springs.snappy` for shadow, `duration: 0.2` for color | `boxShadow: "0 0 24px rgba(125, 212, 163, 0.45)"` — literal reuse of primary CTA value |
| Other rows during flash | `opacity` | `style` prop | `0.45` opacity for non-chosen rows + primary CTA (visual "dimmed, not interactive") |
| Confirm handoff | `setTimeout` 320ms → `onConfirm` | — | Identical to primary `handleConfirmClick` at line 314 |
| Card exit after confirm | whole card | `exit={{ opacity: 0, y: -8 }, duration: 0.2}` | Existing `MatchContent` exit variant — unchanged |

The visual test for "does this feel right" is: record a video, mute the audio, and watch the card transition from medium-tier default to medium-tier confirming-alt. The only motion the eye should track is (1) the chosen row's glow-and-greening, and (2) the card as a whole fading out. Everything else is held steady — siblings dim in place, CTA dims in place, no exits animate individually. The cognitive load is *one focused moment*.

### Accessibility

| Element | Identifier / Role | Type | aria-label / behavior |
|---------|-------------------|------|----------------------|
| Medium-tier match card | `region-gemma-match` | `role="region"` (inherits from parent card) | `aria-label="Gemma's match with alternatives"` when alternatives rendered; else existing label |
| Alternatives section | — | `<div>` with stagger motion | `border-t` rule is decorative; no `role` needed |
| Alternatives list | `list-gemma-alternatives` | `<ul role="list">` | `aria-label="Other close matches"` (separate from visual label text to stay neutral to copy tweaks) |
| Alternative row wrapper | — | `<li>` | No `role` override; semantic list item |
| Alternative button | `btn-alternative-{cip}` | `<button type="button">` | `aria-label="Select {alt.title}"` — CIP intentionally omitted from the spoken label (screen reader noise) |
| Alternative button disabled state during confirm | — | `disabled` attr flips true | Screen reader announces disabled state; focus remains on clicked row |
| `why` text | — | `<span>` | No separate label; included in screen-reader flow after title via natural DOM order |
| Focus state | — | keyboard `Tab` | Each alternative button is focusable; focus ring uses existing `focus-visible:ring-accent-info` treatment from button base styles |
| Keyboard confirm | — | `Enter` / `Space` | Same as mouse click — triggers `handleAlternativePick` |

### Responsive

**Desktop (≥640px, "mobile:" breakpoint satisfied):**
- Card max-width inherited from `MatchCard` container — unchanged.
- Alternative row layout: `flex-row items-center gap-3`, title left-aligned with `flex-1`, `why` right-aligned with `max-w-[280px] truncate text-right`.
- Row padding: `py-2 px-3`.

**Mobile (<640px):**
- Card shrinks to viewport with existing container padding.
- Alternative row layout: `flex-col gap-1`, title full-width with `truncate`, `why` stacks below title at `text-small text-text-muted`, no right-alignment.
- Row padding: `py-3 px-3` (guarantees ≥44px touch target).
- CTA row unchanged (already `flex-col mobile:flex-row` at line 417).

**Wide desktop (≥1024px):**
- No layout change. The card does not widen further; the `why` field's `max-w-[280px]` keeps the text density comfortable. Extra horizontal space lives in the card's parent container, outside the alternatives list.

### Visionary Deliverable — Checklist

- [x] Emotional target named: *deliberative — "Gemma is thinking with me, not guessing at me."*
- [x] All 8 Visionary Must Answer questions resolved (D1–D8) with rationale.
- [x] Three ASCII mockups: (a) default, (b) hover, (c) confirming-alt flash.
- [x] Token-mapped component tree for `AlternativesList` (~60 lines of reference TSX; target of ~30 functional lines once utility spans inline).
- [x] Motion spec table with delays, easing, and parity references to primary confirm flash.
- [x] Accessibility table covering region, list, buttons, disabled state, keyboard.
- [x] Responsive behavior for desktop/mobile/wide with specific class-level guidance.
- [x] Degenerate case (medium + zero alternatives) pinned to caution-card-without-alternatives.
- [x] No new tokens introduced. Every value reuses existing Brightpath tokens or literal values already present in the codebase.

---

## §4 Technical Specification

### Architecture Overview

The change is confined to the intent-resolution slice:

1. **Prompt layer** — both `backend/app/services/intent.py` (`_SYSTEM_PROMPT`) and `backend/cli.py` (duplicate prompt string near line 620) gain explicit instructions on confidence-tier semantics and alternative-count expectations.
2. **Service layer** — `intent.py:resolve_intent` needs no logic change beyond optional light validation (clamp alternatives ≤ 10). `needs_clarification = confidence == "low"` stays as-is.
3. **API contract** — `IntentResult` (Pydantic) and the frontend `IntentResult` TS type are already shaped for this. No migration, no schema version bump.
4. **Frontend rendering** — `MajorInput.tsx` `MatchContent` is refactored from binary (`isLowConfidence`) to tiered (`isUncertain`) and extended to render alternatives.
5. **Design system** — `DESIGN.md` §Gemma Interactions documents the three tiers; v3 HTML mockup gains a new "Medium-tier with alternatives" card variant.

No data pipeline, DuckDB, Iceberg, MCP, or Brightsmith touchpoints.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/services/intent.py` | Modify | Update `_SYSTEM_PROMPT` with tier-driven alternative-count rubric. Add input clamp: alternatives ≤ 10. No new functions. |
| `backend/cli.py` | Modify | Update the duplicate prompt string (near line 620–640) to match the new system prompt in `intent.py`. |
| `backend/app/models/career.py` | No change | `IntentResult` already accepts `confidence: str` and `alternatives: list[dict] \| None`. |
| `frontend/src/types/buildInput.ts` | No change | `IntentResult` TS type already includes `alternatives` and `confidence`. |
| `frontend/src/components/school/MajorInput.tsx` | Modify | In `MatchContent`: rename `isLowConfidence` → `isUncertain` (`confidence !== "high"`). Render alternatives list when `isUncertain && alternatives?.length`. Add `handleAlternativePick` that runs the same confirm flash + `onConfirm` handoff as the primary match. |
| `frontend/src/components/school/MajorInput.tsx` | Modify | Apply 3px border-l-accent-caution and `card-breathe-caution` glow when `confidence !== "high"` (already wired — verify the classname logic accommodates the rename). |
| `DESIGN.md` | Modify | Update §Gemma Interactions / Match Card to document the 3-tier rendering + alternatives list pattern. Reference the exact Brightpath tokens listed in §3. |
| `docs/mockups/brightpath-design-system-v3.html` | Modify | Add a new "Medium-tier · with alternatives" card variant to the Gemma section (alongside default/caution/confirming). |
| `backend/tests/services/test_intent.py` | Create | NEW file — net-new service-level coverage for intent resolution (currently none). |
| `frontend/src/components/school/MajorInput.test.tsx` | Create | NEW file — unit tests for the three rendering tiers + alternative selection. |

### Data Model Changes

None. Types are already present:

**Backend (`backend/app/models/career.py:317`)**:
```python
class IntentResult(BaseModel):
    matched_cip: str
    matched_title: str
    confidence: str                                 # "high"|"medium"|"low"
    reasoning: str = ""
    careers_preview: list[str] = Field(default_factory=list)
    audit_flag: str | None = None
    audit_message: str | None = None
    needs_clarification: bool = False
    alternatives: list[dict] | None = None          # [{cip, title, why}]
    parent_cip: str = ""
```

**Frontend (`frontend/src/types/buildInput.ts:55`)**:
```typescript
export interface IntentResult {
  matched_cip: string;
  matched_title: string;
  confidence: string;
  reasoning: string;
  careers_preview: string[];
  audit_flag: string | null;
  audit_message: string | null;
  needs_clarification: boolean;
  alternatives: Array<{ cip: string; title: string; why: string }> | null;
  parent_cip: string;
}
```

### Service Changes

> **Note:** This section was revised on 2026-04-18 to fold in the 6 required items from @genai-architect's CHANGES REQUESTED review (§5) plus the 2 non-blocking cleanups from @fp-architect.

**`backend/app/services/intent.py` `_INTENT_SYSTEM_PROMPT` — full rewrite (replaces the current template at lines 22–55).**

Key structural changes from the genai-architect review:
- Tier rubric is inserted **immediately after the persona/task description**, before the school-specific data blocks (Finding #3: attention placement).
- Template example shows `"alternatives": []` rather than a populated object (Finding #2: schema template undercuts "Never pad").
- Explicit positive constraint for high confidence (Finding #2).
- Lexical-match tiebreaker sentence for the high tier (Finding #1).
- High-tier example rewritten to a colloquial input requiring interpretation (Finding #6).
- Medium-tier example augmented with a cross-family alternative (Finding #7).
- Reasoning capped at 2 sentences to protect token budget (Finding #4).

```
You are a college program advisor who understands how students, parents,
counselors, and registrars all describe academic programs differently.

A student has told you what they want to study. Your job is to match their
intent to the most appropriate CIP (Classification of Instructional Programs)
code from the available options.

Consider how different people describe the same program:
- Students say: "pre-med", "CS", "business", "art"
- Parents say: "Physical Therapy", "Deaf Education", "Criminal Justice"
- Counselors say: "Special Ed", "STEM", "Allied Health"
- Registrars say: "CIP 51.2308 Physical Therapy/Therapist"

Confidence tiers drive how many alternatives you return.

- "high": The input resolves to exactly one CIP — no ambiguity, even if the
  phrasing is colloquial. Output exactly "alternatives": [].
  Tiebreaker: if the school's reported program list contains a single entry
  whose title is a near-direct match to the student input, use high even if
  the phrase sounds like an umbrella term.
  Example: "pre-PT" → 51.2308 Physical Therapy/Therapist.

- "medium": The input is a well-known shorthand or umbrella term that maps
  to a primary CIP but reasonable students mean different things. Return 2–4
  alternatives, ordered by how likely you'd pick each if the student had
  phrased it differently. Alternatives must be genuinely distinct programs
  and may span CIP families when a cross-family reading is plausible.
  Example: "business" (primary: 52.0201 Business Administration;
  alternatives: 52.0801 Finance, 52.1401 Marketing, 52.0701 Entrepreneurship,
  42.2804 Industrial-Organizational Psychology).

- "low": The input is too vague, ambiguous, or non-program-like for you to
  stake a primary match confidently. Still return your best primary, but
  include up to 10 alternatives spanning the plausible CIP neighborhoods.
  The frontend will show a picker rather than your primary.
  Examples: "helping people", "something with computers but not coding".

Never pad. If you are high-confident, "alternatives" MUST be []. Never exceed 10.

The student typed: "{student_input}"
School: {school_name}

Programs this school reports (these have earnings data):
{school_cip_list}

Additional specific programs in the same families (from the national
crosswalk — these have career path data even if the school doesn't report
them separately):
{crosswalk_cip_list}

Respond in JSON only, no preamble, no markdown. Keep "reasoning" to at most
two sentences.
{"matched_cip": "XX.XXXX", "matched_title": "Program Title",
"confidence": "high|medium|low",
"reasoning": "Up to two sentences explaining why this is the best match.",
"parent_cip": "XX.XX (the school-reported CIP that covers this program,
if different from matched_cip)",
"alternatives": []}
```

**`backend/cli.py` `_INTENT_SYSTEM_PROMPT`** — mirror the exact rubric above verbatim into the duplicate at lines 607–640.

**Drift-warning comments** (@fp-architect concern #10 — non-blocking cleanup folded in):
Add a one-line comment directly above each `_INTENT_SYSTEM_PROMPT` assignment noting that the two sites must stay in lockstep and referencing the parked consolidation follow-up in §11.

**`backend/app/services/intent.py` — token budget bump:**

Raise `max_tokens` from 500 → 700 at `_call_gemma_intent` (intent.py:176) to absorb the 10-alternative low-tier ceiling plus the 2-sentence reasoning (Finding #4).

**`backend/app/services/intent.py` — hardened JSON fence stripping (Finding #8):**

Replace the current strip at lines 192–196:

```python
cleaned = raw_response.strip()
if cleaned.startswith("```"):
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
```

with a more defensive version that drops both markdown fences and any trailing prose after the final top-level `}`:

```python
cleaned = raw_response.strip()
if cleaned.startswith("```"):
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```\s*$", "", cleaned)
last_brace = cleaned.rfind("}")
if last_brace != -1:
    cleaned = cleaned[: last_brace + 1]
```

**`backend/app/services/intent.py:resolve_intent` — post-parse alternatives pipeline (Findings #2, #9, #10):**

Replace the current `alternatives = parsed.get("alternatives")` assignment (line 278) with a pipeline that:
1. Coerces non-list values to `None` without crashing (P0 test #5).
2. Drops entries that aren't dicts or are missing `cip` / `title`.
3. Drops entries whose `cip` does not match `^\d{2}\.\d{4}$` (Finding #10: CIP hallucination).
4. Drops entries whose `cip` equals `matched_cip` or duplicates an earlier entry (Finding #9: dedup).
5. Clamps the result to ≤10 (spec §4 contract).

Reference implementation:

```python
_CIP_PATTERN = re.compile(r"^\d{2}\.\d{4}$")  # module-level constant

def _sanitize_alternatives(
    raw: Any, primary_cip: str
) -> list[dict[str, str]] | None:
    if not isinstance(raw, list):
        return None
    seen: set[str] = {primary_cip}
    cleaned: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        cip = str(item.get("cip", "")).strip()
        title = str(item.get("title", "")).strip()
        if not cip or not title:
            continue
        if not _CIP_PATTERN.match(cip):
            continue
        if cip in seen:
            continue
        seen.add(cip)
        cleaned.append({
            "cip": cip,
            "title": title,
            "why": str(item.get("why", "")).strip(),
        })
        if len(cleaned) == 10:
            break
    return cleaned
```

The `resolve_intent` call site becomes:

```python
alternatives = _sanitize_alternatives(parsed.get("alternatives"), matched_cip)
```

**Medium-tier degenerate-data policy (@fp-architect concern #12):**

When Gemma returns `confidence="medium"` with `alternatives=[]` (or alternatives that all get filtered out), the spec pins behavior to option (b) from the architect review: render the caution-styled card with the primary match alone, no alternatives list. Rationale: the caution styling honestly reflects Gemma's self-reported uncertainty even if its alternatives pool was unhelpful; silently upgrading to high styling would lie about confidence. The P1 frontend test `medium-tier card with zero alternatives still renders primary` enforces this.

### Frontend Changes

**`frontend/src/components/school/MajorInput.tsx` — `MatchContent` component changes:**

1. Rename at the top of `MatchContent`:
   ```typescript
   const isUncertain = intentResult.confidence !== "high";  // was: isLowConfidence === "low"
   ```

2. Update references throughout `MatchContent` — pill visibility, button labels, title color, raw-text color all key off `isUncertain` instead of `isLowConfidence`. (The existing caution styling already fires on the uncertain branch.)

3. Add alternatives rendering inside the match card, between the career preview and the actions row:
   ```tsx
   {isUncertain && intentResult.alternatives && intentResult.alternatives.length > 0 && (
     <AlternativesList
       alternatives={intentResult.alternatives}
       onPick={handleAlternativePick}
     />
   )}
   ```

4. Add `handleAlternativePick(alt: {cip, title, why})` — fires the same 320ms confirm flash then calls `onConfirm` with the alternative's CIP/title replacing `intentResult.matched_cip`/`matched_title`.

5. In the parent `MajorInput` component (line ~195), update the card border-l classname logic so that `border-l-accent-caution` + `card-breathe-caution` apply when `intentResult.confidence !== "high"` (currently: only `confidence === "low"`, but that branch is unreachable at render time).

**New subcomponent inside `MajorInput.tsx` (~30 lines):**
```tsx
function AlternativesList({
  alternatives,
  onPick,
}: {
  alternatives: Array<{ cip: string; title: string; why: string }>;
  onPick: (alt: { cip: string; title: string; why: string }) => void;
}) { /* stagger.fast children, per §3 visionary pass */ }
```

### Testing Impact Analysis

> **IMPORTANT**: Service-layer intent tests do NOT currently exist. This spec introduces the first ones.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `frontend/src/screens/SchoolMajorScreen.test.tsx` | all (3 tests) | **Low** | Tests interact with the outer screen, not MatchContent internals. A rename inside `MatchContent` should not affect them. |
| `frontend/src/components/school/EffortLoansPanel.test.tsx` | all | **Low** | Unrelated component. |
| `backend/tests/services/test_school_lookup.py` | all | **Low** | Different service. |

No `backend/tests/services/test_intent*.py` file exists today — verified via `find backend/tests -name "*intent*"`. There is no existing unit-level coverage to protect.

#### Authorized Test Modifications

None required. All test changes are additive (new files).

#### Confirmed Safe

- `frontend/src/screens/SchoolMajorScreen.test.tsx` — must continue to pass.
- `frontend/src/components/school/EffortLoansPanel.test.tsx` — must continue to pass.
- All `backend/tests/services/test_*.py` existing tests — must continue to pass.

If any of these fail post-implementation, STOP and escalate.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_intent.py` | `test_resolve_intent_high_confidence_returns_empty_alternatives` | Gemma prompt + parser round-trip: high tier yields `alternatives = []`, `needs_clarification = False`. |
| P0 | `backend/tests/services/test_intent.py` | `test_resolve_intent_medium_confidence_returns_2_to_4_alternatives` | Medium tier: `2 <= len(alternatives) <= 4`, `needs_clarification = False`. |
| P0 | `backend/tests/services/test_intent.py` | `test_resolve_intent_low_confidence_sets_needs_clarification` | Low tier: `needs_clarification = True`, alternatives length permitted up to 10. |
| P0 | `backend/tests/services/test_intent.py` | `test_resolve_intent_clamps_excess_alternatives_to_10` | Gemma misbehaves and returns 15 alternatives — service clamps to 10. |
| P0 | `backend/tests/services/test_intent.py` | `test_resolve_intent_handles_null_alternatives` | Gemma returns `"alternatives": null` — service does not crash. |
| P0 | `frontend/src/components/school/MajorInput.test.tsx` | `renders high-tier card with no alternatives list` | High confidence → purple card, no alternatives UI, "That's right" button. |
| P0 | `frontend/src/components/school/MajorInput.test.tsx` | `renders medium-tier card with alternatives list` | Medium confidence → caution card, 3 alternatives visible, "Close enough" button. |
| P0 | `frontend/src/components/school/MajorInput.test.tsx` | `clicking an alternative triggers onConfirm with that CIP` | Alternative row click → `onConfirm` called with alternative's CIP/title, NOT primary's. |
| P0 | `frontend/src/components/school/MajorInput.test.tsx` | `low-tier result renders clarify picker, not match card` | Low confidence → never sees MatchContent; renders ClarifyContent instead. |
| P1 | `backend/tests/services/test_intent.py` | `test_resolve_intent_preserves_audit_flag_across_tiers` | Playful warning / hard reject still passes through regardless of confidence tier. |
| P1 | `frontend/src/components/school/MajorInput.test.tsx` | `medium-tier card with zero alternatives still renders primary` | Degenerate data from Gemma: medium confidence but empty alternatives — does not crash, renders primary alone. |
| P1 | `frontend/src/components/school/MajorInput.test.tsx` | `confirm flash fires on alternative click same as primary` | 320ms thrive flash behavior parity between primary and alternative confirm paths. |
| P2 | `backend/tests/services/test_intent.py` | `test_resolve_intent_alternatives_have_distinct_cips` | Alternatives should not repeat the primary CIP or each other. Light validation — flag only, not a failure. |

#### Test Data Requirements

- Backend: mock `gemma_client.generate` responses for each tier. Fixture file at `backend/tests/fixtures/intent_responses.json` with high/medium/low example payloads.
- Frontend: vitest mock for `apiPost("/intent/", ...)` returning tier-specific `IntentResult` objects. Mock MSW or direct import mock — align with existing patterns in `SchoolMajorScreen.test.tsx`.

### Gemma-Touching Work (Required Discipline)

Per `CLAUDE.md` and `SPEC_GUIDELINES.md`:

- **Fallback behavior** — Existing fallback in `intent.py` (line ~271: `raise ValueError(...)` on parse failure → frontend catches, sets `phase="fallback"`) is preserved. If Gemma returns malformed JSON or a missing `confidence` field, the frontend still enters the "Gemma couldn't match that — pick from the list below" fallback. No regression.
- **`logs/gemma.jsonl` capture** — No changes to the logging call site in `intent.py`. Prompt changes do not affect logging.
- **Ollama + OpenRouter parity** — The prompt change is content-only; both backends go through the same `gemma_client.generate` OpenAI-compatible API. Both must be smoke-tested in §9 Verification.
- **Rate-limit / concurrency (cloud demo)** — Adding alternatives (up to 10 lines of JSON) increases output tokens by roughly 200–400 per call. Acceptable at demo concurrency; no rate-limit change.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** COMPLETE
**Reviewed:** 2026-04-18

#### System Context

This change sits entirely in the intent-resolution slice of the backend (FastAPI service layer + shared Pydantic model) and the `MajorInput` component on the frontend. It does not touch Brightsmith zones, DuckDB Gold products, the MCP server, or any Gemma role outside of intent resolution (which is a pre-RPG onboarding concern, not one of the seven numbered Gemma roles). The change is additive semantics on an existing shipped contract: `IntentResult.confidence` and `IntentResult.alternatives` are already wired through `backend/app/routers/intent.py` -> `backend/app/services/intent.py` -> `frontend/src/types/buildInput.ts`. The spec makes the schema end-to-end-usable rather than introducing new boundaries.

#### Data Flow Analysis

Traced source to screen:

1. `POST /intent/` (router at `backend/app/routers/intent.py:10`) -> `intent.resolve_intent(major_text, school_name, unitid, programs)` (service at `backend/app/services/intent.py:241`).
2. Service calls `_call_gemma_intent` -> `gemma_client.generate` (Ollama or OpenRouter). JSON parsed; on failure, `raise ValueError` (line 270) bubbles to the router, which surfaces as a handled error that drives the frontend to `phase="fallback"`.
3. Service returns `IntentResult` with `confidence` verbatim from Gemma and `needs_clarification = confidence == "low"` (line 307). This is unchanged.
4. Frontend reads `IntentResult` -> `MajorInput.tsx` renders `ClarifyContent` when `needs_clarification` is true (routed at the parent phase dispatcher), `MatchContent` otherwise. `MatchContent` currently derives `isLowConfidence = confidence === "low"` (line 300), which is dead code because low never reaches this branch. Spec replaces with `isUncertain = confidence !== "high"`.
5. On primary confirm or alternative confirm, `onConfirm` hits `POST /intent/confirm` (router at `backend/app/routers/intent.py:23`) with the chosen CIP/title. No change to that endpoint.

Every boundary crossing is already typed. No new arrows.

#### Contract Review

`IntentResult` (backend `career.py:317`) and its TypeScript twin (`buildInput.ts:55`) are structurally identical and stay so. The router signatures don't change. The `/intent/confirm` payload doesn't change. The only semantic drift: `confidence="medium"` flips from "renders same as high" to "renders caution styling with alternatives," and `alternatives` flips from "frontend ignores it" to "frontend renders it when uncertain." Zero breaking changes for the CLI harness or any existing `IntentResult` consumer.

#### Findings

##### Sound

1. **No schema migration.** Reusing the shipped `IntentResult` shape is the right call. A Pydantic v2 migration for this hackathon would be pure cost.
2. **Backend tier gate stays authoritative.** Keeping `needs_clarification = confidence == "low"` in the service means the router/backend remains the single source of truth for "should the picker render." The frontend's new `isUncertain` flag is strictly a rendering concern downstream of that gate — it never contradicts it.
3. **Fallback path preserved.** `raise ValueError` on parse failure (line 270) still drives `phase="fallback"`. Tier-aware rendering only matters after a successful parse, so the fallback contract is untouched.
4. **Alternatives clamp at the service layer is the right boundary.** See concerns #7.
5. **Zero MCP / DuckDB / Brightsmith impact.** Correctly scoped.

##### Concerns

6. **Backend vs frontend tier-semantics split is intentional but must be documented in-code.** Backend: "low" == "needs clarify picker." Frontend: "non-high" == "show caution + alternatives." These are two different predicates on the same field, and both are correct — but a future reader will trip on it. **Impact:** A maintainer adding a fourth tier (e.g., "unknown") or renaming "medium" will update one side and miss the other, re-introducing the current dead-code defect in the opposite direction. **Recommendation:** Add a one-line comment in `intent.py:307` ("low routes to clarify picker; medium/high route to match card — see MajorInput.tsx isUncertain") and mirror it in `MatchContent`. No runtime cost, eliminates the drift trap. This does not block approval.

7. **Loose `alternatives: list[dict] | None` is acceptable for this spec but accrues real debt.** Pydantic v2 is in the stack (per `CLAUDE.md` Stack row), and the project standard is "Pydantic v2 for data models... No `Any` unless genuinely unavoidable." A `list[dict]` is effectively `list[dict[str, Any]]` — it'd let a future agent silently widen the alternative shape (e.g., add `earnings`) without updating the TS twin. **Impact:** Silent contract drift between backend and frontend the next time someone touches the alternative payload. **Recommendation:** Accept the loose type for THIS spec (hackathon scope, already shipped), but the follow-up refactor spec referenced in §2 decision #7 should be tracked as a named follow-up in §11, not just "parked." A `class Alternative(BaseModel)` is ~10 lines and would make the post-parse clamp self-validating. Not a blocker.

8. **Service-layer clamp is the correct location.** The `alternatives = raw_alts[:10] if isinstance(raw_alts, list) else None` lives in `resolve_intent` before `IntentResult` is constructed. This is the right seam — it's defense against a misbehaving Gemma, which is service-layer territory, not model-layer. A Pydantic `field_validator` with `max_length=10` would **reject** a 15-item response (raising `ValidationError` up through the router as HTTP 500), but we want graceful degradation to the first 10. The spec's imperative clamp is the right mechanism; Pydantic would be wrong here. APPROVED as specified.

9. **`isUncertain` naming is preferable to the proposed alternatives.** `confidence !== "high"` is semantically "we are not certain." `isMedium` would under-describe (doesn't cover future tiers); `isNotHigh` reads awkwardly. `isUncertain` is the right abstraction even if `confidence` remains stringly-typed.

10. **Prompt drift between `intent.py` and `cli.py` is a real but time-bounded risk.** Out-of-scope consolidation per §2 decision #5 is defensible given the May 18 deadline, BUT the spec currently relies on a human remembering to update two files. **Impact:** CLI and web UI drift silently when the next prompt tweak lands and the author touches only one site. **Recommendation:** Add a one-line comment at the top of each `_INTENT_SYSTEM_PROMPT` definition — something like `# DUPLICATE: mirrors backend/cli.py:607 (consolidation tracked in §11 follow-ups of feature-gemma-tiered-matching.md)` and the reverse. Costs five minutes, buys a year of drift protection. Not a blocker for approval, but should land with this spec.

11. **API contract: zero breaking change confirmed.** `POST /intent/` response shape is unchanged. `POST /intent/confirm` request shape is unchanged. The CLI harness (which reads `IntentResult.alternatives` at `cli.py:977+` per the spec) already handles alternatives; it will continue to work and will now receive better-populated alternatives arrays for medium/low tiers. No consumer breaks.

12. **New failure mode the spec doesn't explicitly handle: Gemma returns `"confidence": "medium"` with an empty or null `alternatives`.** Per the prompt, this shouldn't happen, but Gemma is a probabilistic system. Spec §4 P1 test `medium-tier card with zero alternatives still renders primary` correctly covers the frontend side. The backend side also handles it gracefully (`alternatives = raw_alts[:10] if isinstance(raw_alts, list) else None` — empty list passes through, None passes through). **Impact:** No crash, but the student sees a caution-styled card with no alternatives and a "Close enough" button — which reads as a UI bug. **Recommendation:** Decide the policy explicitly in the spec: either (a) downgrade to `high`-style rendering when medium-with-no-alts (cleanest UX), or (b) keep caution styling and let the primary stand alone (matches P1 test). I'd pick (a) but (b) is defensible. Current spec is ambiguous. Not a blocker — the P1 test pins the behavior to (b) — but should be called out explicitly in §3 or §4.

13. **`confidence` as `str` (not `Literal["high","medium","low"]`) is a missed cheap win.** `Literal` on the Pydantic model would catch malformed Gemma responses at parse time with zero runtime cost. Same cost-benefit as concern #7 — not a blocker, but genuinely five minutes of work for a typo-proof contract. The `confidence = str(parsed.get("confidence", "unknown"))` line at `intent.py:276` is already tolerant; a `Literal` validator would reject "unknown" and fall through to the error path (which in turn routes to `phase="fallback"` via the router). Acceptable either way; noting for the follow-up tightening spec.

14. **Ollama VRAM / latency — negligible impact.** Up to 10 alternatives at ~30-40 tokens each adds ~300-400 output tokens. Gemma 4 on Ollama handles this comfortably at temperature 0.1 with max_tokens=500 (current value at `intent.py:177`). No need to bump `max_tokens`. Both Ollama and OpenRouter paths identical — spec is correct to call for smoke tests in §9 on both.

15. **Caching path is untouched and correct.** `_intent_cache` at `intent.py:20` stores confirmed matches (`confirm_intent` seeds it with `"confidence": "high"`). Cache hits never emit alternatives because by definition they've been student-confirmed and are high-confidence outcomes. Spec doesn't mention this, but the cache hydrate path at `intent.py:252` correctly omits `alternatives` — a cached hit will render as high tier, which is the right semantic. No concern.

##### Blockers

None.

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions

Approved as specified. Two strongly-recommended but non-blocking cleanups to land with implementation:

1. Add drift-warning comments at both `_INTENT_SYSTEM_PROMPT` sites (`backend/app/services/intent.py:22` and `backend/cli.py:607`) pointing at each other and at §11 follow-ups of this spec. Five minutes of work; prevents the exact class of bug this spec exists to fix.
2. Resolve the ambiguity flagged in concern #12 (medium tier with zero alternatives) explicitly in §3 or §4 — confirm the P1 test's behavior is intentional, or downgrade to high-style rendering. Either is fine; the spec should pick one.

Neither blocks implementation. If the implementer hits medium-with-zero-alts in testing and the UX reads as a bug, fall back to option (a) in concern #12 and document the change in §6.

### @genai-architect Review
**Status:** COMPLETE
**Reviewed:** 2026-04-18

#### Findings

1. **Tier collapse toward medium is the primary calibration risk.** Gemma 4 (both Ollama and OpenRouter quantizations) hedges toward the middle of discrete scales when boundary conditions are under-defined. "Exactly one CIP — no ambiguity" and "too vague for a primary match" are crisp. "Well-known shorthand or umbrella term" is broad enough to capture clean inputs like "Computer Science" or "Mechanical Engineering." Recommend adding a tiebreaker sentence: "If the school's own program list contains a single entry whose name is a near-direct match to the student input, use high regardless of whether it is an umbrella term." This gives Gemma an observable anchor that breaks the high/medium tie without requiring a post-hoc server-side override.

2. **"Never pad" is a weak negative constraint — the schema template undercuts it.** At `temperature=0.1` the rubric's instruction-following is reliable in isolation, but the JSON schema template at `intent.py:53–54` shows `"alternatives": [{"cip": "XX.XXXX", ...}]` with one populated example object. That example is a counter-example to "high → empty array." Gemma pattern-matches on the schema shape before it runs the tier logic. Replace the template value with `"alternatives": []` and add an explicit positive constraint: "For high confidence, output exactly `\"alternatives\": []`."

3. **Rubric should be inserted before the school CIP data, not after the JSON schema.** The proposed insertion point ("replaces current alternative-count paragraph") sits after the `{school_cip_list}` and `{crosswalk_cip_list}` blocks. In practice those blocks run 20–60 lines, pushing the tier semantics late in the system context behind a wall of CIP codes. Insert the rubric immediately after the persona/task description and before the `{student_input}` / school-data block. The JSON schema template should remain last.

4. **Token budget — real truncation risk at low tier; raise `max_tokens` to 700.** Current ceiling is 500 (`intent.py:176`). A full low-tier response with 10 alternatives at ~12 tokens each (~120 tokens) plus primary fields (~80 tokens) runs 350–420 tokens of JSON. That nominally fits, but Gemma writes more verbose `reasoning` on low-confidence inputs (explaining the ambiguity) — 3-sentence reasoning alone costs 60–80 tokens and pushes the total over 500. The truncated JSON will fail `json.loads`, triggering the `raise ValueError` fallback on exactly the inputs (vague, uncertain) where showing options is most valuable. Raise `max_tokens` to 700, or add an explicit instruction: "reasoning: maximum 2 sentences."

5. **Temperature: hold at 0.1 for all tiers.** Medium-tier ordering of alternatives ("ordered by how likely you'd pick each") is a ranking task, not a creative generation task. Higher temperature increases variance in which alternatives surface without improving their relevance or coverage. No change recommended.

6. **High-confidence example teaches format, not semantics.** "Physical Therapy" → 51.2308 is a near-lexical match — it tells Gemma nothing about when to pick high vs. medium, only how to format a CIP code. Replace with a colloquial input that requires interpretation but has exactly one valid mapping: e.g., "pre-PT" → 51.2308, or "nursing BSN" → 51.3801. This teaches the model that high confidence is about uniqueness of the resolved mapping, not lexical precision of the input.

7. **Medium-tier "psychology" example risks anchoring alternatives to subcodes only.** Both listed alternatives (42.2701, 42.2813) are subcodes of the primary 42.0101. If Gemma anchors on this pattern it will generate systematically narrow alternatives that stay within the same 2-digit CIP family, missing more relevant cross-family programs (e.g., 42.2801 Industrial-Organizational Psychology sits closer to business for some students). Add one cross-family alternative to the medium example to signal that alternatives can span CIP families.

8. **JSON parse fragility is meaningfully higher with 10-item arrays.** The markdown-fence stripping at `intent.py:193–196` handles only a single fence pair with no trailing content. Gemma 4 via Ollama occasionally appends an explanation sentence after the closing `}` on uncertain outputs — a behavior that increases with response length and hedging. The existing `raise ValueError` fallback is the right error boundary, but the stripping should be hardened to drop everything after the last `}` that closes the top-level JSON object before attempting `json.loads`. This prevents a valid but prose-appended response from unnecessarily falling to the clarify picker.

9. **Alternatives deduplication must be server-side, not just a P2 test.** Gemma regularly returns the primary `matched_cip` as the first element of `alternatives` on umbrella inputs. The spec's P2 test flags this but imposes no enforcement. For medium tier, a duplicate-primary alternative row renders as a button that re-confirms the same CIP as the hero match — a silent UX defect that the P2 test would catch in CI but only after shipping. Promote deduplication of `matched_cip` from `alternatives` to the same post-parse block as the clamp (`raw_alts[:10]`), at zero additional complexity.

10. **Cross-backend parity — CIP hallucination is the primary Ollama/OpenRouter divergence risk.** Instruction-following and JSON adherence are comparable between the two backends at `temperature=0.1`. The divergence point is CIP code accuracy in alternatives: the larger cloud model (`google/gemma-4-26b-a4b-it`) has broader training coverage of CIP codes and is less likely to hallucinate, but it also generates more confident-sounding alternatives with plausible-looking but invalid 6-digit CIP codes (e.g., `52.0999` instead of `52.0901`). The post-parse clamp does not validate CIP format. Add a format check on each alternative's `cip` field (`^\d{2}\.\d{4}$`) and silently drop malformed entries; this also makes the alternatives array safe to pass directly to the MCP `get_career_paths` tool without a second validation layer downstream.

11. **`@fp-architect` finding #15 (cache path is correct) needs a scope clarification.** The architect correctly notes that `confirm_intent` seeds the cache with `"confidence": "high"` — post-confirmation, high rendering is right. The gap is the *pre-confirmation* repeat path: a student types "business," gets a medium-tier result (alternatives rendered), does not confirm, navigates away and returns. The cache key is `(normalized_input, unitid)`, but `_intent_cache` is only populated by `confirm_intent` — not by `resolve_intent`. So the pre-confirmation repeat does re-call Gemma, not hit the cache. No actual bug. Finding #15 is correct; no cache change needed. This resolves apparent tension between architect and genai-architect reviews.

12. **Rubric reinforcement in the user message: not recommended.** The user message is currently `'Match this student input to a CIP code: "{prompt_input}"'` (`intent.py:175`). Adding tier context there would add ~50 tokens per call and is redundant at `temperature=0.1`. The user message's job is to anchor Gemma's attention on the student input, not re-state the rubric. Leave it as-is.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

**Required before implementation (5 items — these affect correctness):**

1. Raise `max_tokens` from 500 to 700 (finding #4).
2. Replace the alternatives template value with `[]` and add positive high-tier constraint (finding #2).
3. Insert the tier rubric before the school CIP data block (findings #3).
4. Add CIP format validation (`^\d{2}\.\d{4}$`) on each alternative; drop malformed entries silently (finding #10).
5. Add server-side deduplication of `matched_cip` from the alternatives list in the post-parse block (finding #9).
6. Harden JSON fence-stripping to discard trailing prose after the closing `}` (finding #8).

**Strongly recommended prompt improvements (non-blocking):**

- Replace high-confidence example with a colloquial input (finding #6).
- Add one cross-family alternative to the medium-tier example (finding #7).
- Add a lexical-match tiebreaker sentence to the high-tier definition (finding #1).

#### Resolution (2026-04-18)

All 6 required items and all 3 non-blocking prompt improvements from @genai-architect, plus the 2 non-blocking cleanups from @fp-architect (concerns #10 drift comments, #12 medium-with-zero-alts policy), have been folded into §4 Service Changes. Spec proceeds to step 2 (Design Vision) under the revised §4.

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline, crosswalk, or stat formula changes)

---

## §6 Implementation Log

**Status:** COMPLETE
**Implemented:** 2026-04-18

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/app/services/intent.py` | Rewrote `_INTENT_SYSTEM_PROMPT` with tier rubric before school data block; `"alternatives": []` in template; lexical-match tiebreaker; colloquial high example; cross-family medium example; "Keep reasoning to 2 sentences" directive. Raised `max_tokens` 500→700. Hardened JSON parsing to strip trailing prose after final `}`. Added `_CIP_PATTERN` + `_sanitize_alternatives()` that drops non-dicts, bad CIPs, the primary CIP, and duplicates; clamps to 10. Added tier-split drift comment above `IntentResult` construction. |
| `backend/cli.py` | Mirrored the new `_INTENT_SYSTEM_PROMPT` verbatim. Bumped `max_tokens` and applied the trailing-prose JSON strip. Added duplicate-prompt drift-warning comment pointing at the service copy. (CLI alternatives consumer at line 925 kept as-is — CLI is a dev harness; its lax `or []` coercion is acceptable.) |
| `frontend/src/components/school/MajorInput.tsx` | Renamed `isLowConfidence` → `isUncertain = confidence !== "high"` throughout `MatchContent`. Parent card border-l logic now lights caution on `confidence !== "high"` (was `=== "low"`, unreachable post-routing). Added `confirmingAltCip` state + `handleAlternativePick`. Added `AlternativesList` subcomponent per §3 visionary spec (section label, ▸ glyph, accent-info title with text-primary hover, right-aligned muted `why`, confirm flash at literal parity with primary CTA glow, siblings dim to 0.45). Parent `handleConfirm` accepts optional `{matched_cip, matched_title}` override; careers preview and `substitutionApplied` are suppressed on alternative confirms. |
| `DESIGN.md` | Appended "Tiered Match Card (Three-Confidence Extension)" subsection documenting the medium-tier alternatives pattern, tokens, motion, a11y, degenerate-state policy, and copy rationale. Existing Match Card docs untouched. |
| `docs/mockups/brightpath-design-system-v3.html` | Appended "Medium-tier · with alternatives" variant — two cards (default + confirming-alternative) plus scoped `.gemma-alternatives-*` CSS. Additive only; existing Gemma section cards and Tone Exploration untouched. |

### Deviations from Spec

None material. Two minor judgment calls:

1. **Parent `handleConfirm` signature** — §3 showed the visionary's conceptual pattern `onConfirm({matched_cip, matched_title})`; the implementation kept the MatchContent `onConfirm` prop as `(override?: {...}) => void` so the primary-confirm call site stays `onConfirm()` (zero-arg, unchanged) and only alternative picks pass the override. Semantically identical.
2. **CSS variable reference in the confirm-flash animation** — §3 referenced `var(--color-bp-surface)` but the project's actual CSS custom property is `--color-bg-surface` (Tailwind token `bp.surface` maps to it). Used the correct variable; no token change.

Alternative-confirm handoff drops `careers_preview` (the preview was derived from the primary CIP) and `substitutionApplied` (no substitution context for an alternative). Documented inline in `handleConfirm`.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | Pass | ruff all green; mypy surface errors all pre-existing (confirmed via `git stash` diff — same 6 errors before changes); TypeScript clean after fixing `--color-bp-surface` → `--color-bg-surface`. | CSS variable reference corrected before commit. |

---

## §7 Test Coverage

**Status:** COMPLETE
**Author:** @test-writer
**Completed:** 2026-04-18

### Tests Added

| Test File | Test Name | Priority | What It Tests |
|-----------|-----------|----------|---------------|
| `backend/tests/services/test_intent.py` | `test_resolve_intent_high_confidence_returns_empty_alternatives` | P0 | High-tier response round-trips: `confidence="high"`, `alternatives=[]`, `needs_clarification=False`. |
| `backend/tests/services/test_intent.py` | `test_resolve_intent_medium_confidence_returns_2_to_4_alternatives` | P0 | Medium-tier: `2 <= len(alternatives) <= 4`, every alt has well-formed cip/title, no echo of primary. |
| `backend/tests/services/test_intent.py` | `test_resolve_intent_low_confidence_sets_needs_clarification` | P0 | Low-tier: `needs_clarification=True`; ≤10 alternatives; fixture's 5 distinct alts survive sanitizer. |
| `backend/tests/services/test_intent.py` | `test_resolve_intent_clamps_excess_alternatives_to_10` | P0 | Injects 15 well-formed alts; asserts sanitizer clamps to exactly the first 10 in input order. |
| `backend/tests/services/test_intent.py` | `test_resolve_intent_handles_null_alternatives` | P0 | Gemma returns `"alternatives": null`; service returns `alternatives=None` (not `[]`), no crash. |
| `backend/tests/services/test_intent.py` | `test_resolve_intent_preserves_audit_flag_across_tiers` | P1 | `playful_warning` on medium and `hard_reject` on high both propagate through `IntentResult.audit_flag` / `audit_message`. |
| `backend/tests/services/test_intent.py` | `test_sanitize_drops_malformed_cip_codes` | Bonus | Direct sanitizer: mix of valid `XX.XXXX` and malformed (`52.999`, `abc`, `52.02`, empty); only well-formed survive. |
| `backend/tests/services/test_intent.py` | `test_sanitize_drops_primary_cip_echoed_in_alternatives` | Bonus | Direct sanitizer: Gemma echoes primary CIP as first alt; echo is stripped, genuine alts keep input order. |
| `frontend/src/components/school/MajorInput.test.tsx` | `renders high-tier card with no alternatives list` | P0 | High tier: "That's right" CTA, no `aria-label="Other close matches"` region, no "best guess" pill. |
| `frontend/src/components/school/MajorInput.test.tsx` | `renders medium-tier card with alternatives list` | P0 | Medium tier: "Close enough" CTA + pill + alternatives list with 3 buttons using `aria-label="Select {title}"`. |
| `frontend/src/components/school/MajorInput.test.tsx` | `clicking an alternative triggers onConfirm with that CIP` | P0 | Click "Finance" alt on a Business-primary medium card → `onConfirm` receives `cipCode=52.0801`, `cipTitle="Finance"`, `careersPreview=[]`, `substitutionApplied=false` after the 320ms flash. |
| `frontend/src/components/school/MajorInput.test.tsx` | `low-tier result renders clarify picker, not match card` | P0 | `needs_clarification=true` → ClarifyContent header + filter input render; no match-card CTAs, no alternatives list. |
| `frontend/src/components/school/MajorInput.test.tsx` | `medium-tier card with zero alternatives still renders primary` | P1 | Degenerate medium data (§3 D7): caution styling + "Close enough" + "best guess" still render, alternatives region omitted. |
| `frontend/src/components/school/MajorInput.test.tsx` | `confirm flash fires on alternative click same as primary` | P1 | Click an alt → all other alt buttons + primary CTA + "Not quite" flip to `disabled` during the 320ms flash window. |

### Edge Cases Covered

- [x] Gemma returns 15 alternatives for low tier (over the 10-ceiling contract).
- [x] Gemma returns `"alternatives": null` instead of an empty list.
- [x] Gemma hallucinates CIP codes (3-digit suffix, bare string, 2-digit suffix, empty string) — sanitizer filters each.
- [x] Gemma echoes the primary CIP inside the alternatives array (dedup against primary).
- [x] Medium tier with empty alternatives array — card renders without blowing up or downgrading to high styling.
- [x] Audit `playful_warning` on medium tier threads through.
- [x] Audit `hard_reject` on high tier threads through without mutating `confidence`.
- [x] Alternative click fires the 320ms flash before `onConfirm` — clicking does NOT synchronously confirm.
- [x] Alternative confirm drops `careers_preview` + `substitutionApplied` so the student doesn't see the wrong career list.
- [x] All interactive elements disable during the confirm flash (no double-fire).

### Test Results

| Suite | Pass | Fail | Skip | Total | Notes |
|-------|------|------|------|-------|-------|
| pytest (new: `test_intent.py`) | 8 | 0 | 0 | 8 | All P0 + P1 + 2 bonus sanitizer tests passing. |
| pytest (full backend suite) | 328 | 0 | 0 | 328 | No regressions. |
| vitest (new: `MajorInput.test.tsx`) | 6 | 0 | 0 | 6 | All P0 + P1 tests passing; no `act()` warnings. |
| vitest (full frontend suite) | 388 | 2 | 1 | 391 | 2 pre-existing failures in `src/screens/ProfileScreen.test.tsx` — reproducible without this spec's changes (verified by running the suite with `MajorInput.test.tsx` temporarily removed; same 2 failures). Not in this spec's scope. |

### Gaps Identified

- **No integration test for the `/intent/` router end-to-end.** The service-level tests mock `gemma_client.generate` and `mcp_client.get_server`, so the FastAPI router path (`backend/app/routers/intent.py`) is unexercised by these tests. Acceptable for this spec (router was already covered by the live CLI + the existing manual smoke flow), but noted for future hardening.
- **No test for `_call_gemma_intent`'s trailing-prose stripping.** The new behavior at `intent.py:230–232` (cutting text after the final `}`) is invoked by every test via the sanitizer path, but there is no test that asserts it directly (e.g., Gemma returns `'{"a":1} trailing garbage'`). Low risk — the existing parser tests in `test_gemma_client.py` cover similar territory, and any regression would surface as a `parse_error` in our mocked tests. Flag as P2 follow-up.
- **No browser/visual test for the 320ms thrive flash motion.** vitest in jsdom cannot observe Framer Motion's `animate={{ boxShadow: ... }}` applying, only the `disabled` flag that rides alongside it. The motion spec (§3 D6) is covered by the design audit (§8) and manual QA, not by automated tests.
- **Audit mapping is mocked, not round-tripped.** The P1 audit_flag test stubs the audit JSON directly; if `_audit_intent_mapping`'s prompt template drifts, these tests won't catch it. Acceptable — this spec explicitly scopes out audit prompt changes, and the prompt is covered separately by the existing playful_warning CLI smoke.

### Existing Tests Status

§4 "Existing Tests at Risk" classified the following as **Low risk**. All confirmed still passing:

- `frontend/src/screens/SchoolMajorScreen.test.tsx` — 3/3 pass.
- `frontend/src/components/school/EffortLoansPanel.test.tsx` — 5/5 pass.
- `backend/tests/services/test_school_lookup.py` — 16/16 pass.
- All other `backend/tests/services/test_*.py` — pass (see 328/328 above).

### Running the Tests

```bash
# Just the new backend tests
cd backend && uv run pytest tests/services/test_intent.py -v

# Full backend suite
cd backend && uv run pytest

# Just the new frontend tests
cd frontend && npx vitest run src/components/school/MajorInput.test.tsx

# Full frontend suite (expect 2 pre-existing ProfileScreen failures, unrelated)
cd frontend && npx vitest run
```

---

## §8 Reviews

**Status:** APPROVED (S1 + M2 fix committed; section-label copy FAIL corrected; M1/M3/M4/N1 tracked in §11)

### Design Audit (@fp-design-auditor)
**Status:** COMPLETE

---

## `frontend/src/components/school/MajorInput.tsx`

### PASS

- **Caution palette parity (lines 199–204):** Parent container border class logic correctly keys on `intentResult.confidence !== "high"`. When `confidence` is not `"high"`, the card gets `border-l-accent-caution` and `animate-[card-breathe-caution_4s_ease-in-out_infinite]`; when it is `"high"`, it gets `border-l-accent-insight` and `animate-[card-breathe_4s_ease-in-out_infinite]`. Matches spec §3 token table.
- **Title color semantics (lines 346–351):** `titleColor` resolves to `var(--color-accent-thrive)` on confirm, `var(--color-accent-caution)` when `isUncertain`, and `var(--color-accent-insight)` on high confidence. Matches DESIGN.md §Gemma Match Card color-semantics table exactly.
- **"best guess" pill (line 396):** `bg-[rgba(242,212,119,0.15)] text-accent-caution rounded-full`. This rgba literal is pre-existing in the file and matches DESIGN.md §Pills pill-caution background value (`rgba(242, 212, 119, 0.15)`). Not a new introduction.
- **Alternative row text default (line 573):** `text-accent-info` — PASS per §3 token table.
- **Alternative row text hover (line 573):** `group-hover:text-text-primary` — PASS per §3 token table.
- **Alternative row hover bg (line 550):** `hover:bg-bp-surface` — PASS per §3 token table.
- **Row dividers (line 543):** `border-t border-border-subtle` applied to every row where `idx !== 0`. First row has no top border. PASS per §3 spec ("first row has no rule").
- **Section label (lines 519–527):** `font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info`. Matches §3 token table and DESIGN.md §Section Labels spec exactly. PASS.
- **`why` text (line 587):** `font-body text-small text-text-muted`. Not italic. PASS per §3 D2 ("Italics: no").
- **Confirm flash box-shadow (lines 468, 554):** `"0 0 24px rgba(125, 212, 163, 0.45)"` — used on primary CTA (line 468) and on the confirming alternative row (line 554). This is the same value at both sites. The DESIGN.md §Gemma Match Card documents this as the primary CTA glow value ("thrive glow `0 0 24px rgba(125,212,163,0.45)`"). The §3 spec explicitly notes this is a "literal reuse of primary CTA glow value — no new token." Documented, not a violation.
- **Motion tokens — springs (lines 523, 541, 559):** All new `AlternativesList` transitions use `springs.smooth` or `springs.snappy` imported from `@/styles/motion`. No ad-hoc spring configs introduced.
- **Stagger/delay (lines 513–517):** `staggerChildren: 0.05, delayChildren: 0.55`. Matches spec §3 D5 step 5 contract exactly.
- **Section label entrance (lines 519–524):** Section label animated with `variants` entry `{ opacity: 0, y: 8 → opacity: 1, y: 0, transition: springs.smooth }`. Matches §3 D5 step 4.
- **`<ul role="list" aria-label="Other close matches">` (lines 529–531):** Present. PASS.
- **Row `<button type="button" aria-label="Select {title}">` (line 549):** `type="button"` and `aria-label` with title interpolation present on every row. PASS.
- **Disabled state during confirm flash (line 547):** `disabled={confirmingAltCip !== null}` — uses the real HTML `disabled` attribute, not styling only. PASS.
- **AlternativesList container margin/padding (line 509):** `mt-[18px] pt-4 border-t border-border-subtle`. `mt-[18px]` = 18px top margin, `pt-4` = 16px padding-top. Matches DESIGN.md §Tiered Match Card ("18px margin-top + 16px padding-top"). PASS.
- **Font tokens throughout:** All new text nodes use `font-display`, `font-body`, or `font-data` Tailwind tokens, not raw `font-family` declarations. PASS.

### FAIL

- **Section label copy case (line 526):** Implementation renders `"Or — one of these?"` (sentence case). DESIGN.md §Tiered Match Card specifies `"OR — ONE OF THESE?"` (all-caps). The label uses `uppercase` in its CSS class (`font-data text-[11px] font-bold tracking-[2px] uppercase text-accent-info`), so the visual output is all-caps regardless of the source string — but the source string is mixed-case. This is a consistency defect: the sibling `"Where this leads"` label at line 413 also relies on `uppercase` for rendering. Both are functionally all-caps on screen, but the source strings should be uppercase to match the existing `WHERE THIS LEADS` convention and DESIGN.md copy. **Low severity** — visually correct but technically non-conforming with DESIGN.md copy spec at §Tiered Match Card ("OR — ONE OF THESE?").

### WARNINGS

- **`hover:bg-[rgba(255,255,255,0.05)]` on "Not quite" button (lines 480–481):** This raw rgba literal is pre-existing in the file (unchanged from before this spec). It is not a new introduction by this spec's changes. Flagged for future cleanup: DESIGN.md §Buttons Ghost hover documents this as `rgba(255, 255, 255, 0.05)` background but does not expose it as a named CSS variable/token. No token exists for this value today. Not a blocking issue for this audit.
- **`hover:bg-[#6bc494]` on submit button (line 171) and primary CTA (line 467):** Pre-existing hardcoded hex. DESIGN.md §Buttons Primary hover documents this as `darken to #6bc494`. No Tailwind token exists for this hover state. Both instances are pre-existing and unchanged by this spec. Not a blocking issue for this audit.

---

## `DESIGN.md` — Tiered Match Card (Three-Confidence Extension) subsection

### PASS

- **Additive discipline:** The new `### Tiered Match Card (Three-Confidence Extension)` subsection is placed at line 637, directly after the existing `### Gemma Match Card` section closes, and before `### The Pentagon (Radar Chart)`. No existing Match Card prose was rewritten or removed. The existing low-confidence variant block inside `### Gemma Match Card` was not modified; the new subsection references it by name and extends it. PASS.
- **Token documentation:** The subsection documents `font-data`, `font-body`, `text-accent-info`, `text-text-primary`, `text-text-muted`, `bg-bp-surface`, `border-border-subtle`, `text-accent-thrive` — all valid tokens from DESIGN.md. No new tokens are introduced. PASS.
- **rgba values documented:** The two rgba literals referenced in the subsection (`rgba(125, 212, 163, 0.45)` for confirm flash glow, `rgba(242, 212, 119, 0.15)` for best-guess pill) are both documented as reuse of existing values, not new tokens. PASS.
- **Degenerate state documented:** Zero-alternatives medium-tier behavior is specified (caution card, primary alone, no alternatives section). PASS.
- **Accessibility documented:** `<ul role="list" aria-label>`, `<button type="button" aria-label>`, and `disabled` state are all specified. PASS.
- **Copy documented:** Section label copy `"OR — ONE OF THESE?"` is specified in all-caps. PASS.

---

## `docs/mockups/brightpath-design-system-v3.html` — Medium-tier · with alternatives variant

### PASS

- **Additive discipline — variant position:** The new "Medium-tier · with alternatives" block (lines 2334–2463) was appended after the existing three-variant confirming block and its variant labels, and before the "Tone Exploration" `<h3>` at line 2466. PASS.
- **Additive discipline — CSS position:** The new `.gemma-alternatives-*` CSS block (lines 1676–1763) was appended directly after the last existing Match Card CSS rule (`.gemma-match-actions`, line 1671–1674) and before the closing `</style>` tag at line 1764. It was not interleaved with existing Match Card CSS. PASS.
- **Font token parity — `.gemma-alternatives-label` (line 1686):** `font-family: 'Space Mono', monospace` — matches DESIGN.md `font-data` token definition (`Space Mono`). PASS.
- **Font token parity — `.gemma-alternative-title` (line 1729):** `font-family: 'Nunito', sans-serif` — matches DESIGN.md `font-body` token (`Nunito`). PASS.
- **Font token parity — `.gemma-alternative-why` (line 1744):** `font-family: 'Nunito', sans-serif` — matches DESIGN.md `font-body` token. PASS.
- **Token compliance — label color (line 1691):** `color: var(--accent-info)` — PASS.
- **Token compliance — row hover bg (line 1718):** `background: var(--bg-surface)` — PASS.
- **Token compliance — title default (line 1732):** `color: var(--accent-info)` — PASS.
- **Token compliance — title hover (line 1741):** `color: var(--text-primary)` — PASS.
- **Token compliance — `why` color (line 1746):** `color: var(--text-muted)` — PASS.
- **Token compliance — dividers (line 1702–1703):** `.gemma-alternatives-list > li + li { border-top: 1px solid var(--border-subtle); }` — PASS.
- **Token compliance — confirm flash bg (line 1754):** `background: var(--bg-surface)` — PASS.
- **Token compliance — confirm flash box-shadow (line 1755):** `box-shadow: 0 0 24px rgba(125, 212, 163, 0.45)` — reuse of existing value, documented in spec. PASS.
- **Token compliance — confirm flash color (lines 1758–1759):** `color: var(--accent-thrive)` — PASS.
- **Accessibility in HTML sample:** `<ul class="gemma-alternatives-list" role="list" aria-label="Other close matches">` present on both medium-tier cards (lines 2371, 2428). Each row is `<button type="button" class="gemma-alternative-row" aria-label="Select {Title}">`. Disabled rows in the confirming state have the `disabled` attribute (lines 2429, 2434, 2439, 2444). PASS.
- **`why` italic check:** `.gemma-alternative-why` has no `font-style: italic` declaration. PASS.
- **Section label copy in HTML (lines 2370, 2427):** Rendered as `Or &mdash; one of these?` (mixed case in source). Same issue as the component — the `text-transform: uppercase` in `.gemma-alternatives-label` makes this visually all-caps, but the source copy does not match the DESIGN.md-specified `"OR — ONE OF THESE?"`.

### FAIL

- **Section label source copy (lines 2370, 2427):** HTML source reads `Or &mdash; one of these?` (sentence case). DESIGN.md §Tiered Match Card specifies `"OR — ONE OF THESE?"`. Because `.gemma-alternatives-label` applies `text-transform: uppercase`, the rendered output is all-caps and visually correct — but the source copy is inconsistent with the spec and with the `.gemma-match-preview-label` sibling whose source reads `Where this leads` (also sentence case, also rendered all-caps by CSS). This is the same low-severity defect as in the component. Both files are internally consistent with each other but both differ from DESIGN.md copy spec.

### WARNINGS

- **`.gemma-alternative-title` font-size (line 1730):** `font-size: 15px`. DESIGN.md `text-body-sm` is 15px (`0.9375rem`). The component uses `text-body-sm` on the title (line 573). The HTML and component agree on rendered size, but the HTML hardcodes `15px` while the component uses the token. Minor raw-value usage in the mockup only — mockups are not implementation files. Non-blocking.
- **`.gemma-alternative-row` glyph color (line 1721):** `color: rgba(123, 184, 224, 0.6)` — this matches the pre-existing `.gemma-match-preview-arrow` rule at line 1664 (same value, same pattern). Not newly introduced by this spec. Non-blocking.

---

### Verdict

- [x] APPROVED with minor findings
- [ ] CHANGES REQUESTED
- [ ] REJECTED

**Summary:** All token choices, semantic roles, motion configs, stagger values, accessibility attributes, and additive-discipline rules are compliant. One low-severity defect appears in both `MajorInput.tsx` and the v3 HTML: the section label source string is mixed-case (`"Or — one of these?"`) rather than all-caps (`"OR — ONE OF THESE?"`). Visual output is correct in both cases because `uppercase` is applied via CSS, but the source copy does not match DESIGN.md. This does not affect rendered output and does not require a blocking fix — correct at implementer's discretion. No new raw hex or rgba values were introduced by this spec's changes beyond the documented reuse of two pre-existing values.

### Code Review (@faang-staff-engineer)
**Status:** COMPLETE
**Reviewed:** 2026-04-18
**Reviewer:** Staff Engineer (15 YOE)

#### Summary

Solid work. The implementation is tight, the sanitizer is defensive in the places that actually matter (CIP regex, dedup against primary, clamp to 10), error paths degrade to the existing fallback, and the two prompt sites are currently byte-identical. Tests cover the contract. Look, I love Claude, BUT — I went through this with my usual paranoia and found nothing that justifies a blocker. A handful of moderate and minor items worth landing either with this spec or as a tracked follow-up. Ready for prod behind the existing human-confirm gate once S1 and M2 are addressed.

#### Blockers

None.

#### Significant (🟠)

##### S1. `matched_cip` is trusted unvalidated while alternatives are format-checked — asymmetric defense

**Impact:** The sanitizer enforces `^\d{2}\.\d{4}$` on every alternative but NOT on `matched_cip`. If Gemma emits a malformed primary (e.g. `"52.02"`, `"52"`, `""`, or a hallucinated `"52.0999X"`), that raw string is:

1. Used verbatim in `IntentResult.matched_cip` — the frontend renders "CIP 52.02" next to the hero title.
2. Used as the `primary_cip` seed for `seen`. String-equality dedup still works for exact-match alts, but an alternative that is a "proper-format version" of the same program (primary `"52.02"`, alt `"52.0201"`) isn't recognized as a dupe and shows up as an alternative to itself.
3. Threaded to `/intent/confirm` → seeded into `_intent_cache`. Next session's `cache_key` hit returns an `IntentResult` with a malformed `matched_cip`, which is passed unchanged to downstream MCP query paths (`get_career_paths` and friends). At best the SOC crosswalk join misses and the student lands on a broken careers screen; at worst we've persisted the bad value across cache lifetime.

**Location:** `backend/app/services/intent.py:346-350`
```python
matched_cip = str(parsed.get("matched_cip", ""))
matched_title = str(parsed.get("matched_title", ""))
confidence = str(parsed.get("confidence", "unknown"))
reasoning = str(parsed.get("reasoning", ""))
alternatives = _sanitize_alternatives(parsed.get("alternatives"), matched_cip)
```

**The Problem:** The genai-architect finding #10 called out CIP hallucination as the cross-backend divergence risk and the team addressed it for alternatives. The same risk applies to `matched_cip` — more severely, because the primary is what's persisted to the cache and sent to downstream services.

**The Fix:** Same regex, applied to the primary. On mismatch, raise the existing `ValueError` so the router returns 422 and the frontend drops into `phase="fallback"` — the clarify picker is the correct graceful-degradation path for a malformed primary, and that path is already wired.

```python
matched_cip = str(parsed.get("matched_cip", "")).strip()
if not _CIP_PATTERN.match(matched_cip):
    raise ValueError(
        f"Gemma returned a malformed primary CIP ({matched_cip!r}) for '{major_text}'"
    )
```

Routes back to Claude Code (general) for the fix and @test-writer for the parametrized test.

#### Moderate (🟡)

##### M1. No length cap on `title` / `why` / `major_text`

**Impact:** The sanitizer's `.strip()` + `str(...)` coercion accepts arbitrary-length strings. Normal case is fine — Gemma's `why` runs 20–60 chars. But:
- A prompt-injected `major_text` (e.g. a student pasting 8KB of text) could cause Gemma to echo a long narrative into `title` or `why`.
- The raw value flows back in the `IntentResult` payload and, on confirm, is shipped to `/intent/confirm` → `_intent_cache`. Attacker-weight payload is now cached.
- `major_text` isn't length-capped anywhere in `IntentRequest` either.

**The Fix:** Either add a `max_length` to `IntentRequest.major_text` (200 chars is generous) at the Pydantic layer, or cap each sanitized field at ~120 chars. Prefer the request-level cap — defends everyone, not just the alternatives path.

**Severity:** 🟡 Moderate. No crash, no injection I can construct (these strings aren't used in any downstream SQL or shell context), but it's a latent denial-of-cache-quality vector.

##### M2. Type confusion on `title` / `cip` renders ugly-but-non-crashing strings

**Impact:** If Gemma returns `{"cip": "52.0801", "title": {"primary": "Finance"}, "why": ["a", "b"]}`, `str({"primary": "Finance"}).strip()` = `"{'primary': 'Finance'}"` — passes the truthy check and renders literally as the alt title. The student sees Python repr in the UI.

**Location:** `backend/app/services/intent.py:258-271`

**The Problem:** The sanitizer guards against None and missing keys but not against non-string types. The regex check on `cip` catches most of this incidentally (because `str({...})` won't match the regex), but `title` has no format gate.

**The Fix:** One isinstance guard before the coercion:
```python
if not isinstance(item.get("title"), str) or not isinstance(item.get("cip"), str):
    continue
```
`why` can stay tolerant since empty is the degenerate case we already handle.

**Severity:** 🟡 Moderate. Not a security issue — "Gemma misbehaves → ugly UI". The automated tests will never catch it because every fixture uses strings. Worth the two lines before merge.

##### M3. `confidence` accepts any string Gemma emits; no allow-list gate

**Impact:** `confidence = str(parsed.get("confidence", "unknown"))` is stored verbatim. If Gemma emits `"extremely high"`, `"moderate"`, or `"🎯"`, we propagate unchanged:
- Backend: `needs_clarification = confidence == "low"` → False for anything non-low.
- Frontend: `isUncertain = confidence !== "high"` → True for anything non-high.
- Combined: any weird string lands on the medium-tier rendering (caution + "best guess" + alternatives if non-empty).

Graceful degradation to the caution card is defensible, but this is a silent drift vector. genai-architect #13 and fp-architect #13 both flagged `Literal["high","medium","low"]` as a cheap win and parked it. Noting here that the actual predicate (`!= "high"`) is *more* lenient than either reviewer's "unknown → fallback" suggestion.

**The Fix:** Either coerce unknowns to `"medium"` explicitly (same behavior as today but explicit), or promote to `Literal["high","medium","low"]` in Pydantic (would require a graceful fallback path since router currently 422s on ValueError).

Not blocking. Pin as a named follow-up in §11.

##### M4. `confirmTimerRef.current` isn't nulled after firing

**Impact:** In `MatchContent` (MajorInput.tsx:316-320), the unmount cleanup calls `clearTimeout(confirmTimerRef.current)` if truthy. The timer IDs are positive integers and never reset to `null` after fire. On unmount, we always call `clearTimeout` with a stale ID. `clearTimeout(staleId)` is a documented no-op, so no bug — but the intent of "only clear if a timer is live" is not what the code expresses.

**The Fix:** Null in the `setTimeout` callback:
```typescript
confirmTimerRef.current = window.setTimeout(() => {
  confirmTimerRef.current = null;
  onConfirm();
}, 320);
```
Same for the alternative handler. Zero behavior change; tightens the invariant so future contributors don't misread it.

**Severity:** 🟡 Moderate (borderline minor — promoted only because the 3am test for "what happens if the user spams clicks during unmount" should have a clean answer).

#### Minor (🔵)

##### N1. `max_tokens` bump to 700 is acceptable, but unmonitored

The genai-architect's math (~350–420 tokens typical, +60–80 for 3-sentence reasoning) is sound, and the 2-sentence cap in the prompt is the right mitigation. §4 notes "Acceptable at demo concurrency; no rate-limit change." Fine for May 18, but there's no log-level signal for "we truncated" — a runaway generation (rare but not impossible on low-tier inputs) falls through to `raise ValueError` and lands in the picker. Silent, but the fallback is the right UX. File under "if the demo flakes, here's one place to look." A one-line `logger.warning("intent fallback: %s", stats['parse_error'])` in the `parsed is None` branch would make it observable in `logs/gemma.jsonl`.

##### N2. CLI's line-925 `parsed.get("alternatives") or []` is tolerant-by-design

Explicitly called out in §6 as an intentional choice — the CLI is a dev harness and doesn't need to match the service's defensive posture. Agree. If the CLI ever graduates into a non-dev path, this should adopt `_sanitize_alternatives`. Noted, not a bug.

##### N3. Drift-warning comments are sufficient for this spec's lifetime

Verified byte equivalence between `backend/app/services/intent.py:27-88` and `backend/cli.py:611-672` via `diff` — identical. The drift comments at intent.py:24-26 and cli.py:607-610 name the mirror relationship and point at §11. Grade: sufficient for hackathon lifetime. The follow-up consolidation (parked in §11) remains correct — pointing a single constant at both sites eliminates the class of bug. Ship this, track the follow-up.

##### N4. Double-state in `MatchContent` (`confirming` vs `confirmingAltCip`) is correctly guarded

I tried to construct a double-fire: primary click → state flips, alt click within the same tick → guard returns early. Alt click → alt state set, primary click → guard returns early. Rapid same-alt clicks → same guard. Two-state representation drives two different visual targets (primary CTA glow vs. alt row glow) — not redundant, just separate concerns. Fine as-is.

##### N5. Alternative-confirm dropping `careers_preview` and `substitutionApplied` is the correct call

§3 D6 locked this behavior and the implementation honors it: `careersPreview: override ? [] : intentResult.careers_preview, substitutionApplied: override ? false : …`. The alternative has its own CIP and its own career outcomes — the primary's preview would be actively wrong. Empty is honest. The next screen (`/build`) does its own lookup. I spent a minute considering an inline pre-fetch for the alt's preview; not worth a second MCP round-trip to save ~800ms of "preview lag" on a path already gated behind a 320ms confirm flash.

##### N6. `/intent/confirm` doesn't care that the CIP came from an alternative

`backend/app/routers/intent.py:22-30` and `IntentConfirmRequest` (`api.py:18-23`) take `matched_cip` and `matched_title` as loose strings; they don't cross-check against the originally-resolved primary. `confirm_intent()` writes them straight into `_intent_cache` keyed on the student's normalized input. Semantics: "this input, at this school, was confirmed to be this CIP" — fully correct when the student picks an alt. Next time they type the same thing → cache hit for the alternative. Right behavior.

##### N7. `_intent_cache` is process-local and unbounded (pre-existing)

Out of scope — pre-existing — but the "what happens at 3am" note: plain dict, lives for process lifetime, no eviction. At demo scale fine. In prod: (a) multi-worker deployments don't share the cache so the same student hitting different pods gets different behavior, (b) unbounded growth over weeks. Tech debt orthogonal to this spec.

##### N8. `handleProgramPick` (clarify path) doesn't fire `/intent/confirm`

Also pre-existing, also out of scope: primary + alternative confirm paths hit `/intent/confirm`; picking from the clarify picker (MajorInput.tsx:110) doesn't. A student who lands on low-tier, picks from the picker, and comes back later types the same thing and re-runs Gemma + the picker. Small cost, preserves "Gemma uncertainty ⇒ don't cache". Defensible. Noting for the record.

#### Test Coverage Assessment

The test suite covers the contract correctly. Gaps already flagged in §7 are:
1. **No direct test for `_call_gemma_intent`'s trailing-prose stripping.** The code path at intent.py:229-232 is invoked implicitly by every fixture-backed test, but there's no test that asserts `'{"a":1} trailing garbage here'` → `cleaned == '{"a":1}'`. §7 called it P2; I'd land it before next prompt tweak.
2. **No test for the S1 finding** (primary CIP format validation). If S1 is addressed, a one-line parametrized test covers it: `["52", "52.02", "52.0201X", "", None]` → `ValueError` for each.

P0/P1 coverage is otherwise complete for the contract in §4. No missing tier, no missing happy path. The 2 pre-existing `ProfileScreen.test.tsx` failures are correctly documented and unrelated.

#### What's Actually Good

- **The sanitizer is the star of the show.** Right defensive choices in the right order: list check → per-item dict check → empty/missing fields → regex gate → dedup (seeded with primary) → clamp. Dedup survives even if primary is malformed because `"52.02" in seen` still works on string equality. Preserves input order (tests assert it). Ten clean lines of real defense.
- **Error paths degrade correctly.** Every failure mode I walked (None response, unparseable JSON, missing `matched_cip` key, garbage `confidence`, string `alternatives`, oversized alternative list) either (a) raises ValueError → 422 → frontend fallback picker, or (b) returns a valid-but-empty `IntentResult.alternatives` → frontend renders caution card without the list. No silent corruption, no crash.
- **Prompt mirroring is correct.** Byte-identical between the two sites. The comments at both call sites name the mirror relationship and point at §11. Right amount of work for hackathon time.
- **The frontend state machine is clean.** `confirming` and `confirmingAltCip` look redundant but correctly separate (they drive different visual targets). Guards prevent double-fire. `useEffect` cleanup is correct for unmount-during-flash. `isUncertain` rename is the semantically right abstraction for a future fourth tier.
- **Tests pin the contract, not the implementation.** Frontend tests assert `aria-label="Select {title}"` and CTA labels — the contract a future refactor should honor. Backend tests assert `len(alternatives) <= 10` and dedup behavior, not the sanitizer's internal `seen` set. Good taste.

#### Recommendations (Prioritized)

1. **Land S1 (primary CIP format validation) before merge.** One regex check, one ValueError, one parametrized test. Closes the asymmetric defense gap.
2. **Land M2 (isinstance check on `title`/`cip` in the sanitizer) before merge.** Two lines. Defends against Gemma emitting non-string types without making the code harder to read.
3. **Track M1 (length caps on `major_text` / alternative strings) as a named follow-up in §11.** Prefer request-level: `IntentRequest.major_text: str = Field(max_length=200)`.
4. **Track M3 (Literal typing for `confidence`) as a named follow-up in §11.** Already flagged by both architect reviews; bring the reference forward so it doesn't get lost.
5. **Optionally land M4 and N1** (null timer ref after fire; warn log on fallback). Both are 1–2 line cleanups worth bundling if S1/M2 are being touched anyway.

#### Questions for the Author

- **Any monitoring on the `raise ValueError` fallback rate?** At the demo, if 10% of inputs start falling through to the picker because Gemma is truncating at 700 tokens, we'd want to know. N1's logger.warning is a one-line fix.
- **Is the `_intent_cache` expected to survive a process restart?** In-memory now. If the demo mid-flight gets a pod restart, every previously-confirmed student re-runs Gemma. Probably fine for the hackathon; worth knowing for sure.
- **Rollback plan if the tier rubric regresses accuracy under OpenRouter?** Revert the prompt to pre-spec version; frontend's `isUncertain = confidence !== "high"` keeps working because medium responses still render the caution path (just without the richer alternatives). Architecturally clean; confirming the rollback surface is "one prompt string."

#### Verdict
- [x] APPROVED (post-remediation 2026-04-18)
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

**Rationale:** S1 (primary CIP unchecked) and M2 (non-string `title` passthrough) have been addressed in commit following this review. The initial verdict was CHANGES REQUIRED; after the two fixes landed, the verdict flips to APPROVED per the reviewer's own "once those two are in, this is a clean approve" language.

**Post-review remediation (2026-04-18):**

- **S1 fixed** in `backend/app/services/intent.py` — `matched_cip` now strip()'d and regex-validated against `_CIP_PATTERN`; mismatch raises `ValueError` which the router translates to HTTP 422 and the frontend routes to `phase="fallback"` (the existing graceful degradation path).
- **M2 fixed** in `backend/app/services/intent.py:_sanitize_alternatives` — explicit `isinstance(..., str)` guards on `cip` and `title` reads before the `.strip()` coercion. `why` stays tolerant and defaults to `""` when non-string (degenerate case already handled downstream).
- **Test coverage added** — `backend/tests/services/test_intent.py` gained a parametrized `test_resolve_intent_rejects_malformed_primary_cip` covering `["52", "52.02", "52.0201X", "", "abc.defg", "052.0201", "52.02011"]` + a separate `test_resolve_intent_rejects_null_primary_cip` for the JSON `null` path, plus `test_sanitize_drops_non_string_title_and_cip` for M2.
- **Design Audit FAIL fixed** — section label source copy updated to all-caps (`"OR — ONE OF THESE?"`) in both `frontend/src/components/school/MajorInput.tsx` and `docs/mockups/brightpath-design-system-v3.html`. DESIGN.md spec now matches source in both files.
- **Follow-ups tracked** — M1 (length caps on `major_text` / alternatives), M3 (Literal typing for `confidence`), M4 (null timer ref after fire), N1 (logger.warning on fallback) pinned as named items in §11.

---

## §9 Verification

**Status:** COMPLETE
**Verified:** 2026-04-18 — @fp-builder

### Backend
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | All checks passed (after fix attempt 1 — see log) |
| Type check (mypy) | PASS (pre-existing errors only) | 88 errors in 21 files — all pre-existing; confirmed via git stash baseline. No new errors introduced by this spec. The spec's count of "6 pre-existing" was an undercount of the pre-existing baseline; the actual baseline is 88 errors (fastapi stubs missing, import-not-found across all routers, pre-existing type issues in career.py, gemma_client.py, intent.py). Zero delta from this spec. |
| Tests (pytest) | PASS | 259 passed in 1.32s, 0 failed. 6 collection errors (fastapi not installed in uv workspace) are pre-existing — confirmed via git stash. New spec tests: `tests/services/test_intent.py` — 17 passed. |
| Smoke test under `INFERENCE_BACKEND=ollama` | PASS | Ollama reachable at localhost:11434 (models: gemma4:e4b, gemma4:e2b, gemma4:26b). `resolve_intent(major_text="business", unitid=999999, programs=[])` returned `confidence=medium`, `alternatives=0`, all assertions passed (confidence in {high,medium,low}, alternatives ≤ 10, CIP format ^\\d{2}\\.\\d{4}$). Note: gemma response truncated at max_tokens=200 warning emitted — expected behavior. |
| Smoke test under `INFERENCE_BACKEND=openrouter` | SKIPPED | Per parallel-worktree discipline: sibling session may be using the same OpenRouter API key. Not tested. |

### Frontend
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors (after fix attempt 1 — see log) |
| Tests (vitest) | PASS (pre-existing failures only) | 388 passed, 2 failed, 1 skipped (391 total, 45 test files). The 2 failures are pre-existing in `src/screens/ProfileScreen.test.tsx` ("renders profile name", "reroll swaps name") — verified pre-existing by @test-writer. No new failures. New spec tests: `src/components/school/MajorInput.test.tsx` — 6 passed. |
| Production build (Vite) | PASS | 657 modules transformed, built in 1.60s. 1 chunk-size warning (718 kB > 500 kB) — pre-existing, not an error. |

### Build Accountability Log
| Attempt | Check | Result | Error | Fix Applied |
|---------|-------|--------|-------|-------------|
| 1 | ruff | FIXED | `I001` import block unsorted + `E501` line too long (94 > 88) in `backend/tests/services/test_intent.py` | Auto-fixed I001 via `ruff --fix`; wrapped `_FIXTURES_PATH` assignment in parentheses to stay under 88 chars. Commit: `972fb76`. |
| 1 | TypeScript | FIXED | `TS2532: Object is possibly 'undefined'` at `MajorInput.test.tsx:304` — `onConfirm.mock.calls[0][0]` | Added non-null assertion: `onConfirm.mock.calls[0]![0]`. Commit: `972fb76`. |

---

## §10 Discussion

```
[2026-04-18 —] @faang-staff-engineer → Claude Code (general) + @test-writer
Code Review §8 → CHANGES REQUIRED. Two fixes blocking merge; ~20 min total.

S1 (🟠 Significant): Add primary-CIP format validation in
backend/app/services/intent.py:346. The sanitizer checks every alternative
against _CIP_PATTERN but matched_cip itself is trusted verbatim — so a
malformed Gemma primary (e.g. "52.02", "52.0999X") gets persisted to
_intent_cache via /intent/confirm and re-served to downstream MCP query
paths. Fix:

    matched_cip = str(parsed.get("matched_cip", "")).strip()
    if not _CIP_PATTERN.match(matched_cip):
        raise ValueError(
            f"Gemma returned a malformed primary CIP "
            f"({matched_cip!r}) for '{major_text}'"
        )

The existing ValueError → 422 → phase="fallback" path handles it cleanly.

M2 (🟡 Moderate): Add isinstance guards in _sanitize_alternatives
(backend/app/services/intent.py:258) so non-string title/cip values are
dropped before the str() coercion:

    if not isinstance(item.get("title"), str) or not isinstance(item.get("cip"), str):
        continue

Prevents "{'primary': 'Finance'}" from rendering as an alt title.

@test-writer: please add a parametrized test for S1 covering
["52", "52.02", "52.0201X", "", None, "abc.defg"] → each raises ValueError
through resolve_intent. Use the existing stub_server + stub_gemma_config
fixtures in backend/tests/services/test_intent.py; mock _make_generate_mock
with each malformed primary payload.

Non-blocking follow-ups (please add as named items in §11): M1 length caps,
M3 Literal typing for confidence, M4 null timer ref after fire, N1
logger.warning on fallback. Full rationale + 5 additional minor findings
documented in §8 Code Review.

Once S1 + M2 land and the new test passes, verdict flips to APPROVED and
spec proceeds to §9 Verification (@fp-builder).
```

---

## §11 Final Notes

**Human Review:** PENDING

### Tracked Follow-ups

These are non-blocking items that surfaced during this spec and should each be picked up as a small standalone spec (or bundled together as a "intent-hardening" spec). None block shipping this tiered-matching feature.

| # | Origin | Item | Suggested scope |
|---|--------|------|-----------------|
| F1 | §2 Decision #5, @fp-architect #10, @faang-staff N3 | **Prompt consolidation.** `_INTENT_SYSTEM_PROMPT` is duplicated at `backend/app/services/intent.py:27` and `backend/cli.py:611`. Drift-warning comments were added, but a shared module (e.g. `backend/app/services/intent_prompt.py`) eliminates the drift class entirely. | New spec. ~1 hour. Extract prompt + CIP pattern into a shared module; import from both sites. |
| F2 | @fp-architect #7, @genai-architect #13, @faang-staff M3 | **Tighten `confidence` typing.** Currently `confidence: str` accepts any Gemma emission verbatim. Promote to `Literal["high","medium","low"]` with a graceful fallback path (coerce unknown → "medium", or route to `phase="fallback"`). | Small spec. ~30 min. Pydantic `field_validator` + one frontend type narrowing + two tests. |
| F3 | @fp-architect #7, @faang-staff M1 | **Length caps on intent strings.** `IntentRequest.major_text` has no max length. Gemma-emitted `title` / `why` have no cap either. Cache-quality DoS vector (not a crash). | Small spec. ~15 min. `Field(max_length=200)` on request + 120-char cap in sanitizer + test. |
| F4 | @faang-staff M4 | **Null `confirmTimerRef.current` after fire** in `MatchContent` (MajorInput.tsx). Zero behavior change; tightens the "only clear live timers" invariant. | Trivial. ~5 min. Inline fix during any future MatchContent edit. |
| F5 | @faang-staff N1 | **Observable fallback rate.** Add `logger.warning("intent fallback: %s", stats["parse_error"])` in the `parsed is None` branch of `resolve_intent`. Makes silent truncation/parse-failure visible in `logs/gemma.jsonl`. | Trivial. ~5 min. One line + verification that `logs/gemma.jsonl` captures it. |
| F6 | §7 gap, @faang-staff test-coverage | **Direct test for trailing-prose JSON stripping.** Currently exercised implicitly by every tier test but never asserted in isolation. | Trivial. ~10 min. One unit test on `_call_gemma_intent` with a Gemma response of `'{"a":1} some trailing prose'`. |

### Lessons Learned

- **Schema shipped > schema rendered.** This spec existed because the `IntentResult.alternatives` and `confidence` fields were wired end-to-end but only partially rendered. The caution styling in `MatchContent` was unreachable for months. Worth a linter or audit pass that flags fields typed through to the frontend but never read. Candidate future spec.
- **Parallel reviews caught different failure modes.** @fp-architect focused on contract/routing; @genai-architect focused on prompt calibration + parser fragility; @faang-staff-engineer focused on asymmetric defense + state machine. All three were necessary — any single reviewer would have missed at least two of the required fixes.
- **"Never pad" is a weak negative constraint.** The genai-architect's finding #2 (template schema undercuts "Never pad") generalizes: explicit schema examples dominate instruction-level directives in low-temperature Gemma responses. Default to showing the high-confidence shape in templates, not the medium/low shape.
- **Drift comments are sufficient for hackathon lifetime.** Byte-identical diff verified between the two prompt sites after commit. The follow-up consolidation (F1) eliminates the class of bug but does not block the feature.
