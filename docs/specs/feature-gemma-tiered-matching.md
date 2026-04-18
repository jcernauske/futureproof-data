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
```

---

## Status: DRAFT

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-18 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-18 |
| Blocked By | — |
| Related Specs | `docs/specs/completed/cip-intent-substitution.md`, `docs/specs/completed/spike-gemma-intent-resolution.md`, `docs/specs/completed/spike-gemma-intent-openrouter.md` |

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

- [ ] Gemma's response emits `confidence` in `{"high","medium","low"}` and an `alternatives` array whose length is zero for high, 2–4 for medium, and may contain up to 10 for low (driven by the prompt, not post-processed).
- [ ] The frontend renders three visually distinct paths:
   - `high` → existing purple match card, one match, `"That's right"` button.
   - `medium` → caution (yellow) match card, one primary match + 2–4 visible alternatives, `"Close enough"` button, `"best guess"` pill.
   - `low` → existing clarify picker (program list), unchanged.
- [ ] No low-confidence result ever renders the match card (routed to clarify as today).
- [ ] No high-confidence result ever shows alternatives (clean card, same as today).
- [ ] Clicking an alternative in the medium-tier card confirms it just like the primary match (same `onConfirm` handoff, same `/intent/confirm` API call).
- [ ] Backend tests cover all three tiers + the alternative-count contract.
- [ ] Frontend tests cover all three rendering paths + alternative selection.
- [ ] `DESIGN.md` §Gemma Interactions documents the tiered rendering pattern.
- [ ] v3 HTML mockup (`docs/mockups/brightpath-design-system-v3.html`) shows a medium-tier card with alternatives alongside the existing default/caution/confirming variants.
- [ ] Both `backend/app/services/intent.py` and `backend/cli.py` use aligned prompts — no drift between web and CLI behavior.

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

> `@fp-design-visionary` fills this section during the DESIGN VISION step. What's below is scope + tokens, not pixel spec.

### In Scope

Three rendering paths inside `MajorInput` after Gemma resolves:

1. **High-tier match card** — *unchanged* from current production.
2. **Medium-tier match card** — NEW pattern. Extends the Match Card base with an inline alternatives list below the primary match, above the actions row.
3. **Low-tier clarify picker** — *unchanged*.

### Reference Material

- `DESIGN.md` §Gemma Interactions (all three tones are already documented: insight default, caution low-confidence → now medium, thrive confirming)
- `docs/mockups/brightpath-design-system-v3.html#gemma` (existing default + caution + confirming variants + tone gallery)
- `frontend/src/components/school/MajorInput.tsx` MatchContent component (existing implementation to extend)

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
| Alternative row text default | `text-accent-info` |
| Alternative row text hover | `text-text-primary` |
| Alternative row hover bg | `bg-bp-surface` |
| Row divider | `border-border-subtle` |
| Primary CTA (medium) | `bg-accent-thrive` label = "Close enough" |

### Visionary Must Answer

- Section-label text for the alternatives list — proposed: `"OTHER CLOSE MATCHES"`. Alternative: `"OR MAYBE ONE OF THESE"`.
- How each alternative row renders the `why` field: inline (truncated on overflow) vs. on-hover tooltip vs. omitted entirely. Default proposal: inline right-aligned, `font-body text-small text-text-muted`, truncated at ~50 chars.
- Whether to show the CIP code next to each alternative title (proposal: no — clutter. Only primary match shows CIP).
- Mobile responsive behavior: alternatives stack vertically as today; confirm touch targets ≥44px.
- Entrance animation: alternatives stagger in after primary title, using existing `stagger.fast` (50ms). Same pattern as career preview today.
- Confirmation interaction for an alternative: identical to primary (thrive flash 320ms → onConfirm handoff).

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Medium-tier match card | `region-gemma-match` | `role="region"` | `"Gemma's match with alternatives"` |
| Alternatives list | `list-gemma-alternatives` | `<ul>` | `"Other close matches"` |
| Individual alternative button | `btn-alternative-{cip}` | `<button>` | `"Select {title}"` |
| "best guess" pill | (stays as-is) | `<span>` | existing |

### Responsive

Desktop: medium card max-width unchanged from high card (same container). Alternatives list inherits card width.
Mobile: same — alternatives stack full-width within the card.

### Visionary Deliverable

- ASCII mockups for medium-tier card (default, hover on alt, confirming-alt-flash)
- Motion spec (stagger timing, hover transitions, confirm flash)
- Token-mapped component tree

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

**`backend/app/services/intent.py` prompt rubric (replaces current `_SYSTEM_PROMPT` alternative-count paragraph):**

New instruction block to insert into the system prompt:

```
Confidence tiers drive how many alternatives you return.

- "high": The input maps to exactly one CIP — no ambiguity. Return alternatives: [].
  Examples: "Physical Therapy" → 51.2308; "Nursing RN" → 51.3801.

- "medium": The input is a well-known shorthand or umbrella term that maps to a primary
  CIP but reasonable students mean different things. Return 2–4 alternatives, ordered
  by how likely you'd pick each if the student had phrased it differently. Each alternative
  must be a genuinely distinct program within the same CIP family.
  Examples: "business" (primary: 52.0201 Business Administration; alternatives: 52.0801
  Finance, 52.1401 Marketing, 52.0701 Entrepreneurship); "psychology" (primary: 42.0101
  Psychology General; alternatives: 42.2701 Cognitive Psychology, 42.2813 Clinical Psych).

- "low": The input is too vague, ambiguous, or non-program-like for you to stake a primary
  match confidently. Still return your best primary, but include up to 10 alternatives
  spanning the plausible CIP neighborhoods. The frontend will show a picker rather than
  your primary.
  Examples: "helping people", "something with computers but not coding".

Never pad. If you're high-confident, alternatives stays empty. Never exceed 10.
```

**`backend/app/services/intent.py:resolve_intent` — post-parse validation (additive, ~3 lines):**

```python
raw_alts = parsed.get("alternatives") or []
alternatives = raw_alts[:10] if isinstance(raw_alts, list) else None
```

(Replace the current `alternatives = parsed.get("alternatives")` assignment.)

**`backend/cli.py` prompt** — mirror the exact rubric above into the duplicate prompt string near line 620.

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
**Status:** PENDING
#### Findings
[Filled in by @fp-architect]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @genai-architect Review
**Status:** PENDING
#### Findings
[Filled in by @genai-architect — prompt design for tiered alternative count, calibration risks, fallback behavior under JSON parse failure]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline, crosswalk, or stat formula changes)

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
**Status:** PENDING
[Token compliance, Gemma Interactions family adherence, no raw rgba/hex introduced]

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Filled in by reviewer]
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
| Lint (ruff) | |
| Type check (mypy) | |
| Tests (pytest) | |
| Smoke test under `INFERENCE_BACKEND=ollama` | |
| Smoke test under `INFERENCE_BACKEND=openrouter` | |

### Frontend (@fp-builder)
| Check | Result |
|-------|--------|
| TypeScript | |
| Tests (vitest) | |
| Production build (Vite) | |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §10 Discussion

```
[YYYY-MM-DD HH:MM] @source-agent → @target-agent
Message content.
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items. Note whether prompt consolidation between `intent.py` and `cli.py` should be the next refactor spec.]
