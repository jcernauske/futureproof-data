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

## Status: IN_PROGRESS

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
