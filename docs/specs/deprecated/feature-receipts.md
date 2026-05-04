# Feature: Receipts — Data Provenance as a First-Class Product Surface

## Claude Code Prompt (to be finalized when promoted from backlog)

```
Read the spec at docs/specs/feature-receipts.md in its entirety.

Execute the standard FutureProof workflow:

1. ARCHITECTURE REVIEW — @fp-architect (new service, schema additions to
   multiple response types, Gemma prompt changes across several call sites).
2. DESIGN VISION — @fp-design-visionary (inline-citation treatment,
   card-footer attribution, hover tooltips (post-hackathon), "Our Sources"
   page (post-hackathon)).
3. COPY REVIEW — @fp-copywriter (canonical source names + first-reference
   acronym rule applied consistently across all student-facing surfaces).
4. IMPLEMENTATION — follow §4.
5. TEST — @test-writer.
6. DESIGN AUDIT — @fp-design-auditor.
7. CODE REVIEW — @faang-staff-engineer.
8. VERIFICATION — @fp-builder.
9. COMPLETION — standard sequence.
```

---

## Status: DEPRECATED 2026-05-03

> **Deprecated.** The v0.5 hackathon slice (acronym spell-out rule + canonical source registry + card-footer attribution) shipped alongside `feature-set-your-course.md` and is sufficient for submission. The post-hackathon full scope (per-stat hover tooltips, vintage on every number, "Our Sources" page, citation discipline at every Gemma site) is **not being pursued**. If the receipts surface needs to expand later, write a new spec scoped to that specific addition rather than reviving this skeleton.
>
> §1–§4 below describe the original full vision and are preserved for historical reference only.

---

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-19 |
| Last Updated | 2026-05-03 (DEPRECATED — v0.5 stub already shipped is sufficient; full spec abandoned) |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 0.1 (skeleton) |
| Blocked By | — |
| Related Specs | `docs/specs/feature-set-your-course.md` (first consumer — chip-routing prompt requires inline citations; career preview cards carry footer attribution), `docs/specs/feature-school-discovery.md` (card attribution on the discovery list), `docs/specs/feature-chat-guardrails.md` (hallucination defense — citation discipline is first line), `docs/specs/feature-gemma-tool-calling-migration.md` (every migrated call site inherits the citation rule + registry) |
| Mockup reference | `docs/specs/design/set-your-course-mockup/index.html` — **Scenarios 3, 8, 9, 13** show the updated copy that names Indiana University's submission to IPEDS and cites BLS by full name + acronym; the card footer attribution treatment per v0.5 lives beneath the career preview (scenarios 3 + 10) |

---

## §1 Feature Description

### Overview

Every factual claim the product makes — earnings numbers, career mappings, school programs, cost-of-living adjustments, AI exposure scores — carries a **visible receipt**: a named source with a vintage year. Students (and especially their parents) see where the data came from, not a black-box answer. Gemma's prose cites sources inline; career cards carry a subtle footer attribution; key stats (post-hackathon) show source and vintage on hover; a dedicated "Our Sources" page (post-hackathon) lists the full dataset catalog with authority links.

This feature exists because:

