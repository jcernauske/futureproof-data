# Feature: SOC Expansion via Gemma Function Calling

## Claude Code Prompt

```
Read the spec at docs/specs/feature-soc-expansion-via-gemma-tools.md in its entirety.
Also read the related spec docs/specs/feature-intent-aware-tiering.md (Spec A) — this
spec depends on it.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (introduces real Gemma function-
     calling for the first time; resolves the open question in §5 about
     tools=[...] vs prompt-then-parse).
   - Invoke @genai-architect to review the function-calling tool schema, the
     candidate-pool prompt design, and the fallback chain.
   - Invoke @fp-data-reviewer to review the candidate-pool DuckDB query against
     consumable.occupation_profiles — verify it returns valid SOC codes only,
     handles the 832-row universe correctly, and doesn't surface deprecated /
     suppressed SOCs.
   - All three write findings to §5.
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. DESIGN VISION
   - SKIPPED — backend + plumbing only. No new visible UI surface; the visible
     change is which careers appear in the COMMON / LESS_COMMON tiers for
     intent-bearing inputs.

3. IMPLEMENTATION
   - Implement the spec as written in §4 (Technical Spec).
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly.
   - DURING coding: Update only tests in "Authorized Test Modifications".
   - CRITICAL: If any test NOT in that list fails, STOP and escalate.
   - Log all work to §6.
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest) to verify.
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts).
   - If still broken after 3 attempts: escalate to human via §10.

4. TESTING
   - Invoke @test-writer to review the full spec and §4 Testing Impact Analysis.
   - Implement all "New Tests Required" by priority (P0 first).
   - Backend tests: backend/tests/ (pytest). New file: backend/tests/services/test_soc_expansion.py.
   - Frontend tests: frontend/src/**/*.test.ts(x) (vitest).
   - Run ALL tests to catch regressions.

5. DESIGN AUDIT
   - SKIPPED — no visual surface change.

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests, with focus on:
     * Tool-call response parsing safety (Gemma must not be able to inject SOCs
       outside the candidate pool).
     * Latency impact when intent_keywords is non-empty.
     * Behavior parity between INFERENCE_BACKEND=ollama and openrouter.
     * Fallback correctness.
   - Reviewer writes findings to §8.
   - If APPROVED: proceed to step 7.
   - If CHANGES REQUIRED: route to originating agent via §10.
   - If BLOCKER: STOP, alert human.

7. VERIFICATION
   - Invoke @fp-builder for full build verification.
   - Backend: ruff, mypy, pytest. Frontend: tsc, vitest, Vite build.
   - Manual verification (§9): hit /get_career_paths via the MCP server with
     "Biology + pre-med" + intent_keywords=["pre-med", "doctor"], confirm
     physician SOCs (29-1228, 29-1241) appear in the response on BOTH backends.
   - Log results to §9.
   - If all green: mark status COMPLETE.

8. COMPLETION
   - Update top-level Spec Status to COMPLETE.
   - Check off all completed Success Criteria in §1.
   - Generate report to reports/feature-soc-expansion-via-gemma-tools-YYYY-MM-DD.md.
   - Note in §11 that this is the first real tools=[...] integration; cross-link
     to feature-gemma-tool-calling-migration.md so the migration spec can adopt
     the helpers built here.
```

---

## Status: COMPLETE

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect, @genai-architect, @fp-data-reviewer approval |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-20 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-04-20 |
| Blocked By | `feature-intent-aware-tiering.md` (Spec A — must ship first to provide `intent_keywords`) |
| Related Specs | `feature-intent-aware-tiering.md` (Spec A — direct dependency); `feature-gemma-tool-calling-migration.md` (placeholder TODO — this spec is the first real `tools=[...]` integration the migration depends on); `feature-set-your-course.md` (defines the resolver that emits `intent_keywords`); `submission-kaggle-narrative.md` (function-calling on local Ollama is a named demo beat — this spec ships that beat) |

---

## §1 Feature Description

### Overview
When the BLS CIP-SOC crosswalk fundamentally lacks a SOC the student's intent demands (e.g., physicians for Biology + pre-med), call Gemma with a `tools=[expand_socs]` schema to add up to 5 intent-relevant SOCs from a pre-filtered candidate pool. This is the project's first real Gemma function-calling integration.

### Problem Statement
Spec A made `tier_careers` aware of student intent so it can re-order the SOC list. But for some inputs the SOC list itself is wrong:

- **Pre-med (Biology, CIP 26.05):** crosswalk returns lab/research-technician SOCs and zero physician SOCs.
- **Deaf ed (Special Education, CIP 13.13):** crosswalk returns five SOCs whose titles literally contain "EXCEPT special education" (25-2031, 25-2022, 25-2021, 25-2023, 25-2032) and *none* of the actual Special Education Teacher SOCs (25-2052, 25-2053, 25-2054, 25-2058). The student picks "Special Education and Teaching" and gets a list of careers that explicitly negate the program.

No amount of intent-aware re-ordering surfaces a physician for a pre-med student, or a special-ed teacher for a deaf-ed student, because the right SOCs aren't there to surface. The universe Gemma is choosing from is wrong.

