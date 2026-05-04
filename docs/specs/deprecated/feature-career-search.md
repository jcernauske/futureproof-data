# Feature: Career Search From Intent (Header-Menu Page)

> **⚠️ FILE-RECOVERY NOTE (2026-04-29):** This file is a **redraft skeleton**, NOT a
> recovery of the original spec. The original `feature-career-search.md` was lost
> from disk during the same incident that took out
> `feature-compare-schools-for-career.md` (cause undetermined). This skeleton was
> reconstructed from references in the sibling spec only — not from any read of
> the original. Sections marked **[REDRAFT — NEEDS USER INPUT]** must be filled
> in by the author before any agent pipeline can run against this spec. Use the
> `fp-spec-writer` skill to flesh this out properly.

## Claude Code Prompt

```
Read the spec at docs/specs/feature-career-search.md in its entirety.

This spec is currently a REDRAFT SKELETON. Do NOT execute the workflow until
the [REDRAFT — NEEDS USER INPUT] sections are filled in by Jeff. Once filled,
the workflow should follow the standard FP §1-§11 pattern with these
agent gates:

1. ARCHITECTURE REVIEW — @fp-architect + @fp-data-reviewer (intent-resolution
   correctness; Gemma function-calling integration; relationship to the
   sibling spec's `by_soc` mode click-through path).
2. DESIGN VISION — @fp-design-visionary fills §3 (header-menu entry, search
   page surface, intent-to-results UX, Brightpath dark-first).
3. GENAI REVIEW — @genai-architect for the intent-extraction prompt + tool
   schema (POST /careers/search-from-intent).
4. IMPLEMENTATION — Claude Code.
5. TESTING — @test-writer.
6. DESIGN AUDIT — @fp-design-auditor.
7. CODE REVIEW — @faang-staff-engineer.
8. VERIFICATION — @fp-builder.
9. COMPLETION.
```

---

## Status: DEPRECATED 2026-05-03

> **Deprecated.** This was a redraft skeleton after the original spec was lost. Career search is already reachable through the live product surfaces (Set Your Course chip flow, branch tree, compare). Reconstructing the original from sibling references isn't worth the effort before submission. If a dedicated header-menu career-search page is wanted later, write fresh against the shipped UI.