1. **Trust.** Large language models hallucinate. FutureProof reads public federal data and reasons over it with Gemma — every number has a receipt. Surfacing that explicitly is the product's anti-hallucination flex.
2. **Voice.** The voice guide says "data-honest." Hiding sources is not data-honest. Citing them is.
3. **Parents.** Parents care where the numbers come from. "According to the Bureau of Labor Statistics (BLS)…" is exactly the language they respect.
4. **Kaggle demo.** A career card showing "Source: BLS Occupational Outlook Handbook · College Scorecard 2023" is screenshot-worthy — and it's the opposite of what a typical LLM-powered demo looks like.
5. **It answers the "filed with whom?" question.** When Gemma says "IU reports Marketing within its Business program," the receipt clarifies: reported to whom? (Answer: to the U.S. Department of Education's Integrated Postsecondary Education Data System (IPEDS)). That specificity is what converts vague passive voice into trustworthy reporting.

### Problem Statement

The Set Your Course spec (at time of its 2026-04-19 late-session voice-rule revision) replaced jargon like "CIP 52.02" and "crosswalk quirk" with friendlier phrasing like "IU files Marketing under its Business program." Better — but the founder immediately flagged: *"filed with whom?"* The passive-voice fix left the *authority* unnamed. Students and parents reading "filed under Business" might reasonably ask: *who's filing it, and why should I trust that?*

There is no trust in unsourced data. The product either names its sources or looks like an invented product.

### Success Criteria

**v0.5 hackathon slice (REQUIRED — ships alongside `feature-set-your-course.md`):**

- [ ] Acronym spell-out rule: on the first reference per rendered view, any acronym is written as `Full Name (ACRONYM)`. Subsequent references within the same view may use the acronym alone. Example: first mention `Bureau of Labor Statistics (BLS)`, later references `BLS`. Rule is explicit in every Gemma system prompt that can produce student-facing prose.
- [ ] **Taxonomy codes remain forbidden** per `feature-set-your-course.md` §2 Decision #12. The acronym rule applies to **sources** (BLS, IPEDS, O*NET, BEA) — NOT to taxonomy codes (CIP, SOC, crosswalk) which never surface to students at all.
- [ ] Canonical source-name registry at `backend/app/services/receipts.py::CANONICAL_SOURCES` — single source of truth for "Bureau of Labor Statistics (BLS)", "Integrated Postsecondary Education Data System (IPEDS)", "Occupational Information Network (O*NET)", "College Scorecard", "Bureau of Economic Analysis (BEA)", "Karpathy AI Exposure Index," "Anthropic Economic Index." Each entry has `full_name`, `acronym`, `year_available` (for vintage), `authority_url`, `short_description`.
- [ ] Gemma chip-routing prompt (and any other Gemma prompt emitting student-facing prose) MUST cite the source(s) underlying its claims using the acronym-spell-out rule. Prompt includes the current vintage + canonical names so Gemma doesn't invent them.
- [ ] Structured tails in Gemma responses carry a `sources: list[SourceRef]` field. Frontend renders this as a subtle card-footer attribution line.
- [ ] Career preview card in Set Your Course carries a card-footer: *"Data from Bureau of Labor Statistics (BLS) · College Scorecard 2023 · Occupational Information Network (O*NET)"* — sources named per what was actually consulted for the rendered careers.
- [ ] School Discovery v0.5 stub card carries the same footer treatment.
- [ ] The phrasing issue that triggered this spec is fixed: instead of *"IU files Marketing coursework under its Business program"* (mysterious passive voice), the copy reads *"In Indiana University's submission to the Integrated Postsecondary Education Data System (IPEDS), Marketing is offered within its Business program, not as a standalone degree."* — or equivalent, copywriter-polished.
- [ ] Full test suite passes. No frontend regression. Ruff + mypy clean.

**Post-hackathon full scope (BACKLOG):**

- [ ] Per-stat hover tooltips. Hover the median earnings number → "Source: College Scorecard, 2023 cohort."
- [ ] Vintage displayed on every number where applicable (not just the first-reference citation).
- [ ] Dedicated "Our Sources" page at `/sources` listing the full catalog with authority links and plain-English descriptions of what each dataset tracks.
- [ ] Parent-facing "How we know this" explainer — one-screen walkthrough of the pipeline ("You pick a school + major → we match to the federal program taxonomy → we pull outcomes from BLS and College Scorecard → Gemma reasons; nothing is invented").
- [ ] Full build response (`POST /build`) carries `sources_used` per stat so the reveal screen can cite sources on pentagon stats + boss cards.
- [ ] Citation discipline in every Gemma prompt site (boss narration, guidance, skill recs, etc.), not just the chip-routing prompt.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | **Acronyms spelled out with parenthetical on first reference per view; acronym-only after.** Example: "Bureau of Labor Statistics (BLS)" first mention, "BLS" after. | (a) Standard journalism / reporting style students and parents already know. (b) Respects "data-honest" voice — no assumed jargon knowledge. (c) First-reference-per-view (not per-session or per-app) is the right granularity: students may land on any screen cold and need the full name to re-anchor. Overusing the full name everywhere gets ponderous; hiding it entirely loses meaning. | (a) Always-full-name — rejected, reads as government-document stiff. (b) Always-acronym-with-tooltip — rejected, students can't hover on mobile and shouldn't have to. (c) Spell out once per entire app session — rejected, "first reference" is a view-level concept, not a session-level one; students bounce between surfaces. |
| 2 | **Taxonomy codes (CIP, SOC, "crosswalk") are forbidden outright per `feature-set-your-course.md` §2 Decision #12. The acronym rule here applies to SOURCES, not taxonomies.** | (a) Taxonomies are internal scaffolding that has no meaning to the student; spelling out "Classification of Instructional Programs (CIP)" would be worse than omitting it. (b) Sources ARE meaningful — students benefit from knowing the federal authority. Different treatment for different concepts. | Conflating the two rules — rejected, would either leak taxonomy codes (bad) or hide source attribution (also bad). |
| 3 | **Inline Gemma citation over tooltip-on-hover** for prose-bearing surfaces (chip debug trace, guidance, boss narration when that spec lands). | (a) Streaming surfaces can't rely on hover (desktop only, not mobile; breaks the streaming reading flow). (b) Inline citations read like well-cited writing — students see the source as they read the claim, not as a separate action. (c) Tooltips still make sense for structured number displays (median earnings card hover) — NOT for prose. | Tooltip-only — rejected, hides the receipt from mobile students. Footnote-style numbers with a key at the bottom — rejected, clinical and mobile-unfriendly. |
| 4 | **Canonical source-name registry in `backend/app/services/receipts.py`** — single Python source of truth for how every source is referenced. | (a) Consistency across Gemma prompts, frontend components, and the "Our Sources" page. One string changes, everything updates. (b) Prompts can interpolate `CANONICAL_SOURCES["bls"].full_name_first_ref` so Gemma never gets to invent slightly different wordings ("Bureau of Labor and Statistics", "Labor Bureau Statistics," etc.). (c) Tests lint against this registry — no string literals of source names allowed anywhere else in the code. | (a) String literals scattered through the codebase — rejected, guaranteed drift. (b) Frontend-only registry — rejected, Gemma prompts need the same strings. |
| 5 | **Vintage (year) shown for earnings / debt / completion data where applicable.** "College Scorecard 2023" not just "College Scorecard." | (a) Data freshness matters — a student in 2026 seeing "College Scorecard 2020" data is a valid signal (and a to-do for the pipeline). (b) Vintage is what separates "sourced" from "annotated" — a date commits the data to a point in time. (c) Post-hackathon: every stat carries vintage. Hackathon: the card footer carries the latest vintage across its sources. | Always hiding vintage — rejected, obscures freshness. Showing vintage inline in every sentence — rejected, gets noisy. |
| 6 | **Never an "Our Sources" page in v0.5.** Ship card footer + inline Gemma citation only. | (a) Scope — the "Our Sources" page is a full-screen deliverable with copy, routing, data curation, and design. Doesn't fit in the hackathon window. (b) Inline citations are the *actual* surface students read; the page is the appendix. Ship the surface. (c) Post-hackathon has the runway to do the page right (parent view, authority links, vintage per dataset, etc.) | Ship a minimal "Our Sources" page in v0.5 — rejected, either rushed (bad) or time-diluting (worse). |
| 7 | **Sources attributed at the level of WHAT WAS CONSULTED FOR THE RENDERED DATA.** A card showing 5 careers and median earnings attributes BLS + College Scorecard. A career card for a single SOC attributes only the sources that touched that career. | (a) Honest — we don't say "sourced from O*NET" when no O*NET field was used. (b) Prevents over-citing (every card showing 20 sources because we *could* have used them). (c) Engineering cost: each structured response includes `sources_actually_used: list[SourceId]`; frontend resolves to canonical names. | Blanket attribution on every screen — rejected, dilutes the signal and invites skepticism ("did they actually use O*NET for this?"). |
| 8 | **Citation copy is part of `@fp-copywriter`'s scope, not a developer's.** The spec provides anchors; the copywriter writes the polished strings. | (a) Tone discipline — "According to the Bureau of Labor Statistics (BLS), this career's median pay is…" vs "Source: BLS" are different registers. Picking the right one per surface needs a copywriter. (b) Voice guide compliance is easier to enforce with copywriter ownership. | Developer-written citation copy — rejected, will drift into either legalese or marketing-speak. |

### Constraints

- `backend/app/services/receipts.py` — new module, one file, no external dependencies.
- Gemma prompts that currently don't cite (most of them) get a small prompt addition requiring acronym-spell-out + sources. No prompt refactor.
- Response schemas across `POST /intent/stream`, `POST /intent/chip`, `GET /schools/top-for-cip`, and (post-hackathon) `POST /build` gain a `sources: list[SourceRef]` or similar field. Additive; no breaking changes.
- Frontend: new shared component `<SourceAttribution>` (small footer treatment). Post-hackathon: `<SourceTooltip>` for hover.
- Tokens: reuse `DESIGN.md`. No new tokens. `text-text-muted` + `font-body text-xs` carries the footer attribution.
- Voice: cool, confident, data-honest, never hype. Citations are factual; don't editorialize (no "trusted" or "official" modifiers).
- No external HTTP. All source metadata is static.

### Out of Scope

- **Dataset licensing / legal.** Public federal datasets; no licensing burden. If a proprietary dataset is ever added, that gets its own spec.
- **Auto-generated source confidence ratings.** Not the product's job to rank datasets; cite them and let the reader judge.
- **Inline fact-checking of Gemma output against sources.** That's the domain of `feature-chat-guardrails.md` §2 hallucination defense.
- **Authority verification** (clicking a source opens the authority's homepage). Post-hackathon; hackathon stays text-only.
- **Vintage on every number inline** (e.g. "median earnings $58k [College Scorecard 2023]" on every row). Noisy. Post-hackathon uses tooltips for per-number vintage.

---

## §3 UI/UX Design (sketch)

**Full visionary round PENDING** when this is promoted past v0.5. Sketch:

- **Inline Gemma prose citation** — sources named within the sentences Gemma produces. Example: *"According to Indiana University's submission to the Integrated Postsecondary Education Data System (IPEDS), Marketing is offered within its Business program. The Bureau of Labor Statistics (BLS) tracks graduate placements in marketing-related careers — here's what they show."*
- **Card footer attribution** — at the bottom of each career preview card (and School Discovery result card): a single line `font-body text-xs text-text-muted` reading *"Data from Bureau of Labor Statistics (BLS) · College Scorecard 2023 · Occupational Information Network (O*NET)"* — sources listed deduplicated, separated by `·`.
- **Post-hackathon:** per-stat hover tooltips, "Our Sources" page with authority links + plain-English dataset descriptions, parent-view explainer screen.

---

## §4 Technical Specification

### Architecture Overview

**New backend service (`backend/app/services/receipts.py`):**

- `CANONICAL_SOURCES: dict[SourceId, SourceRef]` — the registry.
- `first_reference(source_id: SourceId) -> str` — returns "Bureau of Labor Statistics (BLS)" on first call per render (view-level caching is the frontend's job; backend always returns the full-name-first form for prompt interpolation).
- `for_prompt_context(source_ids: list[SourceId]) -> str` — produces a block interpolated into Gemma prompts:
  ```
  # Sources available to you for citation
  - Bureau of Labor Statistics (BLS) — occupational outlook, median pay, projections
  - Integrated Postsecondary Education Data System (IPEDS) — school-reported programs, completions
  - ...
  ```

**Response schema additions:**

```python
class SourceId(StrEnum):
    BLS = "bls"
    IPEDS = "ipeds"
    ONET = "onet"
    COLLEGE_SCORECARD = "college_scorecard"
    BEA = "bea"
    KARPATHY_AI_EXPOSURE = "karpathy_ai_exposure"
    ANTHROPIC_ECONOMIC_INDEX = "anthropic_economic_index"

class SourceRef(BaseModel):
    source_id: SourceId
    full_name: str                     # "Bureau of Labor Statistics"
    acronym: str | None                # "BLS" (None for College Scorecard)
    year_available: int | None         # 2023 for most; None where not applicable
    authority_url: str                 # "https://www.bls.gov/ooh/" etc.
    short_description: str             # "occupational outlook, median pay, projections"

# Extension on every prose-bearing response:
class ChipResponse(BaseModel):
    ...existing fields...
    sources_used: list[SourceId]       # actually consulted to produce this response
```

**Frontend component:**

```tsx
// frontend/src/components/SourceAttribution.tsx
export function SourceAttribution({ sourceIds }: { sourceIds: SourceId[] }) {
  // Resolves source_ids to canonical names, dedupes, renders as
  //   "Data from Bureau of Labor Statistics (BLS) · College Scorecard 2023 · …"
  // First reference per render uses full name + paren acronym; collapsing
  // happens when the same component instance renders multiple sources
  // (e.g. card + its children).
}
```

**Gemma prompt amendment (applied to chip-routing prompt in `feature-set-your-course.md`; template for future prompt sites):**

```
# Source citation rule
When your response makes a factual claim drawn from the data, cite the
source using its full name followed by the acronym in parentheses on
first mention (e.g. "Bureau of Labor Statistics (BLS)"). After the first
mention, the acronym alone is fine. This rule applies to data sources
(BLS, IPEDS, O*NET, BEA, College Scorecard, and others). It does NOT
apply to internal taxonomy codes (CIP, SOC, crosswalk) — those are
forbidden entirely in student-facing output per §2 Decision #12.

Available sources for citation:
{sources_for_prompt_context}

Do not invent sources. If you don't know which source supplied a claim,
don't cite one — or phrase the claim in a way that doesn't need a
specific source attribution.
```

### File Changes (v0.5 hackathon slice)

| File | Action | Description |
|------|--------|-------------|
| `backend/app/services/receipts.py` | Create | `CANONICAL_SOURCES` registry + helpers. |
| `backend/tests/services/test_receipts.py` | Create | Canonical-name discipline tests. |
| `backend/app/models/api.py` | Modify | Add `SourceId`, `SourceRef`; extend `ChipResponse` + `TopSchoolsResponse` with `sources_used`. |
| `backend/app/services/set_your_course.py` | Modify | Chip-routing prompt gets the citation rule + `{sources_for_prompt_context}` block interpolated. Response populates `sources_used`. |
| `backend/app/services/school_discovery.py` | Modify | Response populates `sources_used` (IPEDS + College Scorecard + BLS for the ranking). |
| `frontend/src/components/SourceAttribution.tsx` | Create | Footer attribution component. |
| `frontend/src/components/SourceAttribution.test.tsx` | Create | Component tests (full-name-first render, dedup, empty state). |
| `frontend/src/screens/SetYourCourseScreen.tsx` | Modify | Render `<SourceAttribution>` beneath the career preview card. |
| `frontend/src/screens/SchoolDiscoveryStubScreen.tsx` | Modify | Same treatment on each school card. |
| `frontend/src/api/*.ts` | Modify | Types updated for new `sources_used` field. |

### Testing Impact Analysis

**To be expanded when promoted past v0.5.** Initial sketch of P0 tests:

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `test_receipts.py` | `test_canonical_name_first_ref_has_acronym` | `first_reference("bls")` returns "Bureau of Labor Statistics (BLS)". |
| P0 | `test_receipts.py` | `test_canonical_name_college_scorecard_has_no_acronym` | "College Scorecard" returns as-is — no parenthetical. |
| P0 | `test_receipts.py` | `test_no_stringly_named_sources_outside_registry` | Grep-style lint: no string literal of a source name anywhere in the codebase except `receipts.py`. (Test is a static audit; acceptable to mark `skipif` in CI if too brittle.) |
| P0 | `test_set_your_course.py` | `test_chip_response_includes_sources_used` | Mocked Gemma returns a response; `ChipResponse.sources_used` is a non-empty list of valid `SourceId` values. |
| P0 | `SourceAttribution.test.tsx` | `test_renders_full_name_and_acronym` | Given `["bls"]`, renders "Bureau of Labor Statistics (BLS)" exactly. |
| P0 | `SourceAttribution.test.tsx` | `test_multi_source_deduplicated_and_separated` | Given `["bls", "college_scorecard", "bls"]`, renders 2 unique entries separated by `·`. |
| P0 | `SourceAttribution.test.tsx` | `test_empty_source_list_renders_nothing` | Given `[]`, component is absent — no empty footer. |
| P1 | `SetYourCourseScreen.test.tsx` | `test_footer_attribution_visible_when_resolved` | Resolved state shows the source attribution footer. |

---

## §5 Architecture Review

**Status:** PENDING (spec in backlog)

---

## §6 Implementation Log

**Status:** PENDING

---

## §7 Test Coverage

**Status:** PENDING

---

## §8 Reviews

**Status:** PENDING

---

## §9 Verification

**Status:** PENDING

---

## §10 Discussion

```
[2026-04-19] Drafted after founder observation: the session's voice-rule fix
("don't show CIP/SOC/crosswalk to students") replaced jargon with friendlier
phrases but left passive-voice mysteries like "IU files Marketing under its
Business program" — "filed with whom?" became the exact question the fix
was supposed to prevent.

The fix isn't better adjectives; it's NAMING the authority. In this case:
the Integrated Postsecondary Education Data System (IPEDS) — the Department
of Education's federal school-reporting system. "IU's submission to IPEDS"
is specific; "IU's filing" is vague.

Broader reframe: data provenance becomes a first-class product surface.
Every factual claim carries a visible receipt. The product is the opposite
of a black-box LLM tool — it reads public federal data and reasons with
Gemma; every number has a source. Cite them.

Founder-added rule during the same exchange: "any acronyms must spell out
the whole thing and then include the acronym in (). Bureau of Labor
Statistics (BLS)." Applied as §2 Decision #1 — first reference per view
uses full name + paren acronym; subsequent references may use acronym
alone.

Scope: v0.5 (hackathon) ships inline Gemma citations + card footer
attribution + the canonical source registry + the acronym rule in prompts.
Post-hackathon: "Our Sources" page, per-stat hover tooltips, parent-view
explainer.

Open questions when promoted:
- Should the "Our Sources" page include last-updated dates per dataset?
- Parent-view explainer — standalone route, or an always-visible info
  button in the global header? @fp-design-visionary picks.
- How does the receipts rule interact with the meme-redirect easter egg
  (docs/specs/feature-chat-guardrails.md §3)? Probably: meme redirects
  don't cite sources (they're jokes, not data claims). Confirm when
  promoting.
```

---

## §11 Final Notes

**Human Review:** PENDING — spec is in the v0.5 / BACKLOG split. Promotion to full DRAFT requires a human review of §1–§4 and resolution of the open questions in §10.
