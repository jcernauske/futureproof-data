# Feature: Multi-CIP Resolution

## Claude Code Prompt

```
Read the spec at docs/specs/feature-multi-cip-resolution.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (system architecture, data flow, Gemma prompt changes, API contracts)
   - Write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. DESIGN VISION (UI)
   - Invoke @fp-design-visionary to propose the premium CIP picker UI
   - Visionary writes to §3 (UI/UX Design): layout, interactions, Brightpath token usage, responsive behavior
   - §3 becomes the pixel-perfect implementation target
   - Invoke @genai-architect for Gemma prompt/schema review (writes to §10)

3. IMPLEMENTATION
   - Implement the spec as written in §3 (UI/UX) and §4 (Technical Spec)
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly
   - DURING coding: Update any broken tests listed in "Authorized Test Modifications"
   - CRITICAL: If any test NOT in the "Authorized Test Modifications" list fails, STOP and escalate to human
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)
   - If still broken after 3 attempts: escalate to human via §10 Discussion

4. TESTING
   - Invoke @test-writer to review the full spec
   - @test-writer MUST review §4 Testing Impact Analysis
   - Implement all tests listed in "New Tests Required" by priority (P0 first)
   - Backend tests: pytest in backend/tests/
   - Frontend tests: vitest in frontend/src/**/*.test.ts(x)
   - Run ALL tests to catch regressions
   - If still broken after 3 attempts: escalate to human via §10 Discussion

5. DESIGN AUDIT (UI)
   - Invoke @design-builder for mechanical token/pattern compliance against Brightpath design system
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
   - Generate report to reports/feature-multi-cip-resolution-YYYY-MM-DD.md
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
| DESIGN AUDIT | @design-builder checking token compliance |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-21 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-21 |
| Blocked By | — |
| Related Specs | `docs/specs/completed/feature-set-your-course.md`, `docs/specs/feature-chip-dispatch-mcp-tool-calling.md`, `docs/specs/feature-intent-aware-tiering.md` |

---

## §1 Feature Description

### Overview

Modify the Set Your Course resolution flow so Gemma returns up to 3 ranked CIP matches instead of 1 when a student's search term maps to multiple programs at their school. The student sees ranked options, picks one, and continues into the existing career reveal flow.

### Problem Statement

Today, when a student types a broad term like "engineering" at Purdue (which offers 14 engineering programs), Gemma picks a single CIP and the student never sees the alternatives. This is a problem because outcomes vary significantly across programs at the same school — Computer Engineering (ERN 9.7, $76K first-year earnings) outperforms Civil Engineering (ERN 7.3, $66K) by $10K/yr, but the student has no visibility into that. The current single-pick design also forces Gemma to make an opinionated choice it shouldn't have to make when the input is genuinely ambiguous.

Data analysis confirms the feature is viable:
- Median CIPs per family per school: **1** (graceful degradation — most searches return 1 option)
- Average: **2.0** (top-3 cap rarely truncates)
- Schools like Purdue have **14 engineering CIPs** — exactly where ranking matters most
- Gemma already sees the full school program list in her prompt (114 programs for Purdue)

### Success Criteria

- [ ] Gemma's resolution prompt returns up to 3 ranked CIP matches with per-option reasoning
- [ ] When only 1 CIP matches, the UX is unchanged from today (no picker, no extra UI)
- [ ] When 2-3 CIPs match, options appear as selectable elements; tapping one swaps the resolution and refetches career outcomes
- [ ] When more options exist beyond the top 3, a `remaining_count` is surfaced with a narrowing hint (e.g., "11 more programs match — try a more specific search")
- [ ] `matched_cip` / `matched_title` remain populated as the primary (first-ranked) option for backwards compatibility
- [ ] The fallback resolver (`_fallback_resolve`) also returns multi-CIP when applicable
- [ ] All existing tests pass (no regressions in the core Set Your Course flow)
- [ ] Zero taxonomy leakage: no CIP codes, SOC codes, or internal jargon visible to students
- [ ] Works under both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter`

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Cap at 3 options, not 5 or unlimited | Data shows median 1, avg 2.0 CIPs per family per school. 3 covers >95% of cases without overwhelming the student. | Unlimited (overwhelming UX), 5 (rarely that many, wastes prompt tokens) |
| 2 | Keep `matched_cip`/`matched_title` as primary for backwards compat | Every downstream consumer (chip dispatch, commit, outcomes fetch, tiering) reads `matched_cip`. Changing the contract is a full-stack break. | Replace with array-only (massive blast radius), new field name (confusing dual contract) |
| 3 | Repurpose existing `alternatives` field on `IntentResult` | Field already exists on both backend model and frontend type with shape `list[{cip, title, why}]`. Currently populated for low/medium confidence but not rendered on Set Your Course. Reusing it avoids new schema fields. | New `matched_cip_options` field (adds schema surface), `ranked_matches` (same problem) |
| 4 | Lazy-fetch outcomes (fetch only for selected CIP) | Eager-fetching 3 sets of career outcomes triples MCP calls and Gemma load. Most students will accept the primary. | Eager-fetch all 3 (3x API cost, latency), prefetch on hover (complexity) |
| 5 | Selection happens client-side by swapping `currentResolution` | No new backend endpoint needed. The frontend already has the CIP, title, and parent_cip for each alternative. Swapping the resolution and refetching outcomes uses the existing `useSetYourCourse` flow. | New `POST /intent/pick-cip` endpoint (unnecessary round-trip), WebSocket (overkill) |
| 6 | Include `remaining_count` and `narrowing_hint` in Gemma response | Lets the UI tell students "11 more programs match" without fetching them. The hint is Gemma-generated so it's natural language. | Frontend counts (doesn't have access to full match set), no hint (student doesn't know to narrow) |
| 7 | Ranking by Gemma's semantic judgment, not by ERN/earnings | Gemma should rank by relevance to the student's input, not by outcome quality. "engineering" → Computer Engineering first because it's the most canonical match, not because it earns more. Outcome data appears after selection. | Rank by ERN (biases toward high-paying fields), rank by alphabetical (useless) |
| 8 | Fallback resolver also returns multi-CIP | The `_fallback_resolve` path (used when streaming fails) should match the same contract. Otherwise the frontend has to handle two different shapes. | Fallback stays single-CIP (inconsistent contract, frontend branching) |

### Constraints

- The Gemma resolution prompt is already ~100 lines of tuned instructions; multi-CIP changes must be surgical, not a rewrite
- The `---INTENT_JSON---` delimiter + JSON tail format is shared with the fallback resolver
- `CIPCODE` is always a string type (XX.XXXX format) — never float
- Zero taxonomy leakage to students: no CIP codes, SOC codes, "crosswalk", or numeric codes in UI

### Out of Scope

- **Reverse SOC→CIP lookup** ("I want to be a nurse — what should I study here?") — related future feature, different entry point
- **Outcome comparison view** (side-by-side career outcomes for 2-3 CIPs) — potential follow-on after this ships
- **Gemma-ranked by outcome quality** — this spec ranks by semantic relevance; outcome-aware ranking is a separate feature
- **Chip dispatch changes** — chips still operate on the single selected `currentResolution`; no multi-CIP chip routing
- **Analytics logging of which option was picked** — desirable but not required for MVP; can be added via `record_commit` in a follow-on

---

## §3 UI/UX Design

> @fp-design-visionary fills this section BEFORE implementation begins. This becomes the pixel-perfect target.

### Scope for Visionary

The visionary should design:

1. **CIP picker** — rendered below the resolved program when `alternatives` has 1-2 entries. Shows the primary (selected) and alternatives as selectable elements. Each option shows the program title and a brief reason. No CIP codes visible.
2. **Remaining count hint** — when `remaining_count > 0`, a subtle line below the picker: "11 more programs match — try a more specific search" (or similar). Uses `narrowing_hint` from Gemma.
3. **Selection interaction** — tapping an alternative swaps it to primary (with animation). Career tiles below refetch and re-render.
4. **Graceful degradation** — when only 1 CIP matches, no picker renders; UX is identical to today.

### Design Token References

- Background: `surface-card` for picker container
- Text: `text-primary` for selected option, `text-secondary` for alternatives
- Accent: `accent-primary` for selected indicator
- Typography: `font-body` for option titles, `font-caption` for reasoning text
- Motion: Framer Motion for selection swap animation
- Responsive: picker stacks vertically on mobile

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| CIP option (primary) | `cip-option-primary` | button | "Selected program: {title}" |
| CIP option (alt 1) | `cip-option-alt-0` | button | "Alternative program: {title}" |
| CIP option (alt 2) | `cip-option-alt-1` | button | "Alternative program: {title}" |
| Remaining hint | `cip-remaining-hint` | p | "{count} more programs match" |

---

## §4 Technical Specification

### Architecture Overview

This feature modifies the Gemma resolution layer (prompt + JSON parsing) and the frontend display layer. The data is already present — `program_career_paths` contains the full CIP×SOC×school join, and Gemma already receives the full school program list in her prompt context. The change is: ask Gemma to return 3 instead of 1, parse the richer response, surface the options in the UI, and let the student pick.

The downstream flow (outcomes fetch, tiering, commit, chip dispatch) is unchanged — it still operates on a single `matched_cip` from `currentResolution`. Selection happens client-side by swapping which alternative becomes the primary.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/models/career.py` | Modify | Add `remaining_count: int = 0` and `narrowing_hint: str = ""` to `IntentResult`. The existing `alternatives: list[dict] \| None` field is repurposed (no schema change needed). |
| `backend/app/services/set_your_course.py` | Modify | Update `_STREAM_INTENT_SYSTEM_PROMPT` to request 3 ranked CIPs. Update `_FALLBACK_JSON_SYSTEM` to match. Modify JSON tail parsing in the `structured` event builder to extract array and populate `alternatives`, `remaining_count`, `narrowing_hint`. |
| `backend/app/services/intent.py` | Modify | Call `_promote_to_leaf_cip` and `_get_career_titles_for_cip` for each alternative CIP (loop, not just primary). Update `_sanitize_alternatives` to validate all entries against crosswalk/school catalog. |
| `frontend/src/types/buildInput.ts` | Modify | Add `remaining_count?: number` and `narrowing_hint?: string` to the `IntentResult` interface. No change to `alternatives` shape — already `Array<{ cip: string; title: string; why: string }>`. |
| `frontend/src/hooks/useSetYourCourse.ts` | Modify | Add `onPickAlternative(index: number)` callback: swaps the selected alternative into `currentResolution` (matched_cip, matched_title, parent_cip), clears tiered careers, triggers outcomes refetch. |
| `frontend/src/screens/SetYourCourseScreen.tsx` | Modify | Render CIP picker when `currentResolution.alternatives?.length > 0`. Render remaining count hint when `currentResolution.remaining_count > 0`. Wire tap handler to `onPickAlternative`. |
| `frontend/src/store/buildInputStore.ts` | Modify | No new state fields needed — `currentResolution` already holds `alternatives`. Selection is handled by swapping `matched_cip`/`matched_title` on the existing `IntentResult` object. |
| `backend/tests/fixtures/intent_responses.json` | Modify | Add multi-CIP fixture entries for test consumption. |

### Data Model Changes

**`IntentResult` (backend/app/models/career.py, line 324)**

```python
class IntentResult(BaseModel):
    matched_cip: str                          # PRIMARY (first-ranked)
    matched_title: str                        # PRIMARY
    confidence: str
    reasoning: str = ""
    careers_preview: list[str] = Field(default_factory=list)
    audit_flag: str | None = None
    audit_message: str | None = None
    needs_clarification: bool = False
    alternatives: list[dict] | None = None    # REPURPOSED: now populated with ranked options 2-3
    parent_cip: str = ""
    confirmed_focus: str | None = None
    student_major_text: str = ""
    intent_keywords: list[str] = Field(default_factory=list)
    remaining_count: int = 0                  # NEW: how many more CIPs matched beyond top 3
    narrowing_hint: str = ""                  # NEW: Gemma-generated hint for narrowing search
```

The `alternatives` list entries use the existing shape: `{"cip": str, "title": str, "why": str}`. The `why` field carries Gemma's per-option reasoning (e.g., "Closest semantic match for 'engineering'").

Each alternative also includes `parent_cip: str` so the frontend can construct the correct `parentCipOrMatched` when swapping:
```python
{"cip": "14.09", "title": "Computer Engineering", "why": "...", "parent_cip": "14.09"}
```

**Frontend `IntentResult` (frontend/src/types/buildInput.ts, line 64)**

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
  alternatives: Array<{ cip: string; title: string; why: string; parent_cip?: string }> | null;
  parent_cip: string;
  school_reported_cip: string;
  confirmed_focus: string | null;
  student_major_text: string;
  intent_keywords: string[];
  remaining_count?: number;       // NEW
  narrowing_hint?: string;        // NEW
}
```

### Service Changes

#### `backend/app/services/set_your_course.py`

**Gemma prompt changes (`_STREAM_INTENT_SYSTEM_PROMPT`)**

Add to the JSON output format instruction (currently requests a single `matched_cip`):

```
If the student's input matches multiple programs at this school, return
up to 3 ranked matches. Rank by semantic relevance to the student's input
(not by outcome quality — that comes later).

Your JSON tail format:
---INTENT_JSON---
{"matched_cip": "XX.XXXX", "matched_title": "Primary Match Title",
 "confidence": "high|medium|low", "reasoning": "...",
 "parent_cip": "XX.XX",
 "alternatives": [
   {"cip": "XX.XXXX", "title": "Second Match", "why": "Also matches because...", "parent_cip": "XX.XX"},
   {"cip": "XX.XXXX", "title": "Third Match", "why": "Also matches because...", "parent_cip": "XX.XX"}
 ],
 "remaining_count": 11,
 "narrowing_hint": "Try 'mechanical engineering' or 'aerospace' to narrow it down",
 "intent_keywords": ["engineering"]}

Rules for alternatives:
- Only include alternatives when 2+ distinct programs genuinely match the input
- Each alternative's "cip" MUST exist in the candidate CIP lists above
- Do NOT include alternatives that are just degree-level variants of the primary (e.g., BS vs MS in the same field)
- "remaining_count" = total matching CIPs minus however many you listed (primary + alternatives). 0 if you listed them all.
- "narrowing_hint" = a plain-English suggestion for how the student could narrow their search. Omit if remaining_count is 0.
- If only 1 program matches, omit "alternatives", set "remaining_count": 0, omit "narrowing_hint".
```

**JSON tail parsing (structured event builder, ~line 579)**

Update `_build_intent_result_from_tail` or equivalent:

```python
def _build_intent_result(parsed: dict, school_cips: list[dict], ...) -> IntentResult:
    # Primary CIP (unchanged)
    matched_cip = str(parsed.get("matched_cip", "")).strip()
    matched_cip = intent._promote_to_leaf_cip(matched_cip, raw_parent, school_cips)
    
    # Alternatives (new)
    raw_alts = parsed.get("alternatives") or []
    validated_alts: list[dict] = []
    for alt in raw_alts[:2]:  # Cap at 2 alternatives (3 total with primary)
        alt_cip = str(alt.get("cip", "")).strip()
        if not _CIP_PATTERN.match(alt_cip):
            continue
        alt_cip = intent._promote_to_leaf_cip(alt_cip, alt.get("parent_cip", ""), school_cips)
        # Validate against crosswalk/school catalog (same logic as primary)
        if alt_cip not in valid_6digit and alt_cip[:5] not in valid_4digit:
            continue
        validated_alts.append({
            "cip": alt_cip,
            "title": _NUMERIC_CODE_PARENTHETICAL.sub("", str(alt.get("title", ""))),
            "why": str(alt.get("why", "")),
            "parent_cip": str(alt.get("parent_cip", "")),
        })
    
    remaining_count = int(parsed.get("remaining_count", 0))
    narrowing_hint = str(parsed.get("narrowing_hint", "")).strip()
    
    return IntentResult(
        matched_cip=matched_cip,
        matched_title=matched_title,
        alternatives=validated_alts or None,
        remaining_count=remaining_count,
        narrowing_hint=narrowing_hint,
        # ... rest unchanged
    )
```

**Fallback resolver (`_fallback_resolve`)**

Update `_FALLBACK_JSON_SYSTEM` to include the same multi-CIP format. The fallback is JSON-only (no prose), so the prompt change is small. Parse `alternatives`, `remaining_count`, `narrowing_hint` from the response using the same validation logic.

#### `frontend/src/hooks/useSetYourCourse.ts`

**New callback: `onPickAlternative`**

```typescript
const onPickAlternative = useCallback((index: number) => {
  const res = currentResolution;
  if (!res?.alternatives?.[index]) return;
  
  const alt = res.alternatives[index];
  const updatedAlternatives = [
    // Move the current primary into the alternatives list
    { cip: res.matched_cip, title: res.matched_title, why: res.reasoning, parent_cip: res.parent_cip },
    // Keep the other alternatives, excluding the one being promoted
    ...res.alternatives.filter((_, i) => i !== index),
  ];
  
  const swapped: IntentResult = {
    ...res,
    matched_cip: alt.cip,
    matched_title: alt.title,
    parent_cip: alt.parent_cip ?? res.parent_cip,
    alternatives: updatedAlternatives,
  };
  
  setCurrentResolution(swapped);
  // Outcome refetch is triggered automatically because currentResolution changed
  // and the existing useEffect watches parentCipOrMatched
}, [currentResolution, setCurrentResolution]);
```

### Gemma Integration Details

**Call sites affected:**

1. `stream_initial_resolution` — primary streaming prompt. Prompt updated to request 3 ranked CIPs.
2. `_fallback_resolve` — JSON-only fallback. Same output format change.

**Call sites NOT affected:**

3. Chip dispatch (`_CHIP_ROUTING_SYSTEM_PROMPT`) — still operates on a single `currentResolution`. No change.
4. Career tiering — downstream of CIP selection. No change.
5. Commit — logs the final selected CIP. No change (logs `matched_cip` which is the selected primary).

**Fallback behavior:**

- If Gemma returns only `matched_cip` with no `alternatives` array: treat as single-CIP resolution (current behavior). `alternatives` stays `None`, `remaining_count` stays `0`.
- If Gemma returns malformed alternatives (bad CIP codes, missing fields): silently drop invalid entries via validation. If all alternatives are invalid, fall through to single-CIP.
- If streaming fails entirely: `_fallback_resolve` fires (existing behavior). It now also attempts multi-CIP but degrades identically.

**Logging:**

- `logs/gemma.jsonl` already captures every `gemma_client.generate` / `generate_chat` call. No change needed — the prompt change flows through the existing logging.

**Inference backend compatibility:**

- Both `ollama` and `openrouter` use the OpenAI-compatible chat completions API. The prompt change is model-agnostic.
- The `gemma4:e4b` model (smallest) may struggle with the array format — the fallback resolver already handles this gracefully.

**Rate-limit / concurrency:**

- No additional Gemma calls. The resolution still makes 1 call (streaming) + 0-1 fallback calls. The only change is the shape of the response.

### Testing Impact Analysis

> **IMPORTANT**: Test files below were found by searching for `IntentResult`, `alternatives`, and `matched_cip` references.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/services/test_set_your_course.py` | `TestStreamInitial` (class, ~10 tests) | **High** | JSON tail parsing assertions will need to handle new `alternatives` array, `remaining_count`, `narrowing_hint` in mocked Gemma responses |
| `backend/tests/services/test_set_your_course.py` | `TestChipDispatch` (class) | **Low** | Chip dispatch doesn't change, but fixtures include `IntentResult` construction |
| `backend/tests/services/test_set_your_course.py` | `TestConfirmedFocus` (class) | **Low** | Uses `IntentResult` fixtures — new fields have defaults, should pass |
| `backend/tests/services/test_set_your_course.py` | `TestResolverIntentKeywords` (class) | **Med** | Tests the resolver output shape; may assert on `alternatives=None` |
| `backend/tests/services/test_intent.py` | `test_resolve_intent_high_confidence_returns_empty_alternatives` | **High** | Directly tests that high-confidence returns empty alternatives — behavior changes |
| `backend/tests/services/test_intent.py` | `test_resolve_intent_medium_confidence_returns_2_to_4_alternatives` | **High** | Tests alternative count for medium confidence — now alternatives are semantic, not confidence-based |
| `backend/tests/services/test_intent.py` | `test_sanitize_drops_malformed_cip_codes` | **Med** | Sanitization logic may need updating if alternatives shape changes |
| `backend/tests/services/test_intent.py` | `test_sanitize_drops_primary_cip_echoed_in_alternatives` | **Med** | Dedup logic stays, but test may need fixture updates |
| `backend/tests/routers/test_set_your_course_router.py` | `TestStream` (class) | **Med** | Mocked events include `IntentResult` — new fields have defaults |
| `backend/tests/routers/test_set_your_course_router.py` | `TestChip` (class) | **Low** | Chip response shape unchanged |
| `frontend/src/hooks/useSetYourCourse.test.ts` | `TestDebounce` (describe) | **Low** | Tests debounce timing, not resolution shape |
| `frontend/src/hooks/useSetYourCourse.test.ts` | `TestChip` (describe) | **Med** | Fixture `makeResolution()` constructs `IntentResult` — needs `remaining_count`, `narrowing_hint` |
| `frontend/src/hooks/useSetYourCourse.test.ts` | `TestCommit` (describe) | **Med** | Commits `currentResolution` — if swap logic changes, assertions may break |
| `frontend/src/hooks/useSetYourCourse.test.ts` | `TestSocRevealStateMachine` (describe) | **Med** | Tests outcome fetch flow — `onPickAlternative` triggers same path |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `TestRender` | **Med** | New picker UI elements need rendering when alternatives present |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `TestStartOver` | **Low** | Start-over clears resolution — new fields clear with it |
| `frontend/src/components/school/MajorInput.test.tsx` | All | **Low** | References `alternatives` but for the low-confidence nudge flow, not multi-CIP |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `backend/tests/services/test_intent.py::test_resolve_intent_high_confidence_returns_empty_alternatives` | Update assertion: high-confidence may now return populated alternatives (semantic matches, not confidence-based) | Behavior change: alternatives are now semantic, not confidence-gated |
| `backend/tests/services/test_intent.py::test_resolve_intent_medium_confidence_returns_2_to_4_alternatives` | Update assertion: alternative count is now 0-2 (capped at 2 alts), not 2-4 | Behavior change: alternatives are now top-3 ranked, not confidence-based fallbacks |
| `backend/tests/services/test_set_your_course.py::TestStreamInitial` | Update mocked Gemma JSON tail to include `alternatives` array format | JSON format change |
| `backend/tests/services/test_set_your_course.py::TestResolverIntentKeywords` | Update `IntentResult` assertions to account for new fields | Schema expansion |
| `backend/tests/fixtures/intent_responses.json` | Add multi-CIP fixture entries | Test data expansion |
| `frontend/src/hooks/useSetYourCourse.test.ts` (all `makeResolution` calls) | Add `remaining_count: 0, narrowing_hint: ""` to fixture — fields have defaults, but explicit is better | Schema expansion |
| `frontend/src/screens/SetYourCourseScreen.test.tsx::seedState` | Add `alternatives`, `remaining_count`, `narrowing_hint` to resolution fixture | Schema expansion |

#### Confirmed Safe

These tests must NOT break. If any fail, STOP and escalate.

- `backend/tests/services/test_set_your_course.py::TestChipDispatch` — chip dispatch is unchanged
- `backend/tests/services/test_set_your_course.py::TestConfirmedFocus` — confirmed focus is unchanged
- `backend/tests/services/test_set_your_course.py::TestObservability` — logging unchanged
- `backend/tests/services/test_set_your_course.py::TestChipFlowIntentKeywords` — chip flow unchanged
- `backend/tests/services/test_intent.py::TestDeterministicShortCircuit` — deterministic path unchanged
- `backend/tests/services/test_intent.py::TestPromptCopy` — prompt copy validation
- `backend/tests/services/test_intent.py::TestYamlGate` — YAML gate unchanged
- `backend/tests/routers/test_set_your_course_router.py::TestChip` — chip router unchanged
- `backend/tests/routers/test_set_your_course_router.py::TestTierEndpointIntentFields` — tiering unchanged
- `frontend/src/hooks/useSetYourCourse.test.ts::TestConfirmedFocus` — confirmed focus unchanged
- `frontend/src/screens/SetYourCourseScreen.test.tsx::TestStartOver` — start-over clears everything (new fields included)
- `frontend/src/screens/SetYourCourseScreen.test.tsx::TestLowConfidence` — low-confidence flow unchanged
- `frontend/src/components/school/MajorInput.test.tsx` — all tests (MajorInput not modified)

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_set_your_course.py` | `test_stream_multi_cip_parses_3_ranked_options` | Mocked Gemma response with 3 CIPs → `IntentResult` has primary + 2 alternatives with correct fields |
| P0 | `backend/tests/services/test_set_your_course.py` | `test_stream_single_cip_no_alternatives` | Mocked Gemma response with 1 CIP → `alternatives` is `None`, `remaining_count` is 0 |
| P0 | `backend/tests/services/test_set_your_course.py` | `test_stream_multi_cip_validates_all_against_crosswalk` | Gemma returns 3 CIPs, one has invalid code → only 2 valid alternatives survive |
| P0 | `backend/tests/services/test_set_your_course.py` | `test_fallback_multi_cip` | `_fallback_resolve` with multi-CIP response → same validation and population |
| P1 | `backend/tests/services/test_set_your_course.py` | `test_stream_multi_cip_remaining_count_and_hint` | `remaining_count` and `narrowing_hint` extracted from Gemma response |
| P1 | `backend/tests/services/test_set_your_course.py` | `test_stream_multi_cip_deduplicates_primary` | If Gemma echoes primary CIP in alternatives, it's dropped |
| P1 | `backend/tests/services/test_intent.py` | `test_promote_to_leaf_called_for_each_alternative` | Each alternative CIP goes through `_promote_to_leaf_cip` |
| P1 | `frontend/src/hooks/useSetYourCourse.test.ts` | `test_pick_alternative_swaps_resolution_and_refetches` | `onPickAlternative(0)` → `currentResolution.matched_cip` changes, outcomes refetch fires |
| P1 | `frontend/src/hooks/useSetYourCourse.test.ts` | `test_pick_alternative_moves_primary_to_alternatives` | After swap, old primary appears in `alternatives` list |
| P1 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `test_renders_cip_picker_when_alternatives_present` | Resolution with 2 alternatives → picker elements visible in DOM |
| P1 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `test_no_picker_when_single_cip` | Resolution with no alternatives → no picker rendered |
| P1 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `test_remaining_count_hint_rendered` | Resolution with `remaining_count: 11` → hint text visible |
| P2 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `test_commit_after_swap_uses_selected_cip` | Pick alt → commit → verify committed CIP is the swapped one |

#### Test Data Requirements

- **Backend fixtures:** Add to `backend/tests/fixtures/intent_responses.json`:
  - `multi_cip_engineering` — 3 engineering CIPs with remaining_count=11
  - `multi_cip_business` — 2 business CIPs with remaining_count=0
  - `single_cip_nursing` — 1 CIP, no alternatives (control)
  - `multi_cip_invalid_alt` — 3 CIPs where alternative #2 has invalid code
- **Frontend fixtures:** Update `makeResolution()` helper in `useSetYourCourse.test.ts` to accept optional `alternatives`, `remaining_count`, `narrowing_hint` overrides

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

### @fp-data-reviewer Review
**Status:** SKIPPED (no pipeline or data changes — feature uses existing program_career_paths data)

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

### Design Audit (@design-builder)
**Status:** PENDING
[Filled in by @design-builder — Brightpath token compliance, dark-first enforcement, responsive behavior]

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

[Final thoughts, lessons learned, follow-up items.]