| Status | Meaning |
|--------|---------|
| REDRAFT SKELETON | File-recovery placeholder; needs Jeff to flesh out |
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect + @fp-data-reviewer approval |
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
| Spec Version | 0.1 (redraft skeleton — original lost) |
| Last Updated | 2026-05-03 (DEPRECATED — redraft skeleton abandoned; career search already reachable through shipped surfaces) |
| Blocked By | Original file content needs to be recovered or rewritten |
| Related Specs | `docs/specs/feature-compare-schools-for-career.md` (sibling — Spec A; click-through destination from this spec's career-search results is Spec A's `by_soc` mode), `docs/specs/feature-header-persistent-actions.md` (header-menu entry-point host), `docs/specs/feature-ask-gemma.md` (Gemma chat surface that this spec's intent-resolution model may share patterns with) |

---

## §1 Feature Description

### Overview (from Spec A references)

A free-text career search page reachable from the header menu. Students type
an intent ("I want to help kids learn", "I'm into design but want to make
money", "what should I do with a chemistry degree?") and the page returns a
ranked list of careers (SOC codes) with brief explanations. Clicking a career
navigates to Spec A's peer-school leaderboard in `by_soc` mode (i.e., the
"compare schools for this career" surface, anchorless when the user has no
active build).

### Problem Statement [REDRAFT — NEEDS USER INPUT]

The original spec presumably articulated:
- Why a header-menu career search page (vs. a homepage entry, vs. a build-flow
  step).
- The student question this answers ("I don't know what I want to do; help me
  find a career").
- Why intent-search beats taxonomy browse for this user.

These aren't recoverable from Spec A's references. Please fill in.

### Success Criteria [REDRAFT — NEEDS USER INPUT]

Likely-applicable criteria inferred from Spec A:

- [ ] A new header-menu entry "Career Search" (or similar; Brightpath voice
      copy TBD) routes to a new page (`/careers/search` or similar).
- [ ] The page accepts free-text intent input.
- [ ] Backend endpoint `POST /careers/search-from-intent` returns a ranked
      list of SOC codes with explanations, powered by Gemma function-calling
      against the existing MCP tool surface.
- [ ] Click-through on a career routes to Spec A's `by_soc` mode (anchorless
      when no active build).
- [ ] Empty / sparse / Gemma-unavailable states are handled per Brightpath.
- [ ] Full pytest + vitest + tsc + ruff + mypy green.

The actual list needs your input — which of these the original spec called
out, what additional criteria it included, and what scope it explicitly
deferred.

---

## §2 Design Decisions [REDRAFT — NEEDS USER INPUT]

The original spec presumably captured decisions on:
- Why a separate page vs. a search box embedded in the header.
- Whether intent-resolution runs through Gemma function-calling, a structured
  classifier, or a hybrid.
- How results are ranked and how many to show.
- Whether the page is anchored to an active build (and if so, what that
  changes).
- Voice/copy decisions on the page (placeholder text, empty states, error
  states).
- Scope of Gemma's response — natural-language explanation per career?
  Stat-pentagon previews? Career card summaries?
- Out-of-scope items (e.g., saving searches, share-link permalinks, etc.).

These need to be re-captured. Use `fp-spec-writer` skill or rewrite from
memory.

---

## §3 UI/UX Design

**Status:** PENDING (visionary fills this section after §1–§2 are completed.)

Notes from Spec A:
- The header-menu entry-point host is `feature-header-persistent-actions.md`.
- Career-card click-through navigates to Spec A (`feature-compare-schools-for-career.md`)
  in `by_soc` mode. Spec A handles the anchorless rendering when no build is
  active.

---

## §4 Technical Specification

**Status:** PENDING (skeleton below; needs to be expanded after §1–§2.)

### Architecture Overview (inferred)

This is additive scope. New surfaces:

1. **Backend endpoint** — `POST /careers/search-from-intent` on
   `backend/app/routers/careers.py` (the same router Spec A creates). Accepts
   a free-text intent in the body, returns a ranked list of SOC codes plus
   per-career explanation text. Likely delegates to a new service
   (`backend/app/services/career_search.py` or similar) that orchestrates
   Gemma function-calling against the existing MCP tool surface.
2. **Frontend** — a new search page route, header-menu entry, and frontend
   API client function (`searchCareers` in `frontend/src/api/careers.ts`,
   which Spec A creates with two functions; this spec extends with a third).
3. **Gemma integration** — intent extraction + career ranking prompt(s),
   tool-calling against existing MCP tools (`get_career_paths`,
   `get_occupation_data`, `get_schools_for_career`), and a fallback path when
   Gemma is unavailable.

### File Changes [REDRAFT — NEEDS USER INPUT]

Likely scope (reconstruct from Spec A references; verify completeness):

| File | Action | Description |
|------|--------|-------------|
| `backend/app/routers/careers.py` | Modify | Add `POST /careers/search-from-intent` to the router Spec A creates. |
| `backend/app/services/career_search.py` | Create | Service that orchestrates Gemma intent extraction → MCP tool calls → ranked career response. |
| `backend/app/models/career.py` | Modify | Add Pydantic models for `CareerSearchRequest` (intent text), `CareerSearchResult` (per-career row with explanation), `CareerSearchResponse`. |
| `frontend/src/api/careers.ts` | Modify | Add `searchCareers(intent)` function. |
| `frontend/src/screens/CareerSearchScreen.tsx` | Create | New search page. |
| `frontend/src/components/ui/AppHeader.tsx` | Modify | Add the header-menu entry. |
| `frontend/src/i18n/strings.ts` | Modify | Strings for the page, empty state, errors, header entry. |
| Tests for all of the above | Create / Modify | Coverage. |

### Open Questions [REDRAFT — NEEDS USER INPUT]

- Does intent-resolution use Gemma function-calling, a deterministic keyword
  matcher, or a hybrid?
- What is the response shape — pure SOC list, or pre-joined with stat
  pentagons / occupation titles / first-school previews?
- How does this interact with the global Gemma availability state from
  `feature-gemma-availability.md`? What's the fallback when Gemma is down?
- Caching strategy for repeat intent searches?
- Rate limiting?

### Testing Impact Analysis [REDRAFT — NEEDS USER INPUT]

The router file is shared with Spec A — coordinate to avoid stepping on
each other's tests. Tests for the new endpoint, service, and frontend page
all need to be specified per the standard FP test priority table.

---

## §5 Architecture Review

**Status:** PENDING

### @fp-architect Review
**Status:** PENDING

### @fp-data-reviewer Review
**Status:** PENDING

---

## §6 Implementation Log

**Status:** PENDING

---

## §7 Test Coverage

**Status:** PENDING

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@fp-design-auditor)
**Status:** PENDING

### Code Review (@faang-staff-engineer)
**Status:** PENDING

---

## §9 Verification

**Status:** PENDING

---

## §10 Discussion

```
[2026-04-29] @claude-code → @jcernauske
This file is a reconstruction skeleton, not a recovery. The original spec
was lost from disk and was never read by Claude Code in this session, so
the original content is not in conversation context. The sibling spec
(feature-compare-schools-for-career.md) was successfully reconstructed
because its full content WAS in context. This file documents what the
sibling spec references so the spec author can rebuild from a known
starting point — but every section marked [REDRAFT — NEEDS USER INPUT]
needs explicit human input before agents should run this workflow.

Recommended next step: invoke the `fp-spec-writer` skill against this
file to draft proper §1–§4 content from your memory of the original
intent.
```

---

## §11 Final Notes

**Human Review:** REQUIRED before workflow execution.

**File-recovery note (2026-04-29):** This is a redraft skeleton, not a
recovery. Original on-disk content is unrecoverable. References from the
sibling spec `feature-compare-schools-for-career.md` were used to seed the
skeleton with what little is known: the file's title, that it adds a
header-menu Career Search page, that click-throughs route to the sibling
spec's `by_soc` mode, that it adds `POST /careers/search-from-intent` to
the same router. Everything else needs to be rewritten by the author.