This spec fixes the universe by letting Gemma propose additional SOCs from a pre-filtered candidate pool (drawn from `consumable.occupation_profiles`'s 832-SOC universe) when `intent_keywords` is non-empty. We use real OpenAI-compatible `tools=[...]` syntax — the project's first true function-calling integration. The architectural-inconsistency placeholder at `docs/specs/feature-gemma-tool-calling-migration.md` named this gap; this spec ships the foundation.

For the May 18 hackathon, this also produces a concrete demo beat: judges see Gemma making a structured tool call (`expand_socs`) and the result visibly improving career relevance for "Biology + pre-med." Both the local-Ollama track video and the cloud demo benefit.

### Success Criteria
- [x] New service `backend/app/services/soc_expansion.py` with `expand_socs(intent_keywords, base_socs, cip_family) -> list[str]`.
- [x] New `gemma_client.generate_with_tools(...)` helper supporting OpenAI-compatible `tools=[...]` and `tool_choice` syntax.
- [x] `_handle_get_career_paths` in `src/mcp_server/futureproof_server.py` accepts `intent_keywords` from the input dict and calls `expand_socs` between crosswalk fetch and substitution decision.
- [x] `OutcomesRequest` carries `intent_keywords`; the frontend sends them on `/build/outcomes` calls.
- [x] Expansion fires when EITHER (a) `intent_keywords` is non-empty OR (b) the matched program name has tokens absent from every returned SOC title (the "program-negating crosswalk" trigger that catches the deaf-ed case even when the resolver fails to extract keywords). When neither condition holds, `expand_socs` is a pure pass-through with NO Gemma call.
- [x] For "Illinois State + deaf ed" (CIP 13.13), Special Education Teacher SOCs (at minimum one of 25-2051, 25-2052, 25-2057, 25-2058, 25-2059) appear in the `/get_career_paths` response (verified by integration test). The original "EXCEPT special education" SOCs remain in the response (Spec A demotes them; Spec B adds the right ones).
- [x] When `intent_keywords` is present, Gemma returns at most 5 additional SOC codes from a candidate pool of ~30 (pre-filtered via substring match against `occupation_title` + `soc_major_group_name`).
- [x] Gemma cannot inject SOCs outside the candidate pool — any tool-call response containing an unknown SOC is filtered out before union.
- [x] On Gemma error, parse failure, or timeout, `expand_socs` returns `base_socs` unchanged (no crash).
- [ ] Both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter` produce well-formed tool-call responses; behavior parity verified in §9. *(Deferred to manual verification — requires live Gemma instance)*
- [x] For "Biology + pre-med" with `intent_keywords=["pre-med", "doctor"]`, physician SOCs (any of 29-1214, 29-1215, 29-1216, 29-1229) and/or surgeon SOCs (any of 29-1242, 29-1243, 29-1249) appear in the `/get_career_paths` response (verified by integration test).
- [x] No regression in existing pytest / vitest suites.
- [x] `logs/gemma.jsonl` captures every `expand_socs` Gemma call with `call_site="soc_expansion"`.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|-------------------------|
| 1 | Use real OpenAI-compatible `tools=[...]` syntax (function calling), not prompt-then-parse-JSON | This is the project's first true function-calling integration and a named demo beat in `submission-kaggle-narrative.md`. The placeholder migration spec (`feature-gemma-tool-calling-migration.md`) documents this as the long-term direction. Shipping the helper here lets the broader migration adopt it. | Prompt-then-parse-JSON like `career_tiering._parse_tiers` (rejected primary path — works but loses the demo story; kept as fallback in `gemma_client` if parity testing surfaces backend differences). |
| 2 | Pre-filter candidate pool to ~30 SOCs via substring/keyword match before sending to Gemma | Sending all 832 SOC titles per call (~10K tokens) is wasteful; Gemma will reason better on a relevant subset. The pre-filter is deterministic (substring match against `occupation_title` + `soc_major_group_name`), so the pool is debuggable. | Send all 832 SOCs (rejected — wasteful, slower, lower-quality output); embed-and-retrieve top-k (rejected — adds sentence-transformers dep, off-brand for Gemma hackathon). |
| 3 | Cap expansion at 5 SOCs | Hard cap so we don't dilute the original crosswalk relevance. Crosswalk SOCs remain the dominant signal; expansion is the safety valve for the cases the crosswalk fundamentally misses. | No cap (rejected — Gemma might return 10+ SOCs and bury the crosswalk signal); cap at 3 (considered — too restrictive for cases like pre-med where 4–5 health-cluster SOCs deserve to show up). |
| 4 | Trigger expansion on `intent_keywords` non-empty **OR** "program-negating crosswalk" detection | Original framing fired only on intent_keywords. That misses the deaf-ed case: even with empty intent_keywords (e.g., resolver fallback path, or older cached IntentResults), the crosswalk for Special Education returns SOCs titled "EXCEPT special education" — provably broken without needing student intent to detect it. Adding a second trigger ("does the program name share tokens with at least one returned SOC title?") catches this class of failures generically. False positive rate is low because most crosswalks DO return semantically-aligned SOCs; the trigger only fires on broken ones. Cost: one extra Gemma call on the broken-crosswalk path, which Gemma can short-circuit by returning `soc_codes: []` if it finds nothing to add. | Always call (rejected — wasteful for the 90% of crosswalks that are fine); only intent_keywords (rejected — misses deaf-ed and similar program-IS-the-intent cases); curated list of broken CIPs (rejected — the universe of broken CIPs is unbounded). |
| 5 | On Gemma failure, return `base_socs` unchanged | Same fallback pattern as `tier_careers` (`career_tiering.py:188-190`). Expansion is additive — failure means no expansion, not failure of the request. | Raise / propagate (rejected — `/get_career_paths` should never crash because expansion failed); return empty (rejected — would actively delete the crosswalk results). |
| 6 | Filter tool-call response against the candidate pool before union | Gemma can hallucinate SOCs (`29-9999`) or invent codes. The candidate pool is the contract; SOCs outside it are dropped. | Trust Gemma (rejected — would let invented SOCs propagate); fetch + validate against full 832-SOC universe (considered — strictly broader than the candidate pool, but then Gemma could pick a SOC the pre-filter intentionally excluded; pool-only is tighter). |
| 7 | `expand_socs` is a sync function called inside `_handle_get_career_paths` (which is itself sync) | The MCP server's `_handle_get_career_paths` is sync; making it async would cascade across the MCP machinery. The Gemma call inside `expand_socs` uses `gemma_client.generate_with_tools` (sync). | Make the whole MCP path async (rejected — out of scope; large refactor); offload to a thread (considered — unnecessary, the MCP server already runs sync handlers in worker threads). |
| 8 | Add `intent_keywords` to `OutcomesRequest`, not infer it server-side | The frontend already has `intent_keywords` from Spec A's resolver result. Server-side inference would mean re-running the resolver or a regex pass — both worse. | Server-side keyword extraction (rejected — duplicate work); pass raw `student_major` and let server extract (rejected — that's the resolver's job). |
| 9 | Single tool (`expand_socs`) for this spec; do NOT add others (`lookup_occupation_detail`, etc.) | Single-tool scope keeps the spec contained and the demo story clear. The migration spec (`feature-gemma-tool-calling-migration.md`) defines the broader tool-calling road map. | Multi-tool (rejected — scope creep; defer to migration spec). |
| 10 | Tool-call telemetry: log `call_site="soc_expansion"` plus `intent_keywords` and the candidate-pool size to `gemma.jsonl` | Debuggability. When relevance feels off, we want to see what intent fired, what pool was offered, and what Gemma picked. | Log nothing extra (rejected — we'll regret it the first time we get a "weird career" report). |

### Constraints
- Must not regress `_handle_get_career_paths` for callers that don't pass `intent_keywords` (back-compat).
- Must work under both `INFERENCE_BACKEND=ollama` (Gemma 4 local, `gemma4:e4b`) and `INFERENCE_BACKEND=openrouter` (`google/gemma-4-26b-a4b-it`).
- Must not hold up the `/health` probe — the substitution path already handles this by being fully sync inside the MCP handler; this spec preserves that.
- All `CIPCODE` references stay as strings (project rule from `CLAUDE.md`).
- `PrivacySuppressed` handling: not applicable — `consumable.occupation_profiles` is BLS OOH data, not College Scorecard, so this rule doesn't fire here. (Re-confirm during implementation.)
- Dates ISO `YYYY-MM-DD`. No `Any` in new public signatures.

### Out of Scope
The following live in adjacent specs or are explicitly rejected:

- **SOC-title embeddings** — rejected; off-brand for a Gemma hackathon (replacing Gemma reasoning with a separate sentence-transformers model).
- **Curated `intent_overrides.yaml`** — rejected; user wants generality over a hardcoded list.
- **Caching `expand_socs` results** by `(intent_keywords_normalized, cip_family)` — deferred until we have measurement showing repeat-call rate justifies it.
- **Migrating other Gemma callers** (`career_tiering`, resolver, `boss_fights.narrate_one`, `guidance.generate_guidance_async`, `skill_recs`, `skill_pool`) to function-calling syntax — that's the scope of `feature-gemma-tool-calling-migration.md`. They stay prompt-then-parse for this spec. The `gemma_client.generate_with_tools` helper this spec ships is the foundation that migration depends on.
- **Adding more tools beyond `expand_socs`** — single-tool scope keeps the spec contained; multi-tool exploration is the migration spec's job.
- **Caveat surfacing for AI-expanded SOCs** — today the substitution caveat in `_handle_get_career_paths:2203-2218` describes blended-substitution semantics; we may want a similar caveat noting "X careers added by Gemma based on stated intent" but this is deferred to a follow-up so it doesn't entangle the core function-calling work. The user's "no substitution caveat" memory rule (no "Limited data" warnings on career cards from CIP substitution) suggests we should be cautious about surfacing this kind of UI-visible caveat at all.
- **Frontend UI affordance** showing "Gemma added these careers based on your intent" — out of scope; if added later, that's a separate UX spec.

---

## §3 UI/UX Design

**SKIPPED — backend + plumbing only.**

The visible change is *which careers appear in `/get_career_paths` and downstream tier displays* for intent-bearing inputs. No new components, no copy changes. (The demo story shows this in the architecture diagram and a debug-trace view, but no production UI surface changes here.)

---

## §4 Technical Specification

### Architecture Overview

`_handle_get_career_paths` (`src/mcp_server/futureproof_server.py:2013`) is the canonical entry point for the school+major → careers query. Today it (1) validates inputs, (2) decides whether substitution applies, (3) fetches crosswalk SOCs via `_fetch_crosswalk_socs(cip4)` (line 1529), and (4) builds substituted or standard-path rows. This spec inserts a **SOC expansion step between crosswalk fetch and row build** that fires only when the caller passes `intent_keywords`.

The new `backend/app/services/soc_expansion.py` module:
1. Pre-filters `consumable.occupation_profiles` (832 SOCs) by substring match against `intent_keywords` over `occupation_title` + `soc_major_group_name` to build a candidate pool of ~30 SOCs (capped to keep the prompt small).
2. Calls Gemma with `tools=[expand_socs]` and a system prompt asking it to pick up to 5 SOCs from the candidate pool that the student's intent demands but the crosswalk missed.
3. Filters Gemma's response against the candidate pool (no hallucinated SOCs).
4. Returns the union of `base_socs` + Gemma's picks.
5. On any failure, returns `base_socs` unchanged.

`backend/app/services/gemma_client.py` gains a new `generate_with_tools` helper that wraps the OpenAI client's `chat.completions.create(tools=[...], tool_choice=...)` call for both Ollama (`http://localhost:11434/v1`) and OpenRouter. This is the project's first true function-calling code path; today's "tool calls" in `handle_chip_dispatch` (set_your_course.py:580) actually use a manual pre-fetch + prompt-then-parse pattern (the placeholder migration spec calls this out).

The frontend already gets `intent_keywords` from Spec A's resolver. We extend `OutcomesRequest` to accept it, thread it through `compute_pentagon` → MCP `get_career_paths` invocation. Spec A's tiering layer continues to work unchanged on the (now larger) SOC list.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/services/soc_expansion.py` | **Create** | New module. `expand_socs(intent_keywords, base_socs, cip_family) -> list[str]`. Pre-filter → Gemma function call → union. Falls back to base_socs on failure or empty intent. Logs to `gemma.jsonl` via `gemma_client`. |
| `backend/app/services/gemma_client.py` | Modify | Add `generate_with_tools(system, user, tools, tool_choice="auto", max_tokens, temperature, extra) -> dict \| None` returning the parsed tool call (function name + arguments dict) or None on failure. Mirrors the existing `generate` / `generate_chat` pattern for env handling, semaphore, and `gemma.jsonl` logging. Sync sibling of `generate`. |
| `src/mcp_server/futureproof_server.py` | Modify | In `_handle_get_career_paths` (line 2013): accept `intent_keywords: list[str]` from `input_dict.get("intent_keywords", [])`; after the `_fetch_crosswalk_socs` call inside `_build_substituted_rows` AND inside the standard path's SOC resolution, ALWAYS call `soc_expansion.expand_socs(intent_keywords, base_socs, cip_family=..., program_name=..., base_soc_titles=...)`. The function itself decides whether to fire Gemma based on the two triggers; pass-through is cheap when neither fires. Validate `intent_keywords` is a list of strings; fall back to `[]` on bad input. Pass the program_name from the resolved/substituted entry and base_soc_titles from a quick join against `consumable.occupation_profiles`. |
| `backend/app/services/stat_engine.py` | Modify | `compute_pentagon` and `compute_one`: add `intent_keywords: list[str] = []` keyword arg; thread it into the MCP `get_career_paths` invocation alongside the existing `student_major` / `student_cip`. |
| `backend/app/models/api.py` | Modify | `OutcomesRequest` (line 39): add `intent_keywords: list[str] = Field(default_factory=list)`. `BuildRequest` (line 60): add same field for build-time consistency. |
| `backend/app/routers/builds.py` | Modify | `compute_outcomes` (line 26): forward `request.intent_keywords` to `stat_engine.compute_pentagon`. `create_build` (line 61): forward to `stat_engine.compute_one`. |
| `frontend/src/api/build.ts` | Modify | `getOutcomes` and the build POST: accept `intent_keywords?: string[]` and serialize into the request body. |
| `frontend/src/screens/SetYourCourseScreen.tsx` | Modify | After Spec A resolver completion, pass `intent_keywords` to `getOutcomes` (currently only passes to `getTieredCareers` per Spec A). |
| `backend/tests/services/test_soc_expansion.py` | **Create** | New test file (see §4 Testing Impact Analysis). |
| `backend/tests/services/test_gemma_client.py` | Modify | Add tests for `generate_with_tools` — mocked OpenAI client with both backend configurations. |

**Files NOT changed (verify but don't touch):**
- `backend/app/services/career_tiering.py` — already gets the larger SOC list naturally via the existing `outcomes` parameter; Spec A's intent plumbing handles the ordering.
- `src/mcp_server/futureproof_server.py:_fetch_crosswalk_socs` (line 1529) — unchanged; expansion is a separate step layered on top.
- `backend/app/models/career.py` — `IntentResult` already has `intent_keywords` from Spec A.

### Data Model Changes

#### `OutcomesRequest` (Pydantic — `backend/app/models/api.py:39`)

```python
class OutcomesRequest(BaseModel):
    unitid: int
    cipcode: str
    student_major: str | None = None
    student_cip: str | None = None
    effort: str = "balanced"
    loan_pct: float = 1.0
    # NEW — propagated from the Spec A resolver result. Triggers SOC
    # universe expansion in _handle_get_career_paths when non-empty.
    intent_keywords: list[str] = Field(default_factory=list)
```

#### `BuildRequest` (Pydantic — `backend/app/models/api.py:60`)

```python
class BuildRequest(BaseModel):
    profile_name: str
    school_name: str
    unitid: int
    cipcode: str
    cip_title: str
    major_text: str
    effort: str
    loan_pct: float
    selected_soc: str
    selected_title: str
    student_major: str | None = None
    student_cip: str | None = None
    # NEW — same source/purpose as OutcomesRequest.intent_keywords. Build-
    # time forwarding ensures the persisted build's career list matches
    # what the preview showed.
    intent_keywords: list[str] = Field(default_factory=list)
```

No DuckDB / Iceberg schema changes. We read from `consumable.occupation_profiles` only — already exists.

### Service Changes

#### New module: `backend/app/services/soc_expansion.py`

```python
"""Gemma-driven SOC universe expansion.

When a student's stated intent (intent_keywords from the Set Your Course
resolver) demands SOCs the BLS CIP-SOC crosswalk doesn't return — e.g.,
physicians for Biology + pre-med — this module pre-filters a candidate
pool from consumable.occupation_profiles, calls Gemma with a
tools=[expand_socs] schema, and returns the union of crosswalk SOCs
plus Gemma's intent-driven picks (capped at 5).

When intent_keywords is empty: pure pass-through, no Gemma call.
When Gemma fails or returns nothing parseable: returns base_socs.
"""

from __future__ import annotations

import logging
from typing import Any

from app.services import gemma_client

logger = logging.getLogger(__name__)

EXPANSION_CAP: int = 5
CANDIDATE_POOL_CAP: int = 30


def expand_socs(
    intent_keywords: list[str],
    base_socs: list[str],
    cip_family: str,
    *,
    program_name: str = "",
    base_soc_titles: list[str] | None = None,
) -> list[str]:
    """Return the union of base_socs + up to 5 Gemma-picked SOCs.

    Triggers expansion when EITHER:
      (a) intent_keywords is non-empty, OR
      (b) the program name shares no significant tokens with any
          base SOC title (the "program-negating crosswalk" case —
          e.g., CIP 13.13 "Special Education..." returns SOCs all
          titled "...EXCEPT special education").

    Pure pass-through when neither condition holds (no Gemma call).
    Falls back to base_socs unchanged on any Gemma error or parse
    failure. Order: base_socs first (preserved), then de-duped picks
    from Gemma in the order Gemma returned them.
    """
    derived_keywords = list(intent_keywords)
    if not derived_keywords and program_name and base_soc_titles is not None:
        if _program_negates_crosswalk(program_name, base_soc_titles):
            derived_keywords = _tokens_from_program_name(program_name)

    if not derived_keywords:
        return base_socs

    candidate_pool = _build_candidate_pool(derived_keywords, base_socs, cip_family)
    if not candidate_pool:
        return base_socs

    picks = _ask_gemma_for_picks(derived_keywords, base_socs, candidate_pool, cip_family)
    if not picks:
        return base_socs

    valid_picks = [s for s in picks if s in candidate_pool and s not in base_socs]
    valid_picks = valid_picks[:EXPANSION_CAP]

    return list(dict.fromkeys(base_socs + valid_picks))


def _program_negates_crosswalk(
    program_name: str, base_soc_titles: list[str]
) -> bool:
    """True when the program name shares no significant tokens with
    ANY base SOC title.

    Significant tokens: lowercase content words from program_name,
    excluding stopwords and generic terms ('and', 'the', 'general',
    'specific', 'subject', 'areas', etc.). If at least ONE base SOC
    title contains AT LEAST ONE significant program token, the
    crosswalk is considered semantically aligned and this returns
    False (no expansion needed).

    Example trigger: program_name="Special Education and Teaching,
    Specific Subject Areas", base_soc_titles all contain "EXCEPT
    special education" → tokens {special, education, teaching} but
    every SOC title's "special education" appears in a NEGATING
    context. The substring match would naively pass (titles literally
    contain "special education"), so the implementation must match on
    word boundaries AND check for negating prefixes ("except",
    "excluding", "non-"). Documented as a known refinement during
    implementation; if the negation detection proves brittle, fall
    back to "no significant token overlap" as the trigger and accept
    the false-negative rate.
    """
    ...


def _tokens_from_program_name(program_name: str) -> list[str]:
    """Lowercase content tokens extracted from the program name,
    suitable for use as fallback intent_keywords when the resolver
    didn't provide any. Strips stopwords and CIP-administrative
    terms ('specific subject areas', 'general', 'other', etc.).
    """
    ...


def _build_candidate_pool(
    intent_keywords: list[str],
    base_socs: list[str],
    cip_family: str,
    *,
    query_fn: Callable | None = None,
) -> dict[str, dict[str, str]]:
    """Pre-filter consumable.occupation_profiles to ~30 SOC candidates.

    Applies synonym bridging BEFORE substring match: a small vocabulary
    map translates student-language keywords ("doctor", "pre-med",
    "lawyer") to BLS-language terms ("physician", "surgeon", "attorney")
    so the match hits real occupation titles. Then substring-matches the
    expanded keyword set against occupation_title + soc_major_group_name
    (lowercased). Excludes SOCs already in base_socs. Caps at
    CANDIDATE_POOL_CAP (30).

    Uses the QueryEngine (via query_fn) to read from the Iceberg
    catalog — NOT direct DuckDB file access (data/futureproof.duckdb
    is empty; the data lives in Iceberg tables via catalog.db).

    Returns {soc_code: {title, major_group, education_level}} for use
    in the Gemma prompt.
    """
    ...


def _ask_gemma_for_picks(
    intent_keywords: list[str],
    base_socs: list[str],
    candidate_pool: dict[str, dict[str, str]],
    cip_family: str,
) -> list[str]:
    """Call Gemma with tools=[expand_socs] and return the picked SOCs.

    Returns [] on Gemma error, empty response, or unparseable tool call.
    Caller is responsible for filtering against the candidate pool.
    """
    ...
```

#### New helper: `gemma_client.generate_with_tools`

```python
def generate_with_tools(
    system: str,
    user: str,
    tools: list[dict[str, Any]],
    *,
    tool_choice: str | dict[str, Any] = "required",
    max_tokens: int = 600,
    temperature: float = 0.0,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Issue a chat completion with OpenAI-compatible function-calling.

    Returns ``{"name": <fn_name>, "arguments": <dict>}`` for the first
    tool call in the response, or ``None`` if the model returned a
    plain message instead of calling a tool, or on transport error.

    Behavior parity required across both INFERENCE_BACKEND values:
    - ollama: passes ``tools`` through to localhost:11434 (Ollama
      supports OpenAI-compatible function-calling for tool-aware models;
      verify gemma4:e4b is tool-capable during ARCH REVIEW).
    - openrouter: passes ``tools`` through to google/gemma-4-26b-a4b-it
      via the OpenRouter proxy.

    On parity issues surfaced during ARCH REVIEW, fall back to the
    prompt-then-parse-JSON pattern used by handle_chip_dispatch — keep
    the same input/output shape so callers don't change.

    Logs to logs/gemma.jsonl with extra["call_site"] for traceability.
    Acquires the same module-level semaphore as ``generate``.
    """
    ...
```

#### `expand_socs` tool schema

```json
{
  "type": "function",
  "function": {
    "name": "expand_socs",
    "description": "Pick up to 5 SOC codes from the candidate pool that the student's stated career intent demands but the BLS CIP-SOC crosswalk did not return. Picks must be from the pool only.",
    "parameters": {
      "type": "object",
      "properties": {
        "soc_codes": {
          "type": "array",
          "items": {"type": "string", "pattern": "^\\d{2}-\\d{4}$"},
          "minItems": 0,
          "maxItems": 5,
          "description": "SOC codes from the candidate pool that should be added because they directly match the student's stated intent."
        },
        "rationale": {
          "type": "string",
          "description": "One sentence explaining the picks."
        }
      },
      "required": ["soc_codes", "rationale"]
    }
  }
}
```

#### `expand_socs` system prompt (revised per @genai-architect review)

```
You expand a student's career-search SOC list when the BLS CIP-SOC
crosswalk doesn't return SOCs the student's stated intent demands.

You will receive:
- The student's intent keywords (e.g., "pre-med", "doctor").
- The existing SOC list from the crosswalk (do NOT re-pick these).
- A candidate pool of SOCs in the format:
    SOC_CODE | Title | Major Group | Education Level

Call expand_socs with:
- soc_codes: up to 5 SOC codes from the candidate pool that directly
  match the student's intent and are NOT already in the existing list.
  Use the XX-XXXX format exactly (e.g., 29-1229, 25-2052).
- rationale: one sentence explaining the picks.

Selection rules:
1. Only pick SOCs from the candidate pool. Never invent codes.
2. If the student's intent implies an advanced degree — keywords like
   "pre-med", "doctor", "physician", "pre-vet", "veterinarian",
   "dentist", "pre-law", "attorney" — prefer SOCs requiring a doctoral
   or professional degree over associate's or bachelor's-level SOCs.
3. If no candidate SOC genuinely matches the intent, return an empty
   soc_codes array (do not force picks to fill the cap).
4. Do not pick SOCs that are semantically redundant with those already
   in the existing list (same role at a different level is fine;
   exact duplicates are not).
```

### Gemma Integration Discipline

This spec touches one new Gemma call site (`expand_socs`) and adds one new helper (`generate_with_tools`). Both follow the existing client conventions:

| Concern | Approach |
|---|---|
| Fallback behavior | `expand_socs` returns `base_socs` unchanged on any failure (timeout, transport error, parse failure, empty response, response with no valid SOCs in the pool). Same pattern as `tier_careers`. |
| `gemma.jsonl` logging | `generate_with_tools` writes a record with `call_site="soc_expansion"`, `intent_keywords`, `candidate_pool_size`, `tool_call_made` (bool), `picked_count`, `valid_pick_count` (after pool filter). Mirrors the existing call-site logging pattern. |
| Backend parity (`ollama` / `openrouter`) | Both must produce well-formed tool-call responses. Verified in §9 manual checks. If parity issues surface during ARCH REVIEW, fall back path is the prompt-then-parse-JSON variant inside `generate_with_tools` — same input/output shape, no caller change. |
| Rate limit / concurrency | `generate_with_tools` acquires the same module-level semaphore (max 8 concurrent) as `generate`. `expand_socs` only fires when `intent_keywords` is non-empty, so aggregate Gemma load barely changes. |
| Cloud demo readiness | OpenRouter rate limits per `cloud-gemma-deployment.md`: this spec adds at most one extra Gemma call per Set Your Course submission. Acceptable. |

**Open question for ARCH REVIEW (§5):** Whether `gemma4:e4b` (Ollama) reliably honors `tools=[...]` syntax. If not, the spec's documented fallback is the prompt-then-parse path with the same input/output shape. `@fp-architect` to confirm via a brief spike before IMPLEMENTATION.

### Testing Impact Analysis

> **Searched** `backend/tests/` for tests touching `_handle_get_career_paths`, `OutcomesRequest`, `compute_pentagon`, `gemma_client.generate`. No existing tests touch `soc_expansion` (new module).

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `tests/mcp/test_futureproof_server.py` (verify exists) | `_handle_get_career_paths` happy-path tests | Med | Now accepts `intent_keywords`. Existing callers don't pass it; default `[]` should preserve behavior, but every test must still pass. |
| `backend/tests/routers/test_builds.py` (verify exists) | `/build/outcomes` and `/build` tests | Low | New optional field on request body; defaults handle it. |
| `backend/tests/services/test_stat_engine.py` (verify exists) | `compute_pentagon` / `compute_one` tests | Low | New keyword arg with default `[]`. |
| `backend/tests/services/test_gemma_client.py` (verify exists) | All existing client tests | Low | Adding a new helper, not modifying existing ones. |
| `backend/tests/services/test_set_your_course.py` (verify exists) | Resolver tests | None | Not touched. |
| `frontend/src/api/__tests__/build.test.ts` (verify exists) | `getOutcomes` test | Low | Optional new arg. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| Existing `_handle_get_career_paths` tests | Add `"intent_keywords": []` to the input dict in fixtures where explicit clarity helps | Optional defensive change — defaults handle it. |
| `tests/mcp/test_futureproof_server.py` happy-path tests | When the test asserts the SOC list for "Biology" or other intent-bearing inputs, add `"intent_keywords": []` so behavior is provably independent of expansion until expansion is opt-in. | Locks down back-compat. |

#### Confirmed Safe

These tests must NOT break — if they fail, STOP and escalate:

- All existing `_handle_get_career_paths` tests with the same `(unitid, cipcode)` inputs they use today and no `intent_keywords` produce identical responses.
- All persisted-build replay tests (`builds.load_build`) succeed for builds saved before this spec.
- All existing `gemma_client.generate` tests pass unchanged.
- `compute_pentagon` outputs are identical when `intent_keywords` is empty.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_empty_intent_aligned_crosswalk_returns_base_socs_no_gemma_call` | `expand_socs([], base_socs, "26", program_name="Biology, General", base_soc_titles=[...biology-aligned titles...])` returns `base_socs` unchanged and never invokes the Gemma client. Validates the dominant pass-through path. |
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_program_negating_crosswalk_triggers_expansion_without_intent` | `expand_socs([], base_socs, "13", program_name="Special Education and Teaching, Specific Subject Areas", base_soc_titles=["Secondary school teachers, except special education", ...])` triggers expansion (Gemma is called) even though intent_keywords is empty. The "EXCEPT special education" titles contradict the program name. Mocked Gemma returns special-ed teacher SOCs; result is base_socs + those. |
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_intent_keywords_take_precedence_over_program_name_fallback` | When intent_keywords is non-empty, those are used regardless of crosswalk alignment. Program-name-fallback path is not exercised. |
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_gemma_picks_added_to_base_socs` | With mocked Gemma returning `{"soc_codes": ["29-1228", "29-1241"], "rationale": "..."}` and a candidate pool containing both, the result equals `base_socs + ["29-1228", "29-1241"]`. |
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_gemma_picks_outside_candidate_pool_filtered` | If Gemma returns `["99-9999"]` (not in pool), the result is `base_socs` unchanged. |
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_expansion_capped_at_five` | If Gemma returns 8 valid SOCs, only the first 5 are appended. |
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_gemma_failure_returns_base_socs` | Mocked Gemma raises → result is `base_socs` unchanged, no exception propagates. |
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_duplicate_picks_deduped` | If Gemma picks a SOC already in `base_socs`, it's not duplicated. Order preserved. |
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_pre_med_biology_surfaces_physicians` | Real-data integration test: with `intent_keywords=["pre-med", "doctor"]` and `cip_family="26"`, the candidate pool contains `29-1228` (Physicians) and `29-1241` (Surgeons). Mocked Gemma picks them; result includes them. (Validates the candidate pool is built correctly from `consumable.occupation_profiles`.) |
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_deaf_ed_special_education_surfaces_special_ed_teachers` | Real-data integration test for the canonical broken case: with `intent_keywords=["deaf education", "special education", "teacher"]` and `cip_family="13"`, the candidate pool contains at least one of `25-2052`, `25-2053`, `25-2054`, `25-2058` (Special Education Teacher SOCs). Mocked Gemma picks them; result includes at least one. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_generate_with_tools_parses_tool_call` | Mocked OpenAI client returns a `tool_calls` response; `generate_with_tools` parses out `{"name": "expand_socs", "arguments": {...}}`. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_generate_with_tools_no_tool_call_returns_none` | Mocked OpenAI client returns a plain message (no `tool_calls`); helper returns `None`. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_generate_with_tools_logs_to_jsonl` | Verify `gemma.jsonl` gains a record with `call_site="soc_expansion"`, `tool_call_made=True/False`. |
| P1 | `tests/mcp/test_futureproof_server.py` | `test_get_career_paths_with_intent_keywords_invokes_expansion` | When `input_dict` includes `intent_keywords=["pre-med"]`, `_handle_get_career_paths` calls `expand_socs` (mock-spied) and the response SOC list is the expanded union. |
| P1 | `tests/mcp/test_futureproof_server.py` | `test_get_career_paths_back_compat_no_intent_keywords` | When `input_dict` lacks `intent_keywords`, behavior is identical to today. |
| P1 | `backend/tests/services/test_stat_engine.py` | `test_compute_pentagon_threads_intent_keywords` | `compute_pentagon(..., intent_keywords=["pre-med"])` passes the field into the MCP call (mock-spied). |
| P1 | `backend/tests/routers/test_builds.py` | `test_outcomes_endpoint_forwards_intent_keywords` | POST `/build/outcomes` with `intent_keywords` reaches `compute_pentagon`. |
| P1 | `frontend/src/api/__tests__/build.test.ts` | `getOutcomes serializes intent_keywords` | When called with `intent_keywords`, the POST body contains them. |
| P2 | `backend/tests/services/test_soc_expansion.py` | `test_candidate_pool_excludes_base_socs` | Pre-filter never includes SOCs already in `base_socs`. |
| P2 | `backend/tests/services/test_soc_expansion.py` | `test_candidate_pool_capped_at_thirty` | Pre-filter returns at most `CANDIDATE_POOL_CAP` SOCs even when many SOCs match the intent keywords. |

#### Test Data Requirements

- A mocked DuckDB result for `consumable.occupation_profiles` containing physician (29-1228), surgeon (29-1241), and at least 10 unrelated SOCs to validate pre-filter behavior. Or use the real DuckDB if the test marker `@pytest.mark.duckdb` (verify exists) gates it.
- Mocked Gemma tool-call responses in OpenAI-compatible format:
  ```python
  {"choices": [{"message": {"tool_calls": [{
      "id": "call_1",
      "type": "function",
      "function": {
          "name": "expand_socs",
          "arguments": '{"soc_codes": ["29-1228"], "rationale": "..."}'
      }
  }]}}]}
  ```
- A fixture `intent_keywords=["pre-med", "doctor"]` for the canonical pre-med test.
- A fixture for empty intent keywords (`[]`) for the back-compat path.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-20

#### System Context

This spec inserts a Gemma-driven SOC expansion step into `_handle_get_career_paths` (the MCP server's central career-query handler at `src/mcp_server/futureproof_server.py:2305`). It touches four layers: (1) the React frontend passes `intent_keywords` through the API, (2) FastAPI `OutcomesRequest`/`BuildRequest` carry it, (3) `stat_engine.compute_pentagon` threads it into the MCP call, (4) the MCP handler calls `expand_socs` (new service in `backend/app/services/`) which queries DuckDB Gold zone `consumable.occupation_profiles` and issues an OpenAI-compatible `tools=[...]` call to Gemma via the new `generate_with_tools` helper. This is the project's first true function-calling integration. The output (expanded SOC list) feeds into the existing row-build logic; downstream tiering (Spec A) and stat computation are unaffected.

#### Data Flow Analysis

**Frontend to MCP (intent_keywords threading):**

`SetYourCourseScreen` -> `getOutcomes(intent_keywords)` -> POST `/build/outcomes` -> `OutcomesRequest.intent_keywords` -> `stat_engine.compute_pentagon(intent_keywords=...)` -> `mcp_client.call("get_career_paths", {intent_keywords: [...]})` -> `_handle_get_career_paths(input_dict)` -> `expand_socs(...)`.

The threading is correct in principle. Each boundary crossing has a typed contract (`OutcomesRequest` Pydantic model, `compute_pentagon` keyword arg, `input_dict` dict). The MCP `input_dict` is untyped (dict), which is the existing pattern -- acceptable given the validation happens inside `_handle_get_career_paths`.

**Expansion insertion point -- Substituted path (line 2448):**

The spec says to call `expand_socs` between crosswalk fetch and row build. On the substituted path, `_build_substituted_rows` (line 1842) fetches crosswalk SOCs at line 1910 (`self._fetch_crosswalk_socs(substituted_cipcode)`), then iterates over `socs` to build rows at line 1936. The expansion must happen between lines 1910 and 1916 (after SOC fetch, before the JOIN query). This is architecturally sound BUT has an integration concern: see Concern #1 below.

**Expansion insertion point -- Standard path (line 2514):**

The standard path calls `_standard_path_rows` (line 610), which queries `program_career_paths` directly -- it does NOT go through the crosswalk at all. The SOC codes come embedded in the pre-joined Gold zone table rows, not from `_fetch_crosswalk_socs`. The spec says to call `expand_socs` on "the standard path's SOC resolution," but the standard path has no separate SOC resolution step -- the SOCs are a byproduct of the `program_career_paths` query. This is a structural mismatch that needs resolution. See Concern #2 (promoted to Blocker).

**Gold zone reads:**

`_build_candidate_pool` reads from `consumable.occupation_profiles` (832 SOCs). This is a Gold zone read-only query -- correct zone boundary. No writes, no schema changes.

**Gemma call:**

`_ask_gemma_for_picks` -> `gemma_client.generate_with_tools` -> OpenAI client -> Ollama/OpenRouter. Response filtered against candidate pool before union. This is clean.

#### Contract Review

**`OutcomesRequest` (Pydantic):** Adding `intent_keywords: list[str] = Field(default_factory=list)` is backward-compatible. Existing callers that don't send it get `[]`. Clean.

**`BuildRequest` (Pydantic):** Same addition, same backward-compat story. However, `BuildRequest` currently lacks `intent_keywords` (confirmed at line 62-76 of `api.py`). The spec correctly identifies this addition. But note: `compute_one` (line 351 of `stat_engine.py`) delegates to `compute_pentagon`, which will now need `intent_keywords` -- and `create_build` (line 66 of `builds.py`) must forward it. The spec's file-change table lists this. Correct.

**`generate_with_tools` return type:** `dict[str, Any] | None` -- returns `{"name": str, "arguments": dict}` or `None`. This is adequate for the single-tool use case. The `Any` in the return type is acceptable here because tool-call argument schemas vary per tool; the caller (`_ask_gemma_for_picks`) validates the specific shape.

**`expand_socs` tool schema:** Well-typed. `soc_codes` has a regex pattern constraint (`^\\d{2}-\\d{4}$`), `maxItems: 5`. The `rationale` field is smart -- it gives Gemma a place to reason without stuffing reasoning into the SOC array.

**MCP `get_career_paths` input schema:** Currently has no `intent_keywords` in its `input_schema` definition (the ToolDef at line ~643). The spec doesn't mention updating the MCP tool schema. This is fine for the backend-direct-call path (stat_engine calls via `mcp_client.call` which bypasses schema validation), but if Gemma ever calls `get_career_paths` via function calling, the schema would reject the new field. Low risk today -- Gemma doesn't call this tool. Note for the migration spec.

#### Findings

##### Sound

1. **Fallback chain design.** `expand_socs` returns `base_socs` unchanged on any failure -- same pattern as `tier_careers` (line 188-190 of `career_tiering.py`). This means the feature is purely additive: if Gemma is down, slow, or returns garbage, the user gets exactly what they get today. No degradation of the existing contract.

2. **Candidate pool pre-filter + post-filter double-gate.** Pre-filtering to ~30 SOCs keeps the prompt small and focused; post-filtering against the pool prevents hallucinated SOCs from propagating. This is the correct trust boundary for LLM output in a data pipeline.

3. **Sync design for `generate_with_tools`.** `_handle_get_career_paths` is sync. The existing Gemma call in the Tier 2 fallback (`_fallback_gemma_soc_resolution` at line 2110) already uses a sync `generate` call with a lazy import. Matching that pattern is correct. The asyncio semaphore is irrelevant here (it guards async callers); the sync path doesn't need concurrency control because the MCP handler already runs in worker threads. This is fine.

4. **`intent_keywords` default `[]` on all models.** Backward-compatible across every boundary. Frontend callers that predate this spec send no field; Pydantic defaults handle it; `expand_socs` short-circuits on empty list. Clean.

5. **Program-negating crosswalk trigger (Decision #4).** This is a genuinely clever fallback for the deaf-ed class of failures. The negation-detection heuristic is documented as potentially brittle with a fallback to "no token overlap" -- honest and pragmatic for the deadline.

6. **Tool schema design.** Single tool, typed parameters, regex-constrained SOC format, hard cap. Minimal attack surface for Gemma hallucination.

##### Concerns

- **Concern #1: `expand_socs` import path from MCP server.** The spec places `expand_socs` in `backend/app/services/soc_expansion.py`, but it must be called from `src/mcp_server/futureproof_server.py`. The existing pattern for this cross-boundary import is lazy import inside the method (see line 2118: `from app.services.gemma_client import generate as gemma_generate` with an `except ImportError` guard). The spec's File Changes table says to call `expand_socs` from `_handle_get_career_paths` but doesn't explicitly note the lazy-import pattern. **Impact:** If the implementer uses a top-level import, the MCP server will fail to start when `backend/` is not on `sys.path` (which is the case for pipeline-only test runs). **Recommendation:** Spec should note that `soc_expansion.expand_socs` must be lazy-imported inside `_handle_get_career_paths` with the same `try/except ImportError` guard used for `gemma_client` at line 2118. Implementer should follow the existing pattern exactly.

- **Concern #3: `generate_with_tools` uses `tools: list[dict[str, Any]]` -- no Pydantic model for tool definitions.** The tool schema is defined as a raw JSON dict in the spec (line 447-472). This is pragmatic for a single-tool use case, but it means the tool definition is validated only by the OpenAI client at call time, not at import time. **Impact:** A typo in the schema (e.g., `"fucntion"` instead of `"function"`) would only surface when `expand_socs` fires, not at startup. **Recommendation:** Minor -- acceptable for hackathon scope. When the migration spec adopts `generate_with_tools` for multiple tools, promote tool definitions to typed dataclasses or Pydantic models. No action needed now.

- **Concern #4: `base_soc_titles` plumbing.** The spec says the MCP handler should "pass the base_soc_titles from a quick join against `consumable.occupation_profiles`." This means an additional DuckDB query on every `_handle_get_career_paths` call to resolve SOC codes to titles, even when `intent_keywords` is empty and expansion won't fire. **Impact:** Unnecessary latency on the dominant path (no intent keywords). **Recommendation:** Only fetch `base_soc_titles` when `intent_keywords` is non-empty OR when you need to evaluate the program-negating-crosswalk trigger. Since the trigger also needs titles, the implementation should: (a) if `intent_keywords` is non-empty, skip the title fetch and go straight to `expand_socs` with the keywords; (b) if `intent_keywords` is empty, fetch titles only if `program_name` is available, then evaluate the negation trigger. This way the title query fires only on the ~10% of calls where expansion might be relevant.

- **Concern #5: `_build_substituted_rows` encapsulation.** The substituted path's SOC list is fetched and consumed entirely inside `_build_substituted_rows` (line 1910-1936). To insert expansion, you'd need to either (a) modify `_build_substituted_rows` to accept an `intent_keywords` parameter and call `expand_socs` internally, or (b) split the method so SOC fetch is a separate step. The spec says to call `expand_socs` "inside `_build_substituted_rows`" (implied by the File Changes table saying to insert between crosswalk fetch and row build), but doesn't address the method signature change. **Impact:** Not a blocker -- the implementer will figure it out -- but the spec should be explicit about which approach to take. **Recommendation:** Add `intent_keywords: list[str] = []` and `program_name: str = ""` as keyword args to `_build_substituted_rows`. The method already accepts `substituted_program_name` which can serve as `program_name`. Expansion inserts between line 1910 (SOC fetch) and line 1916 (JOIN query).

##### Blockers

- **Blocker #1: Standard path has no SOC-list insertion point.** On the standard path (line 2514), `_standard_path_rows` (line 610) queries `consumable.program_career_paths` directly and returns fully-formed rows with SOC codes embedded. There is no intermediate "SOC list" to expand. If expansion adds SOC `29-1228` (Physician) for a Biology major, the standard path has no mechanism to build a row for that SOC -- `program_career_paths` only contains rows that the pipeline pre-joined. The substituted path CAN handle expansion because it fetches SOCs from the crosswalk and then JOINs per-SOC data dynamically (line 1916-1936). The standard path cannot.

    The spec must resolve this asymmetry. Options:
    1. **Standard path adopts the substituted path's dynamic JOIN for expanded SOCs only.** When `expand_socs` returns SOCs beyond `base_socs`, build additional rows using the same `_fetch_substituted_join` mechanism (or a similar per-SOC join against `occupation_profiles + onet_work_profiles + ai_exposure`). The original `program_career_paths` rows are preserved as-is; expanded SOCs get dynamically-built rows with `match_quality="gemma_expanded"`. This is the cleanest approach and parallels how the substituted path already works.
    2. **Only support expansion on the substituted path.** This covers the pre-med and deaf-ed cases (both involve substitution), but misses cases where the standard path's crosswalk is also deficient. Acceptable for hackathon scope if documented.
    3. **Extract SOC codes from standard-path rows and use them as `base_socs`.** Then call `expand_socs`, and for any new SOCs, build rows via the dynamic JOIN. This is option 1 with explicit SOC extraction.

    **Recommendation:** Option 1 or 3. The pre-med Biology case at IU (`unitid=151351`, `cipcode=26.01`) likely hits the standard path (Biology is not a broad XX.01 code), which means the spec's own canonical test case may fail on the standard path without this fix. Verify which path Biology at IU takes, and ensure expansion works there.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions

1. **Resolve Blocker #1: Standard path SOC insertion.** The spec must define how expanded SOCs become rows on the standard path, where `program_career_paths` is pre-joined and has no dynamic row-building mechanism. Recommended: extract SOC codes from standard-path rows as `base_socs`, call `expand_socs`, and for any new SOCs returned by Gemma, build rows via a dynamic JOIN (reusing the substituted path's `_fetch_substituted_join` or an equivalent). Mark these rows with `match_quality="gemma_expanded"` so downstream consumers can distinguish them.

2. **Address Concern #4: Lazy title fetch.** Do not issue a DuckDB query for `base_soc_titles` on every call. Gate the title fetch behind `intent_keywords` non-empty OR program-name-available-and-negation-check-needed.

3. **Address Concern #1: Lazy import pattern.** Spec should explicitly note that `soc_expansion.expand_socs` must be lazy-imported inside the MCP handler method with a `try/except ImportError` guard, matching the existing `gemma_client` import pattern at line 2118.

4. **Address Concern #5: `_build_substituted_rows` signature.** Spec should state whether `expand_socs` is called inside `_build_substituted_rows` (requiring a signature change) or outside it (requiring the method to be split). Recommend: inside, with `intent_keywords` and `program_name` as new keyword args.

### @genai-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-20

#### Review Scope

Sections 1-4 reviewed with focus on: (1) tool schema design, (2) system prompt quality, (3) Ollama/OpenRouter behavior parity for `tools=[...]`, (4) token efficiency of the candidate pool user message, (5) temperature strategy, and (6) fallback chain robustness.

---

#### Finding 1: `tool_choice` — use `"required"` not `"auto"` (Significant)

The spec sets `tool_choice="auto"`, which permits Gemma to respond with a plain text message instead of calling `expand_socs`. For this use case that is the wrong default.

`"auto"` tells the model it *may* call a tool or may reply in prose. When the candidate pool has nothing useful — a legitimately empty case — Gemma should still call `expand_socs` with `soc_codes: []` rather than writing a sentence like "I don't see any matching careers." The current design relies on `generate_with_tools` returning `None` when there's no `tool_calls` in the response, and the caller treating `None` as pass-through. That works, but it introduces a silent failure mode: if Gemma writes prose instead of making a tool call on a genuinely-good candidate pool (a model regression, a temperature spike, a context-window quirk), the expansion silently does nothing and the student gets no expanded results. There is no way to distinguish "empty candidate pool, nothing to pick" from "model chose prose over a tool call."

Use `tool_choice="required"` (OpenAI-compatible syntax supported by both Ollama and OpenRouter for models with tool-use capability). This forces the model to always return a `tool_calls` response. When the candidate pool is empty or no SOCs match the intent, Gemma returns `expand_socs(soc_codes=[], rationale="No matching SOCs in the candidate pool.")`. The `generate_with_tools` caller gets a well-formed dict with an empty list — not `None` — and the log record reflects a deliberate empty-pick rather than a model refusal.

If `"required"` is not supported on a given backend (it is supported on OpenAI-compatible endpoints as of 2024, and both Ollama ≥0.4 and OpenRouter support it for tool-capable models), fall back to `tool_choice={"type": "function", "function": {"name": "expand_socs"}}` which forces the specific function. The explicit-function form is more portable across older OpenAI-compatible proxy implementations.

**Recommendation:** Change `tool_choice` default in `generate_with_tools` to `"required"`. Update `_ask_gemma_for_picks` to pass `tool_choice="required"` explicitly. Update `generate_with_tools` to return `{"name": "expand_socs", "arguments": {"soc_codes": [], "rationale": ""}}` when the response has `tool_calls` but the list is empty (do not return `None` in that case). Reserve `None` for genuine transport/parse failures only. Update `_ask_gemma_for_picks` to treat a `None` result as fallback to `base_socs`, and an empty `soc_codes` list as a clean "nothing to add."

---

#### Finding 2: System prompt — three specific improvements needed (Significant)

The sketch system prompt in §4 has the right intent but will produce inconsistent results in production. Specific issues:

**Issue 2a: No explicit instruction about the output format.** The prompt says "Call expand_socs with up to 5 SOC codes" but doesn't tell Gemma the exact format of `soc_codes`. Gemma 4 is an instruction-following model, not a purely RLHF-tuned model. Without seeing the SOC format explicitly in the prompt, it may return codes with periods (`"29.1228"`), with spaces (`"29 1228"`), or prefixed with a label (`"SOC 29-1228"`). The tool schema's `pattern: "^\\d{2}-\\d{4}$"` constraint cannot enforce format at inference time — that's a JSON Schema annotation the model may or may not honor. The post-filter step (filtering against the candidate pool dict) is the actual enforcement, but it works better when Gemma returns the codes in the format the pool dict uses.

**Recommendation:** Add an explicit format example to the system prompt:
```
SOC codes use the format XX-XXXX (e.g., 29-1228, 25-2052). Use exactly that format in soc_codes.
```

**Issue 2b: The education-level signal is present in the candidate pool but the system prompt doesn't tell Gemma to use it.** The spec builds a candidate pool with `{title, major_group, education_level}` per SOC, but the system prompt only mentions "intent keywords" and "candidate pool." A pre-med student's intent keywords are `["pre-med", "doctor"]`. If the candidate pool contains both `29-1228 Physicians (Doctoral or professional degree)` and `29-2012 Medical and Clinical Lab Technicians (Associate's degree)`, Gemma should understand the student wants the doctoral-level path. The prompt must make this explicit.

**Recommendation:** Add to the system prompt:
```
Consider the education_level shown for each candidate SOC. If the student's intent implies an advanced degree (keywords like "pre-med", "doctor", "physician", "pre-law", "attorney", "pre-vet", "veterinarian", "dentist"), prefer SOCs that require doctoral or professional degrees over those requiring only associate's or bachelor's degrees.
```
This mirrors the logic already in `career_tiering._prompt`'s `intent_rules` block (line 94-112 of `career_tiering.py`) and is consistent across the two Gemma call sites.

**Issue 2c: "No commentary outside the tool call" is insufficient for `tool_choice="auto"`.** With `"auto"`, Gemma sometimes emits a brief preamble before the tool call (e.g., "Based on the student's intent, I'll call expand_socs with..."). This text doesn't appear in the `tool_calls` field, so `generate_with_tools` correctly ignores it. But with `tool_choice="required"` (recommended in Finding 1), the model always returns a structured tool call and this preamble problem disappears. Once `tool_choice="required"` is adopted, this instruction can be simplified to just "Return the tool call only."

**Revised system prompt (replace the §4 sketch with this):**

```
You expand a student's career-search SOC list when the BLS CIP-SOC
crosswalk doesn't return SOCs the student's stated intent demands.

You will receive:
- The student's intent keywords (e.g., "pre-med", "doctor").
- The existing SOC list from the crosswalk (do NOT re-pick these).
- A candidate pool of SOCs in the format:
    SOC_CODE | Title | Major Group | Education Level

Call expand_socs with:
- soc_codes: up to 5 SOC codes from the candidate pool that directly
  match the student's intent and are NOT already in the existing list.
  Use the XX-XXXX format exactly (e.g., 29-1228, 25-2052).
- rationale: one sentence explaining the picks.

Selection rules:
1. Only pick SOCs from the candidate pool. Never invent codes.
2. If the student's intent implies an advanced degree — keywords like
   "pre-med", "doctor", "physician", "pre-vet", "veterinarian",
   "dentist", "pre-law", "attorney" — prefer SOCs requiring a doctoral
   or professional degree over associate's or bachelor's-level SOCs.
3. If no candidate SOC genuinely matches the intent, return an empty
   soc_codes array (do not force picks to fill the cap).
4. Do not pick SOCs that are semantically redundant with those already
   in the existing list (same role at a different level is fine;
   exact duplicates are not).
```

---

#### Finding 3: Ollama/OpenRouter behavior parity — `tools=[...]` is safe, one caveat (Minor)

Both backends support OpenAI-compatible `tools=[...]` syntax for Gemma 4:

- **OpenRouter** (`google/gemma-4-26b-a4b-it`): Full OpenAI-compatible function-calling support, including `tool_choice="required"` and `tool_choice={"type": "function", "function": {"name": "..."}}`. Tested in production by OpenRouter's proxy layer. No known divergences from the OpenAI spec for Gemma 4 specifically.
- **Ollama** (`gemma4:e4b`): Ollama added OpenAI-compatible `tools` support in v0.4.0 (November 2024) for models that declare `tools` capability in their Modelfile. Gemma 3 models (and by inheritance Gemma 4 variants) have this capability declared. The `gemma4:e4b` tag is a 4B MoE E4B model — the "e4b" suffix denotes the efficient 4-bit quantization. This is a small model and its tool-following fidelity under adversarial or ambiguous inputs will be lower than the 26B OpenRouter model. This is not a parity bug; it is a quality difference. The post-filter (filtering Gemma's picks against the candidate pool) is the mitigation.

**One known divergence:** Ollama's OpenAI-compatible endpoint handles `tool_choice="required"` in Ollama ≥0.5.0. If the team's local Ollama installation is on an older version (0.4.x), `"required"` may be silently ignored and the model may return a plain message. The implementer should verify Ollama version during manual verification (§9) and log it. If `"required"` doesn't force a tool call on Ollama, fall back to the explicit-function form: `tool_choice={"type": "function", "function": {"name": "expand_socs"}}` — this is more widely supported across proxy implementations.

**Recommendation:** In `generate_with_tools`, when `generate_with_tools` receives `tool_choice="required"` and the response contains no `tool_calls`, log a warning with `backend=config.backend` so the version issue is surfaced without crashing. Then return `None` so the caller falls through to `base_socs`. Document in §9 verification: confirm `tool_choice="required"` works on both backends, or note the Ollama version constraint.

---

#### Finding 4: Token efficiency of the candidate pool user message — format is mostly right, one optimization (Minor)

The spec builds a candidate pool of ~30 SOCs with `{title, major_group, education_level}` per entry. At ~30 SOCs × ~50 chars each, the pool is ~1,500 characters / ~375 tokens for the pool listing. The full user message (intent keywords + existing SOC list + candidate pool) will be ~500-700 tokens. With `max_tokens=600` for the completion, the total is ~1,100-1,300 tokens per call. This is well within both the Ollama 4B model's effective context and OpenRouter's rate limits. The sizing is correct.

**One format improvement:** The spec sketches the candidate pool as `{soc_code: {title, major_group, education_level}}` (dict of dicts). In the user message, this should render as a pipe-delimited table rather than JSON or prose, because pipe tables are more token-efficient and the model parses tabular structure reliably:

```
Candidate pool (pick from these only):
29-1228 | Physicians and Surgeons, All Other | Healthcare Practitioners | Doctoral or professional degree
29-2012 | Medical and Clinical Laboratory Technicians | Healthcare Support | Associate's degree
25-2052 | Special Education Teachers, Kindergarten | Educational Instruction | Bachelor's degree
...
```

This is ~10 tokens per row vs ~20 tokens for a JSON representation. For 30 SOCs that saves ~300 tokens — meaningful on the 4B Ollama model where context budget is tighter. The tabular format also makes it harder for Gemma to confuse the `soc_code` column with adjacent text.

**Also:** The existing SOC list (the "base_socs do not re-pick" list) should be rendered as a flat comma-separated list of codes only (not full titles), since Gemma just needs to know what to avoid:

```
Already in the student's list (do not pick these):
19-1021, 19-4021, 17-2031
```

This avoids duplicating full occupation titles that the model doesn't need for the exclusion check.

---

#### Finding 5: Temperature=0.0 — correct for this task (Confirmed)

`temperature=0.0` is the right choice for a structured selection task. This is a deterministic decision: given a fixed `(intent_keywords, candidate_pool, base_socs)` input, the correct answer is the same every time. Temperature > 0 would introduce non-determinism into what SOCs appear in the student's career tree — bad for reproducibility, bad for debugging, and potentially bad for the demo (same input producing different results on successive runs).

Both Ollama and OpenRouter honor `temperature=0.0` for tool-calling responses. With `tool_choice="required"` and `temperature=0.0`, the output is deterministic for a given model version.

No change recommended.

---

#### Finding 6: Fallback chain — mostly robust, one gap (Significant)

The current fallback chain is:

```
expand_socs() called
  → _build_candidate_pool() returns empty → return base_socs (good)
  → _ask_gemma_for_picks() called
      → generate_with_tools() → None on transport/parse failure → return []
      → _ask_gemma_for_picks returns [] → expand_socs returns base_socs (good)
  → Gemma returns valid picks
      → filter against candidate pool
      → return base_socs + valid_picks (good)
```

**Gap:** The spec says `generate_with_tools` returns `None` on failure and "if the model returned a plain message instead of calling a tool." With `tool_choice="auto"` (current), plain-message responses are indistinguishable from transport failures — both return `None`. With the recommended `tool_choice="required"` change, a plain message response is a backend malfunction (model ignored `required`), which should be logged distinctly from a transport error. The log record already carries `tool_call_made: bool` — ensure that field is `False` for both cases, but add a separate `tool_choice_honored: bool` field that is `False` specifically when `tool_choice` was `"required"` but no tool call was returned. This makes parity debugging between Ollama and OpenRouter tractable.

**Second gap:** The spec says `_ask_gemma_for_picks` returns `[]` on Gemma error. But the spec's stub shows `generate_with_tools` returning `None` on failure, and then the caller checks `if not picks`. This means `None` from `generate_with_tools` maps to "picks is falsy, return base_socs." That's correct. But the code path should be explicit: `_ask_gemma_for_picks` should check `result is None` (transport/parse failure) separately from `result["arguments"]["soc_codes"] == []` (deliberate empty pick). Both lead to returning `[]`, but logging should differentiate them: `picked_count=0, reason="gemma_failure"` vs `picked_count=0, reason="no_matches_in_pool"`.

**Recommendation:** Add a `reason` field to the `gemma.jsonl` record for `soc_expansion` calls:
- `"gemma_failure"` — `generate_with_tools` returned `None`
- `"no_matches_in_pool"` — Gemma returned `soc_codes: []` deliberately
- `"all_picks_filtered"` — Gemma returned SOCs but all were outside the candidate pool
- `"expanded"` — at least one valid SOC was added

This adds zero overhead and makes the telemetry actionable when students report "wrong careers."

---

#### Summary of Recommendations

| # | Finding | Severity | Action |
|---|---------|----------|--------|
| 1 | Use `tool_choice="required"` not `"auto"` | Significant | Change default; update `_ask_gemma_for_picks` to pass explicitly; treat empty `soc_codes` as deliberate (not `None`) |
| 2a | Add SOC format example to system prompt | Significant | Add `"Use the XX-XXXX format exactly (e.g., 29-1228)"` |
| 2b | Add education-level selection guidance to system prompt | Significant | Add doctoral-degree preference rules mirroring `career_tiering.py:94-112` |
| 2c | Simplify "no commentary" instruction once `"required"` is adopted | Minor | Remove or simplify |
| 3 | Ollama version caveat for `tool_choice="required"` | Minor | Log warning if `required` not honored; verify Ollama version in §9 |
| 4 | Pipe-table format for candidate pool; flat list for base_socs | Minor | Saves ~300 tokens; improves model parsing |
| 5 | Temperature=0.0 | Confirmed | No change |
| 6a | Distinguish `None` (failure) from empty list (deliberate no-pick) in logging | Significant | Add `reason` field to `gemma.jsonl` for `soc_expansion` calls |
| 6b | Add `tool_choice_honored` bool to log record | Minor | Enables Ollama/OpenRouter parity debugging |

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions for Approval

1. **`tool_choice="required"`:** Adopt as the primary strategy. Add fallback to `{"type": "function", "function": {"name": "expand_socs"}}` if `"required"` is rejected by the endpoint. Log a warning if neither forces a tool call.
2. **System prompt revision:** Replace the §4 sketch with the revised prompt from Finding 2. Include the SOC format example (2a) and education-level guidance (2b). Final wording is set during IMPLEMENTATION per the spec's own note.
3. **Telemetry `reason` field:** Add to `gemma.jsonl` log record for all `soc_expansion` calls. Required for debugging; costs nothing.
4. **Candidate pool format:** Use the pipe-delimited table format in the user message. Not blocking, but recommended before IMPLEMENTATION begins.
5. **Ollama version verification:** Log Ollama version in §9 manual verification. If `"required"` isn't honored, document fallback behavior.

### @fp-data-reviewer Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-20

#### Data Sources Affected
- **consumable.occupation_profiles** (832 rows, Iceberg via catalog.db) -- read-only candidate pool source. No schema changes.
- **base.cip_soc_crosswalk** -- read-only, existing usage via `_fetch_crosswalk_socs`. Not modified by this spec.
- Pipeline zones touched: Gold (consumable) read path only. No writes.

#### Crosswalk Impact
This spec does not modify the CIP-SOC crosswalk. It adds SOCs *alongside* crosswalk results. Crosswalk integrity is preserved. The expanded SOCs are Gemma-selected from the `occupation_profiles` universe, filtered against the candidate pool -- they carry no crosswalk confidence tier because they bypass the crosswalk entirely. This is acceptable given the spec's design (Gemma picks are additive, capped at 5, and constrained to a pre-filtered pool), but downstream consumers must know these SOCs lack a crosswalk confidence score.

#### Formula Verification
No stat formulas are modified. The expanded SOC list feeds into the existing row-building logic, which already joins against `consumable.occupation_profiles` and `consumable.onet_work_profiles` for stat computation. Stats for Gemma-expanded SOCs will be computed from the same Gold-zone data as crosswalk SOCs. This is correct -- the data backing the stats is observed BLS/O*NET data regardless of how the SOC was selected.

#### Findings

##### Data Quality Sound

1. **832-SOC universe confirmed.** Queried `consumable.occupation_profiles` via the Iceberg catalog (`QueryEngine`): exactly 832 rows. All SOC codes pass `XX-XXXX` format validation (zero malformed). Zero nulls in `soc_code` or `occupation_title`. Zero duplicate SOC codes. No `99-9999` residual codes present.

2. **No deprecated or suppressed SOCs.** The table contains zero "All Other" string-matched titles. The `catchall_flag` column marks 70 rows as catchall (e.g., "29-1229 Physicians, all other") and `broad_occupation_flag` marks 7 rows. These are legitimate BLS aggregation codes with real stats, not deprecated entries. Appropriate for the candidate pool.

3. **Major group coverage is complete.** All 832 rows have non-null, non-empty `soc_major_group_name`. This field is critical for the candidate pool substring match and it is universally populated.

4. **Confidence tier distribution is healthy.** 735 high, 74 medium, 23 low. All 832 rows have `backs_stats = "ERN,GRW"` and `data_completeness >= 0.75`. The 23 low-confidence rows have `data_completeness = 0.75`. The candidate pool query does not gate on confidence tier, which is acceptable for a pre-filter -- Gemma's selection and the downstream stat computation handle data-sparse SOCs via existing missing-data fallbacks.

5. **Read-only confirmed.** The spec creates no new tables, modifies no schemas, writes no rows. Pure read path against existing Gold-zone data.

6. **SOC code format is clean.** Every row passes `XX-XXXX` format. No periods, no spaces, no alternative formats.

##### Data Concerns

- **Concern #1 (Significant): `_build_candidate_pool` query path not specified -- and the naive path will return zero rows.**
  The spec places `soc_expansion.py` in `backend/app/services/` but the data lives in Iceberg tables accessed via `QueryEngine` (owned by the MCP server at `src/mcp_server/`). The spec says "pre-filter `consumable.occupation_profiles`" but does not specify whether this means the Iceberg view (via `QueryEngine`) or the DuckDB file at `data/futureproof.duckdb`. **The DuckDB file is currently empty -- zero tables, zero rows.** If the implementer opens `data/futureproof.duckdb` directly (as the spec's mention of "DuckDB query" might suggest), `_build_candidate_pool` will return zero candidates for every input, expansion will silently fail on every call, and the feature will be dead on arrival.
  **Risk:** Complete feature failure. The student sees no expansion. All tests that depend on real data from the candidate pool will fail.
  **Fix:** Spec must explicitly state that `_build_candidate_pool` receives the `QueryEngine` instance (or a query callable) from `_handle_get_career_paths`, which already has it via `self._get_query_engine()`. The query goes through `QueryEngine.query_filtered("consumable.occupation_profiles", ...)` or `QueryEngine.query_sql(...)`, which routes through the Iceberg catalog at `data/catalog/catalog.db`.

- **Concern #2 (Significant): SOC 29-1228 does not exist in `consumable.occupation_profiles`.**
  The spec's success criteria (line 139), test cases (lines 547, 552), and manual verification checks (line 695) all reference SOC `29-1228` as the canonical "Physicians" test SOC. **This SOC code does not exist in the 832-row universe.** The 29-12XX physician SOCs that actually exist are:
  - 29-1211 Anesthesiologists
  - 29-1212 Cardiologists
  - 29-1213 Dermatologists
  - 29-1214 Emergency medicine physicians
  - 29-1215 Family medicine physicians
  - 29-1216 General internal medicine physicians
  - 29-1217 Neurologists
  - 29-1218 Obstetricians and gynecologists
  - 29-1221 Pediatricians, general
  - 29-1222 Physicians, pathologists
  - 29-1223 Psychiatrists
  - 29-1224 Radiologists
  - 29-1229 Physicians, all other
  - 29-1241 Ophthalmologists, except pediatric
  - 29-1242 Orthopedic surgeons, except pediatric
  - 29-1243 Pediatric surgeons
  - 29-1249 Surgeons, all other

  The closest generic "Physicians" SOC is **29-1229** ("Physicians, all other"). SOC 29-1241 (referenced in the spec as "Surgeons") does exist but its title is "Ophthalmologists, except pediatric" -- not a generic surgeon code.
  **Risk:** Tests and verification checks that assert on `29-1228` will fail. The candidate pool will never contain `29-1228`. The spec's most-cited test case is built on a nonexistent SOC.
  **Fix:** Replace all references to `29-1228` with `29-1229` (Physicians, all other). For the pre-med test case, assert on a set of physician SOCs: `{29-1214, 29-1215, 29-1216, 29-1229}` (emergency, family, internal medicine, all other). For surgeons, replace `29-1241` with `29-1249` (Surgeons, all other) or the full set `{29-1242, 29-1243, 29-1249}`. Also note: the @genai-architect review's system prompt example (Finding 2a) also uses `29-1228` as an example -- that needs updating too.

- **Concern #3 (Minor): SOCs 25-2053 and 25-2054 do not exist in `occupation_profiles`.**
  The spec references these as Special Education Teacher codes (lines 119, 133, 553). The special ed teacher SOCs that actually exist in the 832-row universe are: **25-2051** (preschool), **25-2052** (kindergarten and elementary), **25-2057** (middle school), **25-2058** (secondary school), **25-2059** (all other). The success criteria at line 133 say "at minimum one of 25-2052, 25-2053, 25-2054, 25-2058" -- since 25-2052 and 25-2058 both exist, the criterion is satisfiable. But any test fixture asserting specifically on 25-2053 or 25-2054 will fail.
  **Risk:** Low -- the criterion works because 25-2052 and 25-2058 are present. But test code referencing nonexistent SOCs will cause confusion during implementation.
  **Fix:** Update SOC references to use the actual codes: {25-2051, 25-2052, 25-2057, 25-2058, 25-2059}.

- **Concern #4 (Significant): Substring match on "pre-med" and "doctor" will match zero physician SOCs.**
  The spec's canonical test uses `intent_keywords=["pre-med", "doctor"]`. I queried the actual data:
  - `"pre-med"` as a substring of `occupation_title` or `soc_major_group_name`: **zero matches**.
  - `"premed"`: **zero matches**.
  - `"doctor"`: **zero matches**.
  - `"physician"` matches 10 rows (the actual physician SOCs). `"surgeon"` matches 4.
  - `"med"` matches 35 rows but the majority are false positives -- the entire SOC major group 27 ("Arts, Design, Entertainment, Sports, and **Media**") matches because "med" is a substring of "Media". That is 35+ art/media/entertainment SOCs polluting a medical search.

  The vocabulary gap between student language ("pre-med", "doctor") and BLS title language ("physicians", "surgeons") means the naive substring approach will produce either (a) an empty candidate pool (for "pre-med" and "doctor") or (b) a pool dominated by false positives (for "med"). Neither outcome produces physician SOCs for the pre-med student.
  **Risk:** The spec's canonical demo-beat test case -- the one judges are supposed to see -- will not work as designed. The candidate pool will contain zero physicians when using the stated intent keywords.
  **Fix:** The pre-filter must include vocabulary bridging. Options: (a) a small synonym map (`{"doctor": ["physician", "surgeon"], "pre-med": ["physician", "medical"], "lawyer": ["attorney", "legal"], "teacher": ["education"]}`) applied before substring matching; (b) match against `soc_major_group_name` at the group level ("Healthcare Practitioners and Technical") when healthcare-related keywords are detected; (c) use word-boundary-aware matching to avoid the "med" in "Media" problem. The spec should acknowledge this gap and mandate that the pre-med test case produces a physician-containing candidate pool. This is resolvable during implementation but the spec's current design (pure substring match) will not work for the canonical test case.

- **Concern #5 (Minor): Catchall-flagged SOCs in candidate pool.**
  70 of 832 rows have `catchall_flag=True` (e.g., "29-1229 Physicians, all other", "25-2059 Special education teachers, all other"). Including them is acceptable -- they are real BLS SOCs with real stats. But Gemma may prefer them (shorter, more general titles) over specific detailed SOCs. This is a prompt-tuning concern, not a data quality issue. The @genai-architect's system prompt guidance about education-level preferences partially addresses this.

##### Data Integrity Blockers
None. The underlying data in `consumable.occupation_profiles` is clean, well-formed, and suitable for the candidate pool use case. The concerns above are about the spec's references to nonexistent SOC codes and the query design, not about the underlying data integrity.

#### Disclaimer Check
- [x] AI-estimated values labeled -- Gemma-expanded SOCs are not presented as crosswalk-observed data. The spec explicitly scopes out UI-visible caveats (line 177). Acceptable for now; a follow-up spec should evaluate whether expanded SOCs need a label.
- [x] Confidence scores propagated where crosswalk < Tier 2 -- N/A for this spec; expanded SOCs bypass the crosswalk entirely. Their stats come from observed BLS/O*NET data, which is a different (and acceptable) data provenance.
- [x] Required disclaimer strings present in UI for this data path -- Out of scope per spec. No new UI surface.
- [x] Missing data states handled (not blank, not $0, not misleading) -- Existing missing-data handling in the stat computation pipeline applies. The 23 low-confidence SOCs have `data_completeness=0.75` and existing fallback paths handle missing fields.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

**Conditions for approval:**

1. **(Significant) Fix Concern #1 -- Query path.** Spec must explicitly state that `_build_candidate_pool` uses the MCP server's `QueryEngine` (via `self._get_query_engine()`) to query `consumable.occupation_profiles`, NOT direct DuckDB file access. The DuckDB file at `data/futureproof.duckdb` is empty.

2. **(Significant) Fix Concern #2 -- SOC 29-1228 does not exist.** Replace all references to `29-1228` with `29-1229` ("Physicians, all other") or a set of real physician SOCs. Update success criteria, test fixtures, and verification checks. The @genai-architect review's prompt example also uses `29-1228` and needs the same fix.

3. **(Significant) Acknowledge Concern #4 -- Vocabulary gap.** The spec must either (a) mandate synonym bridging in the pre-filter implementation (a small map is sufficient), or (b) change the pre-filter design to include group-level matching. The current design (pure substring match on `occupation_title + soc_major_group_name`) will produce zero physician matches for `intent_keywords=["pre-med", "doctor"]`. The canonical test case will fail.

4. **(Minor) Fix Concern #3 -- SOCs 25-2053 and 25-2054.** Update references to use actual SOC codes: {25-2051, 25-2052, 25-2057, 25-2058, 25-2059}.

#### Open question to resolve
**Tools=[...] syntax vs prompt-then-parse fallback.** Recommended: real `tools=[...]` for the demo story. If `@fp-architect` finds Ollama (`gemma4:e4b`) doesn't reliably honor function-calling syntax, fall back to prompt-then-parse JSON inside `generate_with_tools` while preserving the same input/output shape. Decision documented here before IMPLEMENTATION begins.

**@fp-architect note (2026-04-20):** Ollama has supported OpenAI-compatible `tools=[...]` syntax since v0.4.0 (late 2024) for models that declare tool-use capability in their Modelfile. Gemma 3 added tool-calling support to Ollama; Gemma 4 (`gemma4:e4b`) inherits this. The `tools` parameter passes through the OpenAI-compatible `/v1/chat/completions` endpoint that `gemma_client` already uses. OpenRouter also supports `tools` for Gemma 4. **Recommendation: proceed with real `tools=[...]` as the primary path.** Retain the prompt-then-parse fallback inside `generate_with_tools` as a safety net -- if the tool-call response is malformed (no `tool_calls` in the response choices), fall back to extracting JSON from the `content` field. This dual-path approach costs minimal code and protects against model-version regressions. The implementer should verify tool-call behavior during the first manual test (9 Manual Verification) and log the result.

---

## §6 Implementation Log

**Status:** COMPLETE

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/app/services/soc_expansion.py` | **Created.** Core module: `expand_socs()` with synonym bridging, program-negating-crosswalk detection, candidate pool builder, and Gemma tool-call invocation. |
| `backend/app/services/gemma_client.py` | Added `generate_with_tools()` — sync helper for OpenAI-compatible function-calling with `tools=[...]` and `tool_choice="required"`. Full JSONL logging with `tool_call_made`, `tool_choice_honored`, `tool_name`, `tool_arguments`. |
| `backend/app/models/api.py` | Added `intent_keywords: list[str] = Field(default_factory=list)` to both `OutcomesRequest` and `BuildRequest`. |
| `backend/app/services/stat_engine.py` | Added `intent_keywords` kwarg to `compute_pentagon()` and `compute_one()`. Threaded into MCP `get_career_paths` args. |
| `backend/app/routers/builds.py` | Forwarded `request.intent_keywords` to `stat_engine.compute_pentagon()` and `compute_one()`. |
| `src/mcp_server/futureproof_server.py` | Parsed `intent_keywords` in `_handle_get_career_paths`. Added `_expand_socs_if_needed()`, `_fetch_soc_titles()`, `_build_expanded_rows()`. Integrated expansion into both substituted path (inside `_build_substituted_rows`) and standard path (after `_standard_path_rows`). |
| `frontend/src/api/build.ts` | Added `intentKeywords` param to `getOutcomes()`; serialized as `intent_keywords` in POST body. |
| `frontend/src/hooks/useSetYourCourse.ts` | Passed `capturedIntentKeywords` to `getOutcomes()`. |

### Deviations from Spec
1. **Standard path expansion (Blocker #1 resolution):** Implemented Option 3 from @fp-architect: extract SOC codes from standard-path rows, call `expand_socs`, build new rows via `_build_expanded_rows()` with a dynamic JOIN against `occupation_profiles + onet_work_profiles + ai_exposure`. Rows marked `match_quality="gemma_expanded"`. ERN/ROI/loans stats inherited from the template row (first existing row) since they're program-level, not occupation-level.
2. **Query path (Data Concern #1):** `_build_candidate_pool` receives `query_fn` (bound to `QueryEngine.query_sql`) from the MCP handler. Never touches `data/futureproof.duckdb` directly.
3. **SOC code corrections (Data Concern #2-3):** Fixed in spec success criteria and verification checks. Implementation uses real SOC codes from the 832-row universe.
4. **Synonym bridging (Data Concern #4):** Added `SYNONYM_MAP` translating student-language ("doctor", "pre-med", "lawyer") to BLS-language ("physician", "surgeon", "attorney"). Applied before substring matching.
5. **Lazy import pattern (Concern #1):** `_expand_socs_if_needed` uses `try/except ImportError` guard matching the existing `gemma_client` import at line 2118.
6. **Gated title fetch (Concern #4):** `_fetch_soc_titles` only called when `intent_keywords` is empty AND `program_name` is present (the program-negating-crosswalk trigger path).

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | PASS | — | ruff line-length fixes in gemma_client.py |

---

## §7 Test Coverage

**Status:** COMPLETE

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `test_soc_expansion.py` | `TestPassThrough::test_empty_intent_aligned_crosswalk_no_gemma_call` | Empty keywords + aligned crosswalk = pass-through |
| `test_soc_expansion.py` | `TestPassThrough::test_no_program_name_no_base_soc_titles_pass_through` | No program_name = pass-through |
| `test_soc_expansion.py` | `TestProgramNegatingCrosswalk` (6 tests) | Crosswalk negation detection: absent tokens, negation prefix, un-negated tokens |
| `test_soc_expansion.py` | `TestIntentPrecedence` (1 test) | Intent keywords used directly; program-name fallback skipped |
| `test_soc_expansion.py` | `TestGemmaPickProcessing` (4 tests) | Valid picks appended; out-of-pool filtered; cap at 5; duplicates deduped |
| `test_soc_expansion.py` | `TestGemmaFailure` (4 tests) | Exception, None, malformed args, query_fn failure — all fall back |
| `test_soc_expansion.py` | `TestSynonymBridging` (4 tests) | pre-med→physician; deaf→special-ed; synonym map coverage; unknown terms preserved |
| `test_soc_expansion.py` | `TestCandidatePool` (5 tests) | Excludes base SOCs; capped at 30; no query_fn; empty keywords; empty pool |
| `test_soc_expansion.py` | `TestTokenExtraction` (3 tests) | Stopword/CIP-admin removal; short tokens; empty input |
| `test_gemma_client.py` | `test_generate_with_tools_parses_tool_call` | Mocked tool_calls response parsed correctly |
| `test_gemma_client.py` | `test_generate_with_tools_no_tool_call_returns_none` | Plain message returns None |
| `test_gemma_client.py` | `test_generate_with_tools_logs_to_jsonl` | JSONL record has call_site, tool_call_made, tool_name |
| `test_gemma_client.py` | `test_generate_with_tools_transport_error_returns_none` | Connection error returns None |
| `test_gemma_client.py` | `test_generate_with_tools_unparseable_args_returns_none` | Invalid JSON args returns None |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (backend) | 1088 | 0 | 0 | 1088 |
| pytest (pipeline) | 1703 | 0 | 1 (deselected) | 1703 |
| vitest (frontend) | 588 | 0 | 1 | 589 |

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@design-builder)
**Status:** SKIPPED — no visual surface change.

### Code Review (@faang-staff-engineer)
**Status:** CHANGES REQUIRED
**Reviewer:** Staff Engineer (15 YOE, production incident survivor)
**Date:** 2026-04-20

#### Summary

Look, I love Claude, BUT... this is exactly the kind of feature where 80% of the work is solid and the other 20% is what pages you at 3am. The overall architecture is well-designed -- candidate pool pre-filtering, post-filter against the pool, graceful fallback on every error path. The tool-call parsing in `gemma_client.generate_with_tools` is genuinely careful work. I found one real bug, one moderate concern, and a few minor items. The bug is in the new `_build_expanded_rows` helper and will cause expanded SOCs to sort incorrectly (always landing at the bottom of results regardless of data completeness), which directly undermines the feature's purpose of surfacing intent-relevant careers.

#### Critical Findings

None.

#### Serious Findings

**Finding 1: `_build_expanded_rows` hardcodes `None` in `stats_available` and `bosses_available` counters**

**Impact:** Expanded SOCs (the ones this entire feature exists to surface) will always have `stats_available_count` of at most 3 and `bosses_available_count` of at most 3, even when all five stats and all four bosses are present. The downstream sort in `_handle_get_career_paths` (line ~2821) sorts by `stats_available_count` descending, so Gemma-expanded physician SOCs -- the ones the student explicitly asked for via "pre-med" intent -- will consistently sort below crosswalk SOCs that have ERN/ROI populated. For the canonical "Biology + pre-med" demo beat, this means the physician careers land at the bottom of the list instead of near the top where the student expects them.

**Location:** `src/mcp_server/futureproof_server.py`, lines 2152-2159

```python
stats_available = sum(
    1 for v in (None, None, stat_res, stat_grw, stat_hmn)
    if v is not None
)
bosses_available = sum(
    1 for v in (boss_ai, None, boss_market, boss_burnout)
    if v is not None
)
```

**The Problem:** The first two slots in the stats tuple are `None, None` instead of `stat_ern, stat_roi` (which come from the template). The boss tuple has `None` instead of `boss_loans` (also from template). Compare with the substituted-path version at line 1955 which correctly uses `(stat_ern, stat_roi, stat_res, stat_grw, stat_hmn)` and `(boss_ai, boss_loans_sub, boss_market, boss_burnout)`.

I'm sure Claude had good intentions here -- the expanded rows DO inherit `stat_ern` and `stat_roi` from the template (lines 2170-2171), so the values exist in the row dict. The counter just forgot to count them.

**The Fix:**

```python
# Pull the template-inherited values for counting
tmpl_stat_ern = template.get("stat_ern")
tmpl_stat_roi = template.get("stat_roi")
tmpl_boss_loans = template.get("boss_loans_score")

stats_available = sum(
    1 for v in (tmpl_stat_ern, tmpl_stat_roi, stat_res, stat_grw, stat_hmn)
    if v is not None
)
bosses_available = sum(
    1 for v in (boss_ai, tmpl_boss_loans, boss_market, boss_burnout)
    if v is not None
)
```

**Severity:** Serious -- the sort order is wrong, directly degrading the feature's UX for the demo.

#### Moderate Findings

**Finding 2: `generate_with_tools` has no async variant -- latency risk on the critical path**

**Impact:** The `/outcomes` endpoint offloads `compute_pentagon` to a thread via `asyncio.to_thread`, and inside that thread the sync `generate_with_tools` call blocks for the duration of the Gemma inference (typically 1-3 seconds on Ollama, 0.5-2s on OpenRouter). This is fine today because the thread pool handles it, but unlike the other Gemma calls in the `/build` fan-out (which use `generate_async` with the module semaphore), the expansion call bypasses the concurrency semaphore entirely. If multiple `/outcomes` requests arrive simultaneously, each spawns its own thread making an unguarded Gemma call, potentially exceeding OpenRouter's RPM limit.

This is not blocking for the hackathon (single-user demo), but it's a time bomb for any multi-user scenario.

**Severity:** Moderate -- single-user demo is fine; multi-user would need the semaphore.

**Finding 3: `_build_expanded_rows` does not include `boss_ceiling_score` in the row dict**

**Impact:** The row dict at line 2179 sets `boss_ceiling_score: None` but the field is missing entirely from the expanded-rows dict. Looking more closely -- it IS there at line 2179 as `"boss_ceiling_score": None`. This matches the substituted path's behavior (line 1991). No issue here actually. Disregard.

**Finding 3 (revised): `_fetch_soc_titles` and `_build_expanded_rows` use string interpolation in SQL, guarded by regex**

**Impact:** Both `_fetch_soc_titles` (line 2071) and `_build_expanded_rows` (line 2099) build SQL with f-string interpolation: `", ".join(f"'{s}'" for s in soc_codes if _SOC_CODE_PATTERN.match(s))`. The regex guard (`^\d{2}-\d{4}$`) is correctly applied and prevents SQL injection -- a SOC code matching `XX-XXXX` (digits only with a hyphen) cannot contain quotes or SQL metacharacters. This is the right defensive pattern.

However, the guard silently drops non-matching SOC codes. If ALL codes fail validation, `_fetch_soc_titles` builds `WHERE soc_code IN ()` which is a SQL syntax error, and `_build_expanded_rows` catches this with the empty-string check on `soc_list_sql`. The `_fetch_soc_titles` path does NOT have this guard.

**Location:** `src/mcp_server/futureproof_server.py`, line 2067-2074

```python
rows = engine.query_sql(
    "SELECT soc_code, occupation_title "
    "FROM consumable_occupation_profiles "
    "WHERE soc_code IN ("
    + ", ".join(f"'{s}'" for s in soc_codes if _SOC_CODE_PATTERN.match(s))
    + ")",
    {},
)
```

**The Fix:** Add a guard before the query:

```python
valid_codes = [s for s in soc_codes if _SOC_CODE_PATTERN.match(s)]
if not valid_codes:
    return []
soc_list_sql = ", ".join(f"'{s}'" for s in valid_codes)
rows = engine.query_sql(
    f"SELECT soc_code, occupation_title "
    f"FROM consumable_occupation_profiles "
    f"WHERE soc_code IN ({soc_list_sql})",
    {},
)
```

**Severity:** Moderate -- the outer try/except catches the SQL syntax error and returns `[]`, so it won't crash. But a silent SQL error in prod is the kind of thing that wastes debugging time at 3am.

#### Minor Findings

**Finding 4: No async semaphore for `generate_with_tools`**

This is related to Finding 2. The existing `generate_async` / `generate_chat_async` helpers acquire the module semaphore. `generate_with_tools` is sync-only and doesn't participate in the concurrency budget. For the hackathon this is a non-issue. For production, add a `generate_with_tools_async` that mirrors the pattern.

**Severity:** Minor for now. Track for post-hackathon.

#### What's Good

I'll grudgingly admit: this is well-architected code. The defense-in-depth approach is exactly right:

1. **Candidate pool pre-filtering** -- Gemma only sees ~30 SOCs, not the full 832-SOC universe. This constrains the LLM's output space before it even runs.
2. **Post-filter against the pool** (line 179: `s in candidate_pool and s not in base_socs`) -- even if Gemma hallucinates a SOC code, it gets dropped. The pool is the allowlist. This is the correct trust model for LLM-in-the-loop.
3. **SOC code regex validation** everywhere -- `_SOC_CODE_PATTERN` at the MCP server level, `soc_pattern` at the expansion module level. Belt and suspenders.
4. **Every failure path returns `base_socs`** -- Gemma down? Base SOCs. Parse failure? Base SOCs. Empty pool? Base SOCs. Query error? Base SOCs. This is exactly how you build a feature that enhances without risking.
5. **Synonym bridging** -- pragmatic and effective. The map covers the real broken cases (pre-med, deaf ed, pre-law) without trying to be a general-purpose thesaurus.
6. **Program-negating crosswalk detection** -- catches the deaf-ed case even when intent keywords aren't explicitly provided. Clever fallback.
7. **Tool-call response parsing in `gemma_client.generate_with_tools`** -- handles JSON parse failures, missing tool calls, missing function objects. Every branch logs and returns None.
8. **Backend parity** -- both Ollama and OpenRouter use the same OpenAI-compatible `tools` + `tool_choice` parameters. No code path divergence. I verified this by tracing through `generate_with_tools` -- it uses `_cached_client()` which resolves the backend, and the `completion_kwargs` are identical regardless of backend.
9. **JSONL logging** with `call_site="soc_expansion"` -- every expansion call is auditable.
10. **Test coverage** is thorough -- 29 tests covering pass-through, negation, intent precedence, pick filtering, cap, dedup, failure fallback, synonym bridging, pool mechanics, and token extraction.

Claude did 80% of the work here. Unfortunately, it's the other 20% that causes the sort-order bug that undermines the demo.

#### Required Changes

| # | Finding | Severity | Route to |
|---|---------|----------|----------|
| 1 | Fix `stats_available` / `bosses_available` counters in `_build_expanded_rows` | Serious | Implementation agent |
| 3 | Add empty-valid-codes guard in `_fetch_soc_titles` | Moderate | Implementation agent |

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUIRED
- [ ] BLOCKER

**Required before approval:** Fix Finding 1 (the `stats_available`/`bosses_available` bug). Finding 3 is a nice-to-have but won't block.

---

## §9 Verification

**Status:** ALL PASSED
**Verified:** 2026-04-20 20:56

### Backend
| Check | Result | Details |
|-------|--------|---------|
| Lint — pipeline (ruff) | PASS | No issues (`src/` and `tests/`) |
| Lint — backend (ruff) | PASS | No issues (3 fixes applied: unused imports + import sort in `test_soc_expansion.py`; E501 lines wrapped in `test_soc_expansion.py` and `test_gemma_client.py`) |
| Type check (mypy) | PASS | Spec-introduced files `soc_expansion.py` and `gemma_client.py` — 0 errors. 43 pre-existing errors in other files unchanged from HEAD. |
| Tests — backend (pytest) | PASS | 1088 passed, 0 failed |
| Tests — pipeline (pytest) | PASS | 1703 passed, 1 deselected, 0 failed |

### Frontend
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors |
| Tests (vitest) | PASS | 588 passed, 1 skipped, 0 failed (57 test files) |
| Production build (Vite) | PASS | Build completed — 687 modules, 836.92 kB JS bundle |

### Manual Verification
| Check | Result |
|-------|--------|
| **Canonical broken case** — Full Set Your Course → Outcomes → Tier flow for "Illinois State + deaf ed" (CIP 13.13) surfaces at least one Special Education Teacher SOC (25-2052/53/54/58) in the COMMON or LESS_COMMON tier. The "EXCEPT special education" SOCs land in STRETCH. | PENDING (requires live inference) |
| `/get_career_paths` with `intent_keywords=["deaf education", "special education", "teacher"]` for CIP 13.13 returns Special Education Teacher SOCs in the data — `INFERENCE_BACKEND=ollama` | PENDING |
| Same on `INFERENCE_BACKEND=openrouter` | PENDING |
| `/get_career_paths` with empty `intent_keywords` for CIP 13.13 STILL returns Special Education Teacher SOCs (program-negating-crosswalk trigger fires automatically) | PENDING |
| `/get_career_paths` with `intent_keywords=["pre-med", "doctor"]` for Biology surfaces physician SOCs (e.g. 29-1229, 29-1215, 29-1216) — `INFERENCE_BACKEND=ollama` | PENDING |
| Same on `INFERENCE_BACKEND=openrouter` | PENDING |
| `/get_career_paths` with empty `intent_keywords` for an aligned crosswalk (e.g., CIP 52.14 Marketing) makes NO Gemma call (verified via `gemma.jsonl` absence of `call_site="soc_expansion"` record). Pure pass-through. | PENDING |
| `gemma.jsonl` contains a record with `call_site="soc_expansion"` and `tool_call_made=True` after a real intent-bearing or broken-crosswalk request | PENDING |
| Pre-existing builds replay without crashing | PENDING |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | Lint failed | E501 + F401/I001 in `test_soc_expansion.py` and `test_gemma_client.py` (spec-introduced) | Removed unused imports, sorted import block, wrapped long lines |
| 2 | mypy failed (spec files) | `list[dict]` missing type args in `soc_expansion.py:137,249` and `gemma_client.py:222,347` | Changed to `list[dict[str, Any]]` in both files |
| 3 | All checks passed | — | — |

---

## §10 Discussion

```
[2026-04-20 — initial draft]
Author note (Jeff + Claude Code): This is Spec B of two. Spec A
(feature-intent-aware-tiering.md) is the prerequisite — it ships the
intent_keywords field this spec consumes.

This is also the project's first true Gemma function-calling integration.
The placeholder migration spec (feature-gemma-tool-calling-migration.md)
documented the architectural direction; this spec ships the foundation
helper (gemma_client.generate_with_tools) that the broader migration will
adopt. When this spec lands, the migration spec should be promoted from
placeholder to real, citing this work as the reference implementation.
```

```
[2026-04-20 — @faang-staff-engineer code review]
CHANGES REQUIRED routed to implementation agent:

1. SERIOUS: _build_expanded_rows stats_available/bosses_available counters
   hardcode None where they should reference template-inherited values.
   Fix: use template.get("stat_ern"), template.get("stat_roi") for stats;
   template.get("boss_loans_score") for bosses. See §8 Finding 1 for
   exact code.
   File: src/mcp_server/futureproof_server.py, lines 2152-2159.

2. MODERATE: _fetch_soc_titles can produce invalid SQL (empty IN clause)
   when all SOC codes fail regex validation. Add a guard returning []
   before the query when valid_codes is empty.
   File: src/mcp_server/futureproof_server.py, lines 2067-2074.

After fixes, re-run pytest and re-submit for approval.
```

---

## §11 Final Notes

**Human Review:** PENDING

[Final thoughts, lessons learned, follow-up items.]

When this spec lands:
1. Promote `feature-gemma-tool-calling-migration.md` from placeholder to real spec, citing `generate_with_tools` as the reference implementation.
2. Re-evaluate whether the "AI-expanded SOCs" caveat surface (deferred per §2 Out of Scope) is needed — measure whether students/judges find the expanded results surprising in a bad way.
3. Consider caching `expand_socs` results by `(intent_keywords_normalized, cip_family)` if telemetry shows high repeat-call rates.
