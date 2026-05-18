# Bugfix Bundle: Post-100-Build-Test Fixes

## Claude Code Prompt

```
Read the spec at docs/specs/bugfix-post-100-build-test-fixes-bundle.md in its entirety.

This spec bundles six independent fix surfaces discovered by the 2026-05-17
real-Playwright 100-build E2E run. The diagnostic evidence lives in
reports/chrome-agent-real-2026-05-17/{TRIAGE.md, SYNTHESIS.md, results.json,
screenshots/}. Read TRIAGE.md first — it has the verdicts and the diagnoses.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (six bundle designs: template-leak
     gate, insufficient-data banner, school search overhaul, narrowing_hint surface +
     HTML pre-filter, postgrad-intent extension, backend cleanup). Focus on whether
     the six bundles can coexist cleanly in one spec without coupling, and whether
     any bundle should split out.
   - The Gemma-prompt edits (Bundles 1, 4d, 5) touch the resolver hot path. The
     architect should explicitly call out fallback behavior + ensure logs/gemma.jsonl
     still captures every call site under both INFERENCE_BACKEND values.
   - @fp-data-reviewer NOT required (no Iceberg schema changes; no stat formula
     changes; one new YAML data file in data/reference/ is a static lookup).
   - Findings → §5. APPROVED → proceed; CHANGES REQUESTED → STOP, alert human;
     REJECTED → STOP, alert human.

2. DESIGN VISION
   - Invoke @fp-design-visionary for Bundle 2 (InsufficientDataBanner). Reuse the
     existing GradCredentialNotice tile pattern at
     frontend/src/components/school/GradCredentialNotice.tsx as the reference —
     same Brightpath surface/border/icon idiom. Banner sits above the Pentagon
     section in BuildResultsScreen.
   - The visionary writes the ASCII mockup, copy direction, and design-token usage
     to §3. Copy must follow the memory-encoded rules:
     • feedback_no_substitution_caveat (no "Limited data" language)
     • feedback_pdf_no_game_language (advisory, not game framing)
   - Other UI changes (Bundle 4 — narrowing_hint render, soft-nudge extension) are
     small lift-and-shift edits and don't need a full vision pass; visionary just
     calls out the placement.

3. IMPLEMENTATION
   - Implement bundles in this order to minimize merge conflicts:
     a. Bundle 6 (backend cleanup) — trivial, lands the API max_length first.
     b. Bundle 1 (template-leak gate) — adds the rejection at the boundary.
     c. Bundle 5 (postgrad-intent extension) — prompt edits in same file as #1.
     d. Bundle 3 (school search overhaul) — independent backend module.
     e. Bundle 4 (narrowing_hint + HTML pre-filter) — frontend + small backend.
     f. Bundle 2 (insufficient-data banner) — frontend-only, depends on no others.
   - BEFORE coding each bundle: read its Testing Impact Analysis subsection in §4.
   - DURING coding: update tests listed in "Authorized Test Modifications".
   - CRITICAL: if any test NOT in "Authorized" fails, STOP and escalate via §10.
   - Log work to §6 after each bundle.
   - BUILD ACCOUNTABILITY: if build breaks, YOU fix it (max 3 attempts per bundle).
     After 3 attempts, escalate via §10 and set status BLOCKED.

4. TESTING
   - Invoke @test-writer to review §4 Testing Impact Analysis across all six bundles.
   - Implement all P0 tests for every bundle before P1. Bundles 1 and 4 must have
     the placeholder-rejection regression tests landed in this step.
   - Run pytest backend/tests/services/test_set_your_course.py first — this suite
     has ~8 fixtures using the literal "XX.XXXX" placeholder that must be rewritten
     per Bundle 1's Authorized Modifications.
   - Then run full backend pytest + frontend vitest. Catch regressions across the
     whole suite, not just the touched files.

5. DESIGN AUDIT
   - Invoke @fp-design-auditor for InsufficientDataBanner (Bundle 2) only.
   - Mechanical check: does the banner use Brightpath tokens (bg-bp-mid,
     border-border-subtle, text-accent-caution, font-body, font-display) and
     reuse the GradCredentialNotice tile structure?
   - Other UI changes are small enough to skip the auditor.

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review the bundle. Focus areas:
     • Template-leak gate (Bundle 1): is the rejection path bulletproof? Any
       residual path where matched_title="Program Title" leaks?
     • School search (Bundle 3): is token-overlap a perf hit on the 6800-row
       institution scan? Confirm latency stays within budget.
     • HTML pre-filter (Bundle 4d): is the regex strict enough? Any way for a
       sanitized payload to slip through to Gemma?
     • Postgrad-intent (Bundle 5): does soc_expansion's candidate pool actually
       contain every target SOC, or do we still drop pharmacy/SLP/PT?
   - Findings → §8. APPROVED → proceed; CHANGES REQUIRED → §10 routing;
     BLOCKER → STOP.

7. VERIFICATION
   - Invoke @fp-builder for the full sweep:
     • Backend: ruff check backend/, mypy backend/app/, pytest backend/tests/
     • Frontend: tsc --noEmit, vitest run, vite build
   - Log to §9. All green → proceed to step 8.

8. COMPLETION
   - Update Status to COMPLETE.
   - Tick all Success Criteria checkboxes in §1.
   - Move spec to docs/specs/completed/.
   - Write a summary report to reports/bugfix-post-100-build-test-fixes-bundle-YYYY-MM-DD.md
     with: bundles shipped, LOC by bundle, tests added, regressions caught and fixed.
   - Commit and ask the user before pushing.
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
| DESIGN AUDIT | @fp-design-auditor checking token compliance |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-05-17 |
| Author | Jeff Cernauske + Claude Code |
| Spec Version | 1.0 |
| Last Updated | 2026-05-17 |
| Blocked By | — |
| Related Specs | `bugfix-e4b-cip-soc-destination-filter.md` (predecessor), `bugfix-broad-cip-substitution-and-intent.md` (related resolver context) |

---

## §1 Feature Description

### Overview

Six independent fix bundles, derived from real evidence captured by the 2026-05-17 Playwright 100-build E2E run. Bundled into one spec because each bundle is small (15-200 LOC) and they share testing surface; splitting into six specs would 6× the review overhead under the May 18 hackathon deadline.

### Problem Statement

The 100-build E2E run (`reports/chrome-agent-real-2026-05-17/`) surfaced concrete bugs and UX gaps that a prior LLM-based agent's report had either fabricated, mis-framed, or missed entirely. After triaging 18 findings in `reports/chrome-agent-real-2026-05-17/TRIAGE.md`, six bundles emerged as worth shipping before demo:

1. **Template-leak gate.** The e4b resolver fallback occasionally returns the literal `XX.XXXX` / `"Program Title"` placeholder from its own prompt instead of substituting. The streaming path's safety net blanks `matched_cip` but still leaks `matched_title`. The fallback path has no equivalent gate. Real students typing "Biology" at U Florida and "Aerospace Engineering" at MIT saw `Matched "Biology" to CIP XX.XXXX / Program Title` rendered to the UI, plus the downstream Pydantic 422 message `cipcode must match CIP pattern \d{2}\.\d{2,4}` as raw error text.
2. **Insufficient-data banner.** When College Scorecard suppresses program-level earnings (small cohort, <30 federal-loan-recipient completers), ERN and ROI render as `—` with no explanation. Suppression carries signal — substituting OEWS would launder small-cohort programs into confident-looking numbers. A banner that surfaces the suppression honestly is the right product call. Also catches sparse-IPEDS cases like Cincinnati State / Mortuary Science, where the school's actual program isn't in our ingested data and Gemma's only candidate is a clearly-wrong CIP.
3. **School search overhaul.** Current matching is substring-only OR short-acronym (no space). Sort is alphabetical. Misses 14 colloquial inputs from the test plan (Penn State, UC Berkeley, Cal Poly SLO, Georgia Tech, UNC Chapel Hill, UT San Antonio, Cal State Long Beach, West Point, UC Davis, Florida A&M, SUNY Cobleskill, Le Cordon Bleu, Purdue [typo "Univeristy"], and HBCU short-forms). Ranks branch campuses above main (Ohio State Lima > Main; Bowling Green Firelands > Main; Baptist University of Florida > University of Florida).
4. **Surface Gemma's existing ambiguity signals.** Backend already returns `narrowing_hint`, `confidence`, and `alternatives` on every resolution. Frontend ignores `narrowing_hint` unless alternatives is non-empty — which is never the case on the e4b fallback path. Medium-confidence resolutions ("money" → Mathematics, with a good narrowing_hint about economics/finance) get no nudge. Also: e4b is non-deterministic on HTML-shaped inputs, sometimes confidently misclassifying `<script>alert(1)</script>` as CS. Add a pre-Gemma filter for markup-shaped inputs.
5. **Extend postgrad-intent recognition (split into two groups per A9).** Existing pattern handles "pre-med/doctor/physician, pre-vet/veterinarian, dentist, pre-law/attorney" — when student input matches these, soc_expansion adds postgrad SOCs that land in `#tier-postgrad` (or trigger `GradCredentialNotice` for feeder undergrad programs).
   - **Group A — Genuine advanced-degree intents** (add to the existing "prefer SOCs requiring doctoral/professional degree" rule): Pharmacy → Pharmacists (PharmD, doctoral), Speech-Language Pathology → SLPs (master's, professional), Physical Therapy / Kinesiology → PTs (DPT, doctoral).
   - **Group B — Non-advanced-degree credentials worth recognizing as intents but NOT routing to doctoral preference**: Library Science → Librarians (master's, but a distinct standalone credential — the "advanced degree preference" rule is overkill), Music Therapy → Music Therapists (bachelor's + MT-BC certification), Mortuary Science → Morticians (associate's degree per BLS — instructing Gemma to prefer doctoral SOCs here would be actively wrong). Group B entries land in the resolver's intent-keyword synonym map and soc_expansion's candidate pool, but do NOT extend the advanced-degree-preference clause.
   Each entry in both groups needs intent_keyword patterns + confirmation that soc_expansion's candidate pool exposes the target SOC.
6. **Backend cleanup bundle.** Two small low-risk fixes: (a) `prefetch._compute_career` (prefetch.py:91-107) already catches `Exception` and logs at WARNING when `stat_engine.compute_one` raises `LookupError` for a (unitid, cipcode, soc) triple that isn't in gold. The build still works (caller treats prefetch as best-effort), so the noise is log-spam not a real fault. Fix: catch `LookupError` separately *before* the generic `Exception` clause, log at INFO with structured `extra` context. (b) Four `major_text: str` fields in `backend/app/models/api.py` have no `max_length` bound; one path (`AskCareerPickRequest`) already has `max_length=200`. Inconsistent. Add the bound everywhere + a `maxLength={200}` on the SetYourCourseScreen major input.

### Success Criteria

- [ ] Resolver no longer surfaces `XX.XXXX`, `"Program Title"`, or `"N/A"` in `matched_cip` or `matched_title` on any code path; both the fallback and streaming paths gate the rejection. Regression test asserts every path.
- [ ] BuildResultsScreen renders an `InsufficientDataBanner` above the Pentagon section when the selected career has `career.stats.ern == null && career.stats.roi == null` (using the `stats` object on `CareerOutcome`, NOT the top-level `stat_ern` / `stat_roi` fields which belong to the unrelated `SchoolForCareerRow` leaderboard type). Banner reuses Brightpath tokens and the GradCredentialNotice tile structure. Copy is advisory, not game framing.
- [ ] School search returns Penn State, UC Berkeley, UC Davis, Cal Poly SLO, Georgia Tech, UNC Chapel Hill, UT San Antonio, Cal State Long Beach, West Point, Florida A&M, SUNY Cobleskill, and "Purdue Univeristy" (typo) as the first or one of the first 3 results. Main campuses rank above branches. Test with all 14 inputs from the run.
- [ ] When `narrowing_hint` is non-empty and `alternatives` is empty, the hint is rendered as advisory copy under the matched-title on SetYourCourseScreen. Soft-nudge UI extends to `confidence === "medium"`.
- [ ] HTML-shaped inputs (regex `/<[a-z]+[\s>]|<\/[a-z]+>|<script/i`) short-circuit to a soft-nudge "that looks like code, try a real major name" without calling Gemma. The XSS payload from the test plan no longer hits Gemma.
- [ ] Resolver intent_keywords pattern recognizes new terms in two groups: **(Group A — advanced-degree intents)** pharmacist, pre-pharm, slp, speech pathologist, physical therapist, pre-pt, dpt; **(Group B — recognized intent but not advanced-degree preference)** librarian, mlis, music therapist, mt-bc, mortician, funeral director. Group A extends the "prefer doctoral/professional SOC" rule; Group B doesn't. soc_expansion candidate pool surfaces each target SOC for the matching intent.
- [ ] `prefetch.compute_one` LookupError is caught at the prefetch boundary and logged at INFO (not ERROR / WARNING). Build stream still functions when prefetch returns nothing.
- [ ] All four unbounded `major_text` fields in `backend/app/models/api.py` have `Field(min_length=1, max_length=200)`. Frontend major input has `maxLength={200}` attribute.
- [ ] Full backend + frontend test suite passes. No regressions in existing tests. New P0 tests for each bundle land green.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | One spec bundling six fixes rather than six specs | Hackathon deadline tomorrow. All six are diagnosed and have nailed-down fix surfaces in TRIAGE.md. Six independent specs would 6× the agent-pipeline review overhead. Bundles are independent enough that they can be reverted individually if a regression appears. | Six separate specs (cleaner blast-radius isolation but blows the timeline). Two specs split by frontend/backend (still doubles overhead). |
| 2 | Banner instead of OEWS substitution for suppressed earnings | College Scorecard suppression carries real signal: cohort too small, few federal-loan recipients, brand-new program. Substituting OEWS occupation-level wage would launder that signal into a confident number. The product is honest-by-default. | OEWS substitution (rejected: launders meaningful absence). Show "Not published" instead of "—" with no banner (smaller fix but loses the explanation). |
| 3 | Trigger banner on `career.stats.ern == null && career.stats.roi == null` rather than `small_cohort_flag` | `small_cohort_flag` is the upstream root-cause signal in `consumable_career_outcomes` but is NOT propagated to `consumable_program_career_paths` (the table the build endpoint reads). Propagating it would be an Iceberg schema change → triggers Brightsmith spec gate. The downstream null-pair effect on `career.stats.ern` and `career.stats.roi` catches the same cases because of the null-propagation chain in `college_scorecard_career_outcomes.py:267-281` and the gold-zone `compute_stat_ern` / `compute_stat_roi_from_multiplier` returning `None` (`futureproof_engine.py:86, 159`). Note: these are the `stats: PentagonStats` fields on `CareerOutcome` (`frontend/src/types/build.ts:6-12, 92`), not the unrelated `stat_ern` / `stat_roi` top-level columns on `SchoolForCareerRow`. | Schema change to propagate `small_cohort_flag` (cleaner trigger semantically, but adds a separate schema spec out of scope here). Trigger on `roi_cost_basis == 'none'` (intermediate signal, less direct than the null-pair). Use `selectedCareer.stat_ern` top-level (rejected — that field doesn't exist on the in-build `CareerOutcome` type). |
| 4 | Curated school aliases YAML rather than alias table in DuckDB | Aliases are a small fixed lookup (~20 entries for the demo); YAML keeps them out of the data pipeline and avoids a schema change. Edited by humans, reviewed in PR. | Add to `consumable_school_lookup` or similar (overkill for 20 entries). Add to the IPEDS ingestion (changes source-of-truth — wrong layer). |
| 5 | Token-overlap requires ALL tokens to match, not ANY | "State University" as the query shouldn't match every state school in the country; requiring all query tokens prevents over-matching. Single-token queries fall back to the existing substring + acronym paths. | ANY-token match (over-matches dramatically). Weighted token rarity (more complex; not needed at this scale). |
| 6 | HTML pre-filter is a regex in the resolver, not a Pydantic validator | Pre-filter needs to short-circuit to a friendly UX response, not reject with 422. A Pydantic validator would return an error message — the existing 422 UX is what we're trying to avoid. The regex lives at the top of `_fallback_resolve` and the streaming path, before any Gemma call. | Pydantic validator (rejected: produces 422). Frontend-only filter (rejected: defense in depth at API boundary too). |
| 7 | Banner is one component used in one place (BuildResultsScreen), not reused on SetYourCourseScreen | Suppression signal is a property of the *selected career* + school. Show it after the student commits, not before — premature surfacing on every career card during browsing would be visual noise. Could extend later if real users say they need it before commit. | Show on SetYourCourseScreen career cards (rejected: noisy on a list of 13 careers). Show in both places (rejected: scope creep). |
| 8 | Postgrad-intent recognition is just an additive prompt + soc_expansion candidate pool edit; no new architecture | Existing infrastructure already does the right thing for pre-med/pre-law/pre-vet. New professions just need entries. No new components, no new endpoints. | Build a generic "credential ladder" feature with explicit mapping table (massive scope creep). Hardcode each new path as a special case (anti-pattern). |

### Constraints

- May 18, 2026 hackathon deadline. Spec ships and verifies tonight or doesn't ship.
- All evidence is in `reports/chrome-agent-real-2026-05-17/`. No new investigation needed before implementation; all diagnoses are done.
- Gemma e4b is the demo runtime — every fix must work under e4b's actual behavior, not idealized model behavior.
- Both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter` must keep working.
- `logs/gemma.jsonl` must continue to capture every Gemma call, including pre-filter short-circuits (log the short-circuit as a separate call_site so we can audit).

### Out of Scope

| Item | Reason | Disposition |
|------|--------|-------------|
| Schema change to propagate `small_cohort_flag` to `consumable.program_career_paths` | Triggers Brightsmith schema-change spec gate; pure-frontend trigger is good enough | Future spec if we need the semantic precision |
| OEWS / wage substitution for suppressed program earnings | Explicit product decision: suppression is signal, no substitution | Will not ship |
| Levenshtein / fuzzy typo correction on school search | Likely covered by Bundle 3's token-overlap (matches "purdue" token); defer until we see post-#3 evidence of remaining typo misses | Defer to follow-up if needed |
| "Accountancy" / word-form stemming in `_candidate_score` | Real users almost certainly type "Accounting"; the variant is a test-plan artifact | Defer indefinitely |
| Accreditation warning for for-profit schools | We don't ingest accreditation data, and the product is outcome-focused | Out of scope (no data, no editorial framing) |
| React duplicate-key warnings | Not reproducible on fresh dev server across 8+ builds including high-cardinality 43-card case; likely Vite HMR artifact | Closed |
| Dev-server crash + endpoint flakiness | Environmental (concurrent local Ollama tests starved resources); production deploys auto-restart | Closed |
| Refactor `_candidate_score` / `_intent_match_tokens` to use Porter stemmer | Out-of-scope cleanup; not needed for the demo | Future spec |
| English / Writers crosswalk gap | Per BLS CIP-SOC crosswalk: `23.01* English-General` does not map to `27-3043 Writers`; this is correct, not a bug | No action |

---

## §3 UI/UX Design

> **Vision (Bundle 2):** The emotional target is **trusted candor.** A student picks Howard / Architecture or Cincinnati State / Mortuary Science, the pentagon renders, two points are blank, and without explanation it reads as a glitch. With the wrong explanation ("Limited data") it reads as the product apologizing for itself. The banner needs to do something quieter and harder: tell the student that the absence is *meaningful* — the federal government suppressed earnings because the cohort is small enough that publishing would identify individuals — and that the rest of their build is still real. They should think "huh, that's actually useful to know," not "oh no, the app broke." This is a sibling to `GradCredentialNotice`, not a new pattern. Same surface, same left-stripe accent (caution amber), same icon idiom, same fade-in. The student should recognize it before they read it.

### Mockups

#### Bundle 2 — InsufficientDataBanner (desktop, rendered state)

Banner sits in the column gutter between Section 2 (Boss results) and Section 3 (Pentagon). Same horizontal inset as the Pentagon card below it — they read as a stacked pair.

```
                                                          (BuildResultsScreen, desktop, ≥1024px)

  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │                                                                                  │
  │   Section 2 — Boss results (unchanged)                                           │
  │   ...                                                                            │
  │                                                                                  │
  └──────────────────────────────────────────────────────────────────────────────────┘

                                                          ↓ 24px gap (Section spacing)

  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │▌                                                                                 │  ← 3px left stripe, accent-caution
  │▌  ⓘ   Earnings data isn't published for this program                            │     border-l-[3px] border-l-accent-caution
  │▌                                                                                 │
  │▌      The Department of Education doesn't release wage data for                  │
  │▌      Architecture at Howard University — the graduating cohort is               │
  │▌      small enough that publishing it could identify individual                  │
  │▌      students. The rest of your build still reflects real outcomes              │
  │▌      for this field.                                                            │
  │▌                                                                                 │
  └──────────────────────────────────────────────────────────────────────────────────┘
   ↑                                                                                 ↑
   bg-bp-mid/60                                                                      rounded-xl, shadow-md
   border-border-subtle                                                              p-5 (tablet+), p-4 (mobile)

                                                          ↓ 24px gap

  ┌──────────────────────────────────────────────────────────────────────────────────┐
  │                                                                                  │
  │   Section 3 — Pentagon + Legend (unchanged structurally; ERN and ROI             │
  │                                  points render dimmed with "—" labels)           │
  │                                                                                  │
  │              ┌─────────────────┐                                                 │
  │              │      ⟨GRW⟩      │                                                 │
  │              │   ╱       ╲     │                                                 │
  │              │ ⟨—⟩       ⟨RES⟩│   ← ERN point: dimmed, no value plotted          │
  │              │  ╲         ╱    │                                                 │
  │              │   ⟨—⟩  ⟨AURA⟩  │   ← ROI point: dimmed, no value plotted          │
  │              └─────────────────┘                                                 │
  │                                                                                  │
  └──────────────────────────────────────────────────────────────────────────────────┘
```

**Anatomy:**

```
  ┌──────────────────────────────────────────────────────────────┐
  │ A  B    C ─────────────────────────────────────────────────  │
  │           D ───────────────────────────────────────────────  │
  │           D ───────────────────────────────────────────────  │
  │           D ───────────────────────────────────────────────  │
  └──────────────────────────────────────────────────────────────┘
   ↑  ↑    ↑
   A  B    C/D
   ┃  ┃    ┗━━ Title (C) on row 1; Body (D) starts row 2, indented
   ┃  ┗━━━━━━━ Icon — ⓘ glyph, text-accent-caution, 20px, opacity 0.9
   ┗━━━━━━━━━━ Left stripe — 3px accent-caution band, full container height
```

The icon and title share row 1 (`flex items-start gap-3`); body wraps to a left-aligned column starting at the same x-offset as the title (created by `pl-8` on the body block, equivalent to icon width + gap). This mirrors GradCredentialNotice's reading rhythm exactly — title and body share a left edge, icon hangs in the gutter.

### Interactions

The banner is purely informational — no clicks, no hover states beyond a subtle elevation cue if the parent card supports it. It is not dismissible (suppression is a property of the data, not a notification — there's no state to clear). The icon is decorative (`aria-hidden="true"`); semantics live on the container.

**Copy** (en — primary recommendation):

| Slot | Copy |
|------|------|
| Title | `Earnings data isn't published for this program` |
| Body | `The Department of Education doesn't release wage data for {programTitle} at {schoolName} — the graduating cohort is small enough that publishing it could identify individual students. The rest of your build still reflects real outcomes for this field.` |

Why this title: it's a statement of fact, not an apology or a warning. Subject is "data," not "we." Voice is the same register the rest of the build uses to talk about BLS/IPEDS — confident, sourced, not performative.

Why this body: it names the *source* (Department of Education), the *reason* (cohort size threshold for privacy), and *what's still real* (everything else in the build). Two beats: explanation + reassurance. Mentions the program by name because suppression is per-program — Howard publishes earnings for plenty of majors, just not this one. Concludes with a half-sentence that pre-empts the "is the whole pentagon broken?" panic.

**Alternates** (for fp-copywriter to choose from):

| # | Title | Body |
|---|-------|------|
| Alt 1 | `Earnings figures withheld at the source` | `The Department of Education suppresses wage data when a program's graduating cohort is small enough to identify individual students — that's the case for {programTitle} at {schoolName}. Growth, resilience, and aura still come from program-specific data.` |
| Alt 2 | `No wage data for {programTitle} at {schoolName}` | `Federal reporting suppresses earnings when fewer than ~30 graduates take federal loans in a year, which protects individual privacy. The rest of the pentagon reflects this program directly.` |

Alt 1 is the most clinical — leads with the data fact, names the three stats that *are* real. Alt 2 is the most specific — quantifies the threshold (~30) so a student who wants the mechanism gets it. The primary recommendation lands between them: human enough to read on first pass, sourced enough to trust.

**Copy** (es): `TODO(i18n-es)` — translate primary recommendation. Maintain the two-beat structure (fact + reassurance). Do NOT translate "Department of Education" — keep as proper noun, parenthetical Spanish gloss if needed. Use formal register ("usted" form not necessary; this is the build's neutral voice).

### Brightpath token usage (per element)

Match GradCredentialNotice's pattern exactly. Where the existing component uses one value, use the same one.

| Element | Tokens / Classes |
|---------|------------------|
| **Container** (`<motion.section>`) | `relative rounded-xl bg-bp-mid/60 border border-border-subtle border-l-[3px] border-l-accent-caution p-4 tablet:p-5 shadow-md` |
| **Row 1 wrapper** (icon + title) | `flex items-start gap-3` |
| **Icon** (`<span aria-hidden="true">`) | Inline SVG or ⓘ glyph. `text-accent-caution opacity-90`, sized at `w-5 h-5` (20×20). `shrink-0 mt-0.5` so it baseline-aligns with the title's cap height. |
| **Title** (`<h3>`) | `font-display text-body-lg font-semibold text-text-primary leading-tight` |
| **Body** (`<p>`) | `mt-3 pl-8 font-body text-body text-text-secondary leading-relaxed` |
| **Motion variants** | `springs.smooth` (see Motion section below) |

`pl-8` on the body equals the icon column width (`w-5` + `gap-3` ≈ 32px) so the body's left edge sits flush under the title. This is the same trick GradCredentialNotice uses to keep the eye moving down a single column.

**Why caution amber, not info blue:** the suppression carries decision-relevant signal — the student should pause on it. Caution is the existing Brightpath token for "look at this, but don't panic." Info would read as a footnote; alert/error would read as a failure. Caution is the right register: noted, then move on.

**Why `bg-bp-mid/60`, not `bg-bp-mid`:** the `/60` opacity lets the background gradient breathe through, which makes the banner feel like part of the page rather than a slab pasted on top. Same choice GradCredentialNotice made.

### Motion

Single fade-in from the dim state. The banner is not a hero element — it should appear settled, not announce itself. Slower than a button hover, gentler than a modal entrance. Matches the cadence the Pentagon below it uses to plot points.

```typescript
import { motion, useReducedMotion } from "framer-motion";
import { springs } from "@/styles/motion";

const reducedMotion = useReducedMotion();

<motion.section
  initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 12 }}
  animate={{ opacity: 1, y: 0 }}
  transition={springs.smooth}
  aria-labelledby="insufficient-data-banner-title"
  data-testid="insufficient-data-banner"
  className="relative rounded-xl bg-bp-mid/60 border border-border-subtle border-l-[3px] border-l-accent-caution p-4 tablet:p-5 shadow-md"
>
  ...
</motion.section>
```

`springs.smooth` is the same preset GradCredentialNotice uses for its entrance — keeps these two notice tiles feeling like one family across the app. No exit animation needed; the banner unmounts cleanly when the predicate flips (which, in practice, only happens on career switch, where the whole results column re-renders).

**Reduced motion:** opacity-only fade. No y-translate. Same idiom GradCredentialNotice already establishes.

### Responsive Behavior

The banner is a one-column block in all viewports. No layout shift.

| Breakpoint | Padding | Width | Body indent |
|------------|---------|-------|-------------|
| Mobile (<768px) | `p-4` | Full width of results column gutter (`mx-4` parent inset) | `pl-8` retained — title and body still share a left edge under the icon |
| `tablet:` (≥768px) | `p-5` | Full results column width | `pl-8` retained |
| `desktop:` (≥1024px) | `p-5` | Matches Pentagon card width exactly | `pl-8` retained |

The body copy wraps naturally; at the narrowest viewport (~360px wide) the longest expected program name + school name combination ("Doctor of Audiology — University of Pittsburgh-Pittsburgh Campus") wraps to three lines. Tested against the longest known IPEDS institution name (84 chars). No truncation needed; the body is meant to be read.

### Cozy Quest References

This isn't a hero moment, but it inherits the surrounding world. The banner sits inside the BuildResultsScreen's plush-dark composition — the bear is still visible at the top, the boss results column sits above, the pentagon waits below. The amber stripe ties to the same accent the boss-loss state uses for contemplative outcomes — the visual through-line is "thoughtful pause," not "error." Like the moment in Stardew Valley when the museum tells you a fossil you donated is "of unknown provenance" — the game doesn't apologize, it just states the fact and moves on.

### Bundle 4 — narrowing_hint render placement (lift-and-shift)

`frontend/src/screens/SetYourCourseScreen.tsx` currently renders `current-resolution-summary` (testid) around line 550-600 containing the matched title and (when low confidence) the soft-nudge. Extend this region so that when `currentResolution.narrowing_hint` is non-empty AND `currentResolution.alternatives` is empty (CipPicker doesn't render), an additional advisory line appears below the matched-title:

```
Matched "money" to CIP 24.0101 Liberal Arts and Sciences/Liberal Studies.
ⓘ Consider economics, finance, or business-related fields if 'money' refers to the subject matter.
```

Same `text-text-secondary` color, same `font-body text-small leading-relaxed` font scale as the existing reasoning paragraph. Single inline ⓘ glyph at `text-accent-info opacity-80`, `gap-2` to the text. No new component — inline render block, testid `narrowing-hint-inline`. Placement decision confirmed: directly under the matched-title line, above any existing reasoning text. Reads as a continuation of the resolver's own commentary.

### Bundle 4 — soft-nudge extension to medium confidence (lift-and-shift)

`SetYourCourseScreen.tsx:326`: change `currentResolution?.confidence === "low"` to `=== "low" || === "medium"`. All downstream UI that keys off `lowConfidence` (caution-amber color shifts, softNudge text rendered) extends automatically. Placement confirmed — no additional design needed; the existing soft-nudge surface already lives in the right place and uses the right token register. The extension just widens which confidence values trigger it.

### Accessibility

| Element | data-testid | Role | aria-label / aria-labelledby |
|---------|-------------|------|------------|
| InsufficientDataBanner container (`<motion.section>`) | `insufficient-data-banner` | `note` (implicit via `<section>` with `aria-labelledby`) | `aria-labelledby="insufficient-data-banner-title"` pointing at the `<h3>` |
| InsufficientDataBanner title (`<h3>`) | `insufficient-data-banner-title` | (heading — implicit) | n/a — content is the accessible name |
| InsufficientDataBanner icon (`<span>`) | n/a | n/a | `aria-hidden="true"` (decorative; meaning lives in the title) |
| narrowing_hint advisory line | `narrowing-hint-inline` | (no role; inline text) | n/a |
| HTML pre-filter soft-nudge | `html-input-nudge` | `alert` | "Input looks like code, please try a real major name" |

Use `aria-labelledby` against the title rather than a static `aria-label` so the accessible name reflects the actual rendered copy if the title is ever revised — and so screen readers announce the same words sighted users see, not a paraphrase. The body is read as part of the section's natural content flow; no separate label needed.

---

## §4 Technical Specification

### Architecture Overview

This bundle touches three modules and one new data file:

1. **Resolver core** — `backend/app/services/set_your_course.py` and `backend/app/services/intent.py`. Bundle 1 (template-leak gate) and Bundle 5 (postgrad-intent extension) modify the resolver prompt + post-processor. Bundle 4d (HTML pre-filter) adds a regex short-circuit at the entry points.
2. **School search** — `backend/app/services/school_lookup.py` and `src/mcp_server/futureproof_server.py` (the `_handle_get_school_programs` handler). Bundle 3 adds token-overlap scoring, relevance-ranked sort, and an aliases lookup.
3. **Frontend resolver UI** — `frontend/src/screens/SetYourCourseScreen.tsx` and `frontend/src/screens/BuildResultsScreen.tsx`. Bundles 2 and 4 add the new banner + extend `lowConfidence`.
4. **Backend API models + prefetch** — `backend/app/models/api.py` (Bundle 6b: max_length) and `backend/app/services/prefetch.py` (Bundle 6a: LookupError catch).
5. **New data file** — `data/reference/school_aliases.yaml` (Bundle 3).

No Iceberg schema changes. No new database tables. No new API endpoints. No new top-level frontend routes.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/services/set_your_course.py` | Modify | Bundle 1: add `_is_placeholder_resolution(matched_cip, matched_title) -> bool` helper. Use in `_fallback_resolve` (line ~957) — reject and return `None` when placeholder detected; caller's fallback IntentResult builder takes over. Use in `_build_intent_result_from_tail` at two sites: (a) replace the truthy-or assignments at lines 1097 and 1108 (`matched_title or "Program not offered here"` / `or "Couldn't confirm a program"`) with calls that filter placeholder values before keeping `matched_title` — defense in depth so a future early-return refactor at this branch can't reopen the leak; (b) extend the final regex-failure gate at line ~1121-1134 to also short-circuit on placeholder detection and blank `matched_title` when it's in `_PLACEHOLDER_TITLES`. Bundle 1: in the three prompt templates at lines 213, 288, 672, replace the placeholder example values `"matched_cip": "XX.XXXX"` / `"matched_title": "Program Title"` with concrete fake-but-valid examples `"matched_cip": "13.1001"` / `"matched_title": "Human Resources Management"` (each annotated with `← replace with the actual match`). Bundle 4d: add HTML-shaped-input pre-filter at top of `stream_initial_resolution` and `_fallback_resolve`, short-circuiting to a fixed IntentResult with `confidence="low"`, `matched_cip=""`, `reasoning=t("syc.htmlNudge")`, and emit one observability record via `gemma_client.log_synthetic_event(call_site="set_your_course_html_prefilter", event="short_circuit", extra={...})` so the short-circuit is auditable in `logs/gemma.jsonl` without polluting real-inference latency stats. |
| `backend/app/services/intent.py` | Modify | Bundle 1: prompt template at line ~146 — same placeholder replacement. Bundle 5 Group A: extend the "advanced degree intents" guidance in `_INTENT_SYSTEM_PROMPT` (lines 78+) and in `soc_expansion.py` system prompt (lines ~93-115) to include pharmacist/pre-pharm (doctoral PharmD), speech-language pathologist/slp (master's professional), physical therapist/pre-pt/dpt (doctoral DPT). Bundle 5 Group B: add intent-keyword synonyms for librarian/mlis (master's, but not added to advanced-degree-preference clause), music therapist/mt-bc (bachelor's + cert), mortician/funeral director (associate's). Group B entries land in the synonym map only. Bundle 5: ensure `_get_crosswalk_cips_for_families` returns families containing the target SOCs even when the school doesn't report that family directly (already handled by soc_expansion's candidate pool — confirm). |
| `backend/app/services/soc_expansion.py` | Modify | Bundle 5: extend the candidate-pool query so it surfaces 29-1051 (Pharmacists), 29-1127 (SLPs), 29-1123 (PTs), 25-4022 (Librarians), 29-1129 (Music Therapists, under "Therapists, all other"), 39-4031 (Morticians/Funeral Directors) when the corresponding intent_keywords are present, even when the student's resolved CIP isn't in the SOC's natural family. The Group A SOCs (29-1051, 29-1127, 29-1123) ride the doctoral/professional preference clause; the Group B SOCs (25-4022, 29-1129, 39-4031) are surfaced without that preference so they land in their natural education-level tier per BLS (`tier-first-jobs` or `tier-early-career` for the associate's/bachelor's ones, `tier-postgrad` only for those that genuinely require it). |
| `backend/app/services/school_lookup.py` | Modify | Bundle 3: replace the `sorted(seen.values(), key=lambda s: s.institution_name)` at line 67 with a relevance-ranked sort: (1) exact name match, (2) starts-with query, (3) token-overlap count desc, (4) program count desc (proxy for "main campus over branch"), (5) name length asc. |
| `src/mcp_server/futureproof_server.py` | Modify | Bundle 3: in `_handle_get_school_programs` (lines 2245-2294), add three matchers in this order: (a) check `data/reference/school_aliases.yaml` for the normalized query; if present, look up by alias-mapped unitid or canonical name. (b) substring match (existing behavior). (c) acronym match (existing). (d) **new**: token-overlap — split the query into tokens (3+ chars, alphanumeric); a school matches if ALL query tokens appear as substrings of `name_norm` (in any order). Return all matchers' results, deduplicated by unitid, sorted by match-strength then by school_lookup's relevance rank. |
| `data/reference/school_aliases.yaml` | Create | Bundle 3: curated mapping of colloquial school names to canonical IPEDS unitids. Covers the 14 confirmed misses from the test run + ~10 common acronyms that the existing acronym path doesn't catch (e.g., "UC Berkeley", "Cal Poly SLO" — both have spaces so the acronym path is disabled). Format: `aliases: [{alias: "Penn State", canonical_unitid: 214777, canonical_name: "Pennsylvania State University-Main Campus"}, ...]`. Loaded once at MCP server boot. |
| `frontend/src/components/build-results/InsufficientDataBanner.tsx` | Create | Bundle 2: new component. Props: `{ schoolName: string; programTitle: string }`. Renders only when called (gating is in `BuildResultsScreen`). Mirrors `GradCredentialNotice` tile pattern — surface, border, icon, padding, motion. ~80 LOC. |
| `frontend/src/screens/BuildResultsScreen.tsx` | Modify | Bundle 2: import + render `InsufficientDataBanner` above the Pentagon section (line ~942). Visibility: `career.stats.ern == null && career.stats.roi == null` — the same `career` object that feeds the Pentagon's `stats={career.stats}` prop at line 954. Pass `schoolName` and `programTitle` from the build state. ~10 LOC. |
| `frontend/src/screens/SetYourCourseScreen.tsx` | Modify | Bundle 4: line 326 — extend `lowConfidence` to include `confidence === "medium"`. Around line 550-600, add inline render of `currentResolution.narrowing_hint` when non-empty AND `alternatives` empty. ~15 LOC. |
| `frontend/src/components/school/CipPicker.tsx` | Modify | Bundle 4: line 27 — keep `narrowing_hint` rendering here for the alternatives case (existing behavior) but ensure no duplication when SetYourCourseScreen renders it inline (mutually exclusive paths). |
| `frontend/src/i18n/strings.ts` | Modify | Bundle 2: 2 new keys (banner title + body) in en + es. Bundle 4: 1 new key (`syc.htmlNudge`) in en + es. ~6 entries × 2 locales = 12 string additions. |
| `backend/app/models/api.py` | Modify | Bundle 6b: add `Field(min_length=1, max_length=200)` to `major_text: str` at lines 48, 58, 734, 850. Confirm `AskCareerPickRequest.major_text` (line 62) already has it; align all four to match. |
| `backend/app/services/prefetch.py` | Modify | Bundle 6a: `_compute_career` at line 91-107 already catches `Exception` (architect's A2 correction). The fix is log-level + context: catch `LookupError` *separately and before* the generic `Exception` clause, log at INFO with structured `extra={"call_site": "prefetch_compute_one", "unitid": ..., "cipcode": ..., "soc_code": ..., "reason": "soc_not_in_gold"}`. Other exceptions still log at WARNING. The build router's stream/POST paths (`builds.py:226, 339`) already catch LookupError separately — no router changes. ~5 LOC. |
| `frontend/src/screens/SetYourCourseScreen.tsx` | Modify (already covered above) | Bundle 6b: add `maxLength={200}` attribute on the major input element at line ~485-494. ~1 LOC. |

### Data Model Changes

#### `school_aliases.yaml` (new)

```yaml
# data/reference/school_aliases.yaml
# Curated colloquial → canonical school mapping for school autocomplete.
# Loaded once at MCP server boot. Edit and PR to add entries.
#
# Format:
#   aliases:
#     - alias: "Penn State"
#       canonical_unitid: 214777
#       canonical_name: "Pennsylvania State University-Main Campus"
#       notes: "Common colloquial; substring 'penn state' not present in canonical name"

aliases:
  - alias: "Penn State"
    canonical_unitid: 214777
    canonical_name: "Pennsylvania State University-Main Campus"
  - alias: "Georgia Tech"
    canonical_unitid: 139755
    canonical_name: "Georgia Institute of Technology-Main Campus"
  - alias: "UNC Chapel Hill"
    canonical_unitid: 199120
    canonical_name: "University of North Carolina at Chapel Hill"
  - alias: "UT San Antonio"
    canonical_unitid: 229027
    canonical_name: "The University of Texas at San Antonio"
  - alias: "Cal State Long Beach"
    canonical_unitid: 110583
    canonical_name: "California State University-Long Beach"
  - alias: "West Point"
    canonical_unitid: 197036
    canonical_name: "United States Military Academy"
  - alias: "UC Berkeley"
    canonical_unitid: 110635
    canonical_name: "University of California-Berkeley"
  - alias: "UC Davis"
    canonical_unitid: 110644
    canonical_name: "University of California-Davis"
  - alias: "Cal Poly SLO"
    canonical_unitid: 110556
    canonical_name: "California Polytechnic State University-San Luis Obispo"
  - alias: "Florida A&M"
    canonical_unitid: 134097
    canonical_name: "Florida Agricultural and Mechanical University"
  - alias: "SUNY Cobleskill"
    canonical_unitid: 196158
    canonical_name: "SUNY College of Agriculture and Technology at Cobleskill"
  # Le Cordon Bleu intentionally omitted — not in IPEDS; null-unitid entries
  # silently behave identically to "no match" (architect's A7 concern). Future
  # spec can add a "school not in our dataset" UX path; for now, the existing
  # "No schools found" handler is the correct behavior.
  - alias: "Purdue Univeristy"  # intentional typo from test plan
    canonical_unitid: 243780
    canonical_name: "Purdue University-Main Campus"
    notes: "Common spelling error worth catching as an alias"

# Unitids confirmed against IPEDS 2024 release; if you add an entry, verify the
# unitid by querying base_college_scorecard.
```

#### Pydantic field updates (no new models)

```python
# backend/app/models/api.py — Bundle 6b
# All four major_text fields get the same constraint:
major_text: str = Field(..., min_length=1, max_length=200)
```

No new Iceberg tables. No DuckDB schema changes. No new MCP tool definitions.

### Service Changes

#### Bundle 1 — Template-leak gate

New helper in `set_your_course.py`:

```python
_PLACEHOLDER_CIPS = frozenset({"XX.XXXX", "XX.XX", "N/A", "n/a", ""})
_PLACEHOLDER_TITLES = frozenset({"Program Title", "...", "N/A", "n/a", ""})


def _is_placeholder_resolution(
    matched_cip: str | None, matched_title: str | None
) -> bool:
    """Detect when Gemma echoed a prompt placeholder instead of substituting.

    Small models (e4b) intermittently return the literal "XX.XXXX" / "Program
    Title" template values from the resolver prompt. Treat these as failures
    and route through the clarifier UX rather than rendering them to the user.
    """
    cip = (matched_cip or "").strip()
    title = (matched_title or "").strip()
    return cip in _PLACEHOLDER_CIPS or title in _PLACEHOLDER_TITLES
```

Used in `_fallback_resolve` (after parsing, before building IntentResult):
```python
if _is_placeholder_resolution(parsed.get("matched_cip"), parsed.get("matched_title")):
    logger.info(
        "set_your_course: placeholder leak detected and rejected",
        extra={"call_site": "set_your_course_fallback_resolve",
               "matched_cip": parsed.get("matched_cip"),
               "matched_title": parsed.get("matched_title")},
    )
    return None  # caller falls through to _build_intent_result_from_tail
```

Used in `_build_intent_result_from_tail` at **two** locations for defense in depth (the architect's B2 concern):

**(a) The `not_in_school_universe` branch** (lines 1094-1108) currently uses `matched_title or "Program not offered here"` / `matched_title or "Couldn't confirm a program"`, which preserves placeholder values like `"Program Title"` because they're truthy. Filter them out at the assignment:

```python
# Line 1097 — was: matched_title = matched_title or "Program not offered here"
matched_title = (
    "Program not offered here"
    if not matched_title or _is_placeholder_resolution("", matched_title)
    else matched_title
)

# Line 1108 — was: matched_title = matched_title or "Couldn't confirm a program"
matched_title = (
    "Couldn't confirm a program"
    if not matched_title or _is_placeholder_resolution("", matched_title)
    else matched_title
)
```

**(b) The final regex-failure gate** (line ~1121-1134) blanks both cip and placeholder titles:

```python
if not _CIP_PATTERN.match(matched_cip) or _is_placeholder_resolution(matched_cip, matched_title):
    safe_title = (
        "" if matched_title.strip() in _PLACEHOLDER_TITLES else matched_title
    )
    return IntentResult(
        matched_cip="",
        matched_title=safe_title,
        confidence="low",
        ...
    )
```

Two layers because the `not_in_school_universe` branch executes BEFORE the final gate (no early return); filtering at both points means a future refactor that adds an early return at the branch can't accidentally reopen the leak.

#### Bundle 3 — School search overhaul

New function in `src/mcp_server/futureproof_server.py`:

```python
@lru_cache(maxsize=1)
def _load_school_aliases() -> dict[str, dict[str, Any]]:
    """One-shot load of {normalized_alias: {unitid, name, notes}} from YAML.

    Loaded at first access. Tests can call .cache_clear() to force a reload.
    """
    path = pathlib.Path("data/reference/school_aliases.yaml")
    if not path.exists():
        logger.warning("school_aliases.yaml not found; alias matching disabled")
        return {}
    data = yaml.safe_load(path.read_text())
    out: dict[str, dict[str, Any]] = {}
    for entry in (data or {}).get("aliases", []):
        alias_norm = _normalize_for_school_search(entry["alias"])
        if alias_norm:
            out[alias_norm] = entry
    return out


def _tokens_for_search(query_norm: str) -> list[str]:
    """Token-overlap tokens. 3+ alphanumeric chars."""
    return [t for t in query_norm.split() if len(t) >= 3 and t.isalnum()]
```

Modified `_handle_get_school_programs` flow (replace lines 2261-2278):

```python
needle_norm = _normalize_for_school_search(needle)
try_acronym = _looks_like_acronym_query(needle_norm)
query_tokens = _tokens_for_search(needle_norm)
aliases = _load_school_aliases()
alias_hit = aliases.get(needle_norm)

filtered: list[dict] = []
seen_unitids: set[int] = set()

def _add(r: dict) -> None:
    uid = r.get("unitid")
    if isinstance(uid, int) and uid not in seen_unitids:
        seen_unitids.add(uid)
        filtered.append(r)

for r in rows:
    if not self._confidence_tier_allowed(r.get("confidence_tier"), min_confidence):
        continue
    name = str(r.get("institution_name") or "")
    name_norm = _normalize_for_school_search(name)

    # 1. Alias match — highest priority
    if alias_hit and r.get("unitid") == alias_hit.get("canonical_unitid"):
        _add(r); continue
    # 2. Substring (existing)
    if needle_norm and needle_norm in name_norm:
        _add(r); continue
    # 3. Acronym (existing)
    if try_acronym:
        acronym = _school_acronym(name)
        if acronym and acronym.startswith(needle_norm):
            _add(r); continue
    # 4. Token-overlap — ALL tokens must appear
    if query_tokens and len(query_tokens) >= 2:
        name_tokens = set(_tokens_for_search(name_norm))
        if all(any(qt in nt or nt.startswith(qt) for nt in name_tokens) for qt in query_tokens):
            _add(r); continue
```

Relevance-ranked sort in `school_lookup.search_schools` (replace line 67):

```python
def _rank_key(s: SchoolMatch, query: str) -> tuple:
    """Sort by relevance to query, then by program count (proxy for main campus)."""
    q = query.lower().strip()
    n = s.institution_name.lower()
    return (
        0 if n == q else (1 if n.startswith(q) else 2),  # exact > prefix > other
        -_program_count_for_unitid(s.unitid),             # main campus > branch
        len(s.institution_name),                          # shorter ranks first
        s.institution_name,                               # stable alpha tiebreak
    )

return sorted(seen.values(), key=lambda s: _rank_key(s, query))
```

`_program_count_for_unitid` is **pre-warmed at module load with a single `GROUP BY` query** to avoid 10 sequential MCP queries on a cold first search (architect's A3 concern):

```python
@lru_cache(maxsize=1)
def _program_counts_by_unitid() -> dict[int, int]:
    """One-shot load of {unitid: program_count} from consumable_career_outcomes.

    Pre-warmed at module load. ~80 KB resident for ~6800 institutions.
    Tests call .cache_clear() to force reload.
    """
    server = mcp_client.get_server()
    rows = server.query_iceberg(
        "SELECT unitid, COUNT(DISTINCT cipcode) AS n "
        "FROM consumable_career_outcomes "
        "GROUP BY unitid"
    )
    return {int(r["unitid"]): int(r["n"]) for r in rows if r.get("unitid") is not None}


def _program_count_for_unitid(unitid: int) -> int:
    return _program_counts_by_unitid().get(unitid, 0)
```

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/services/test_set_your_course.py` | All tests that stub Gemma with `"matched_cip": "XX.XXXX"` or `"matched_title": "Program Title"` (~8 fixtures) | **High** | Bundle 1 rejects these as placeholders; existing assertions on the returned IntentResult will fail because the IntentResult is now blanked. |
| `backend/tests/services/test_set_your_course.py` | `test_fallback_resolve_*` family (lines ~370-450 area) | **High** | Bundle 1 changes `_fallback_resolve` return contract: it now returns `None` when Gemma's response is a placeholder. Tests that assert IntentResult fields after a placeholder response need updating. |
| `backend/tests/services/test_set_your_course.py` | `test_build_intent_result_from_tail_*` family (lines ~1124-1490 area) | **Med** | Bundle 1 changes the matched_title blanking behavior when matched_cip regex fails. Assertions on `result.matched_title` may need updates. |
| `backend/tests/services/test_intent.py` | `test_intent_prompt_*` | **Low** | Bundle 5 modifies the intent prompt text. Snapshot-style assertions may flag the diff. |
| `backend/tests/services/test_soc_expansion.py` | `test_soc_expansion_*` (if exists) | **Med** | Bundle 5 extends the candidate pool. Tests that assert specific SOCs come out may need updating to reflect new ones added. |
| `backend/tests/services/test_school_lookup.py` | `test_search_schools_*` | **High** | Bundle 3 changes the sort. Tests asserting alphabetical ordering will fail. Tests asserting "result 1 has institution_name X" need to be updated to reflect relevance ranking. |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `*lowConfidence*` / `*softNudge*` | **Med** | Bundle 4 extends `lowConfidence` to medium. Tests that pass `confidence: "medium"` and assert no nudge will need to flip. |
| `frontend/src/components/school/CipPicker.test.tsx` | `*narrowingHint*` | **Low** | Bundle 4 changes the narrowing_hint render path but only when alternatives empty; CipPicker's hint render is unchanged when alternatives present. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | All existing tests | **Low** | Bundle 2 adds a banner that only renders when `career.stats.ern == null && career.stats.roi == null`. Existing fixtures use `overall_confidence: "high"` and full stats (`stats.ern`, `stats.roi` populated), so banner doesn't fire. No regression expected. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `test_set_your_course.py` placeholder-fixture tests (~8) | Rewrite fixtures to use realistic CIPs like `"13.1001"` instead of `"XX.XXXX"`; add **new** tests that explicitly assert placeholder rejection (see "New Tests Required" below) | The old fixtures conflated "Gemma returned a value" with "Gemma returned a valid value" — they were never testing the right thing. |
| `test_set_your_course.py` `_fallback_resolve` tests | Update assertions to allow `None` return when stubbed response is placeholder; keep existing behavior for valid responses | Contract change is intentional per Bundle 1. |
| `test_school_lookup.py` ordering assertions | Update expected ordering to reflect relevance rank instead of alphabetical | Sort change is intentional per Bundle 3. |
| `SetYourCourseScreen.test.tsx` medium-confidence assertions | Flip from "no nudge" to "nudge present" | Per Bundle 4 design decision. |

#### Confirmed Safe

These tests **must not break**. If they fail, STOP and escalate:

- `backend/tests/services/test_set_your_course.py` — all tests using realistic CIP fixtures (not the placeholder ones).
- `backend/tests/services/test_intent.py` — `_promote_to_leaf_cip` tests; we're not changing that function.
- `backend/tests/services/test_career_pick_qna.py` — Bundle 6b's `max_length` on api.py only adds a constraint; existing valid inputs are unaffected.
- `backend/tests/services/test_stat_engine.py` — Bundle 2 banner is frontend-only; stat_engine unchanged.
- `frontend/src/screens/BuildResultsScreen.test.tsx` — Bundle 2 banner doesn't fire on existing fixtures.
- `frontend/src/screens/MenuScreen.test.tsx`, `FutureScreen.test.tsx` — unchanged.
- All Pentagon, CareerCard, CareerTierSection tests — unchanged.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_set_your_course.py` | `test_fallback_resolve_rejects_placeholder_cip` | Stub Gemma → `{"matched_cip": "XX.XXXX", ...}`; assert `_fallback_resolve` returns None |
| P0 | `backend/tests/services/test_set_your_course.py` | `test_fallback_resolve_rejects_placeholder_title` | Stub Gemma → `{"matched_cip": "13.1001", "matched_title": "Program Title"}`; assert rejection |
| P0 | `backend/tests/services/test_set_your_course.py` | `test_fallback_resolve_rejects_na_variant` | Stub Gemma → `{"matched_cip": "N/A", "matched_title": "N/A"}`; assert rejection |
| P0 | `backend/tests/services/test_set_your_course.py` | `test_build_intent_result_blanks_placeholder_title_when_cip_invalid` | When matched_cip regex fails, matched_title="Program Title" must be blanked too |
| P0 | `backend/tests/services/test_set_your_course.py` | `test_html_prefilter_short_circuits` | Input matches HTML regex → no Gemma call; returns low-confidence IntentResult with `syc.htmlNudge` |
| P0 | `backend/tests/services/test_school_lookup.py` | `test_school_search_alias_match` | "Penn State" → first result is unitid 214777 (Pennsylvania State University-Main Campus) |
| P0 | `backend/tests/services/test_school_lookup.py` | `test_school_search_token_overlap` | "UC Berkeley" → University of California-Berkeley in results |
| P0 | `backend/tests/services/test_school_lookup.py` | `test_school_search_ranks_main_above_branch` | "Ohio State" → Main Campus (204796) ranked above Lima Campus (204671) |
| P0 | `backend/tests/services/test_school_lookup.py` | `test_school_search_university_of_florida_ranks_flagship_first` | "University of Florida" → unitid 134130 ranked above Baptist University of Florida (132408) |
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_pharmacy_intent_surfaces_pharmacist_soc` | intent_keywords includes "pharmacy" or "pre-pharm" → SOC 29-1051 in expanded list |
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_slp_intent_surfaces_slp_soc` | Same for 29-1127 |
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_physical_therapy_intent_surfaces_pt_soc` | Same for 29-1123 |
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_librarian_intent_surfaces_librarian_soc` | Same for 25-4022 |
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_mortician_intent_does_not_prefer_doctoral_socs` | intent_keywords includes "mortician" → 39-4031 (associate's) is surfaced, but doctoral SOCs in the candidate pool are NOT preferred over it. Asserts Group B doesn't ride the advanced-degree preference clause. |
| P0 | `backend/tests/services/test_soc_expansion.py` | `test_music_therapist_intent_does_not_prefer_doctoral_socs` | Same pattern — Group B (29-1129) surfaces without doctoral preference. |
| P0 | `backend/tests/services/test_prefetch.py` | `test_compute_one_lookup_error_caught` | Stub `stat_engine.compute_one` to raise LookupError; assert prefetch returns None without raising |
| P0 | `backend/tests/routers/test_set_your_course_router.py` | `test_intent_stream_rejects_oversize_major_text` | Major_text >200 chars → 422 with the expected validation message |
| P0 | `frontend/src/components/build-results/InsufficientDataBanner.test.tsx` | `renders_when_both_stats_null` | Component renders with title + body |
| P0 | `frontend/src/components/build-results/InsufficientDataBanner.test.tsx` | `does_not_render_when_either_stat_present` | Returns null when `stats.ern` or `stats.roi` is non-null |
| P0 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `shows_insufficient_data_banner_for_null_stats_career` | Integration: career fixture with `stats: { ern: null, roi: null, res: 4, grw: 7, aura: 8 }` → banner visible above the Pentagon |
| P0 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `renders_narrowing_hint_when_no_alternatives` | Resolution with non-empty narrowing_hint + empty alternatives → hint visible inline |
| P0 | `frontend/src/screens/SetYourCourseScreen.test.tsx` | `extends_softnudge_to_medium_confidence` | Resolution with `confidence: "medium"` → soft-nudge UI visible |
| P1 | `backend/tests/services/test_set_your_course.py` | `test_html_prefilter_passes_clean_input_through` | Plain text input not matching HTML regex → Gemma is called normally |
| P1 | `backend/tests/services/test_school_lookup.py` | `test_school_search_typo_purdue` | "Purdue Univeristy" → Purdue University-Main Campus in results (via alias) |
| P1 | `backend/tests/services/test_set_your_course.py` | `test_postgrad_intent_pharmacy_triggers_grad_credential_notice` | End-to-end: "Pharmacy" at Rutgers → IntentResult.intent_keywords includes "pharmacist" / "pre-pharm" |
| P2 | `frontend/src/components/build-results/InsufficientDataBanner.test.tsx` | `accessibility_aria_label_present` | Banner has correct aria-label per §3 |
| P2 | `backend/tests/services/test_school_lookup.py` | `test_school_alias_yaml_load_handles_missing_file` | If YAML is absent, falls back to substring/acronym matching with a warning log |

#### Test Data Requirements

- Fixtures with `confidence: "medium"` resolution stubs in `frontend/src/screens/SetYourCourseScreen.test.tsx`.
- Fixtures with `stats: { ern: null, roi: null, ... }` career outcomes in `BuildResultsScreen.test.tsx` (mirror an HBCU-Architecture-style row).
- New `data/reference/school_aliases.yaml` must exist and be loadable (or harness mocks the loader to test the no-file path).
- Stub MCP server responses for school search tests; reuse existing patterns in `test_school_lookup.py`.
- Existing `logs/gemma.jsonl` capture path must continue to work — manual smoke check after Bundle 1+4d edits.

### Gemma-touching work (extra discipline)

Bundles 1, 4d, and 5 modify Gemma call sites or prompts. Per spec discipline:

1. **Fallback behavior per call site:**
   - `set_your_course_resolve` (streaming) — falls back to `_fallback_resolve` already; Bundle 1's edit preserves that. If Bundle 1's gate fires on the streaming path's parsed JSON tail, the existing fallback IntentResult (line ~1018-1029) takes over with `confidence="low"`, `matched_cip=""`, `needs_clarification=True`.
   - `set_your_course_fallback_resolve` — Bundle 1 returns `None` on placeholder; caller in `stream_initial_resolution` already handles `None` by falling through to `_build_intent_result_from_tail`. No new failure mode.
   - `set_your_course_html_prefilter` (new call_site name for Bundle 4d) — short-circuits BEFORE any Gemma call. Returns a friendly IntentResult deterministically. Logged with `call_site="set_your_course_html_prefilter"` for audit.
   - `soc_expansion` (Bundle 5) — extends the candidate pool but doesn't change the call's fallback. When Gemma's tool call doesn't fire, the existing default behavior holds.

2. **`logs/gemma.jsonl` capture:**
   - All existing call sites continue to log via `extra={"call_site": ...}`.
   - Bundle 4d's pre-filter logs a synthetic entry with `call_site="set_your_course_html_prefilter"`, response body containing the short-circuited IntentResult JSON, and `duration_ms=0` (no inference). This makes it auditable without polluting real-inference latency stats.
   - No call sites removed.

3. **Both inference backends:**
   - Bundle 1's placeholder detection is post-processor — fires regardless of backend.
   - Bundle 4d's pre-filter is pre-Gemma — fires regardless of backend.
   - Bundle 5's prompt changes apply identically; cloud (OpenRouter / Gemma 26b) is expected to handle the new postgrad keywords more cleanly than e4b.
   - Smoke-test both backends after implementation: `INFERENCE_BACKEND=ollama` (e4b) and `INFERENCE_BACKEND=openrouter` (gemma 26b).

4. **Rate-limit / concurrency:**
   - No new Gemma call sites. Pre-filter REDUCES calls (HTML inputs short-circuit). Bundle 5's prompt extension may slightly increase tool-call success on soc_expansion (more relevant SOCs in candidate pool) — net latency neutral.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-05-17

#### System Context

Six bundles, all sitting on the read side of the pipeline (DuckDB Gold → MCP → FastAPI → React). No Iceberg writes, no Silver/Gold schema changes, one new static reference YAML in `data/reference/`. Two bundles touch the Gemma resolver hot path (`backend/app/services/set_your_course.py` + `intent.py` + `soc_expansion.py`), one extends the MCP `get_school_programs` tool handler in `src/mcp_server/futureproof_server.py`, two are pure frontend, and one is a backend cleanup pair (API model bounds + a log-level adjustment).

The architecture is sound at the layer level — every change respects zone boundaries. The blockers below are about *contract precision*, not layering.

#### Data Flow Analysis

Resolver path (Bundles 1, 4d, 5):
```
Frontend major_text → POST /intent/stream → set_your_course.stream_initial_resolution
   ├─ (new) HTML pre-filter → log_synthetic_event(call_site=set_your_course_html_prefilter) → IntentResult
   ├─ streaming Gemma call (call_site=set_your_course_resolve) → _build_intent_result_from_tail
   │     └─ on placeholder/regex fail → blank matched_cip (+ now matched_title)
   └─ fallback path → _fallback_resolve (call_site=set_your_course_fallback_resolve)
         └─ on placeholder → return None → caller's IntentResult builder
intent_keywords flow → soc_expansion.expand_socs (call_site=soc_expansion)
   └─ extended SYNONYM_MAP surfaces pharmacist/SLP/PT/librarian/etc.
```

School search path (Bundle 3):
```
Frontend query → mcp_client.call(get_school_programs) → _handle_get_school_programs
   ├─ alias YAML lookup (new, lru_cache)
   ├─ substring (existing)
   ├─ acronym (existing)
   └─ token-overlap (new, ALL tokens must hit)
returns rows → school_lookup.search_schools → SchoolMatch[] sorted by _rank_key
   └─ _rank_key calls _program_count_for_unitid → DuckDB query (one per unitid, cached)
```

Banner path (Bundle 2): pure render-time gate inside `BuildResultsScreen`, no new data crossing the API boundary.

Backend cleanup (Bundle 6): API model field bounds + `prefetch._run_prefetch._compute_career` log-level reclassification.

#### Contract Review

- **Pydantic models** — Bundle 6b cleanly aligns four `major_text` fields to `Field(min_length=1, max_length=200)`. `Field` import already in `api.py`. No new models.
- **MCP tool schema** — `get_school_programs` response shape unchanged; only the ordering and matcher set changes. Backward-compatible with every caller.
- **IntentResult** — Bundle 1 narrows the matched_title contract (blanks `"Program Title"` echoes). Bundle 4d adds a new call_site value but reuses the existing IntentResult shape. Both safe.
- **gemma.jsonl** — `gemma_client.log_synthetic_event` (lines 506–532) already exists and is the right affordance for Bundle 4d's pre-filter record. The spec describes the behavior but doesn't name the helper — see Concern A1.
- **Frontend types** — banner predicate as written references fields that don't exist. See Blocker B1.

#### Findings

##### Sound

- **Coexistence of the six bundles.** They touch overlapping files but disjoint logic. Bundle 1 (placeholder gate) and Bundle 4d (HTML pre-filter) both edit `set_your_course.py` but at different functions; Bundle 5 edits `intent.py` and `soc_expansion.py` SYNONYM_MAP / SYSTEM_PROMPT — independent of Bundle 1's helper. Implementation order in the Claude Code Prompt (6 → 1 → 5 → 3 → 4 → 2) lands changes in dependency order and minimizes diff overlap.
- **Bundle 1 architecture.** Defending at BOTH `_fallback_resolve` (line 957) AND `_build_intent_result_from_tail` (line 1121) is correct — those are the two return paths to the frontend. Concrete fake-but-valid placeholder swaps in the three prompts (lines 213, 288, 672 in `set_your_course.py` and line 146 in `intent.py`) is the right approach for e4b. The `_PLACEHOLDER_CIPS` / `_PLACEHOLDER_TITLES` frozensets are appropriately strict.
- **Bundle 4d HTML pre-filter location.** Putting it BEFORE any Gemma call (and logging synthetically) is the right call — it short-circuits adversarial inputs without rate-limit / latency cost and still leaves a jsonl audit trail. The existing `log_synthetic_event` helper is the correct mechanism.
- **Bundle 3 token-overlap rule.** Decision Log row 5 (ALL tokens must match, single-token falls back to substring + acronym) is the right tradeoff. Single-token "State" matching all 50 state schools would be a UX disaster.
- **Bundle 5 candidate pool.** Verified at `soc_expansion._build_candidate_pool` (line 244): it scans the full `consumable_occupation_profiles` table and substring-matches title + major_group against expanded keywords. Adding pharmacist→["pharmac"], slp→["speech", "language", "pathol"], pt→["physical therap"], etc. to `SYNONYM_MAP` (line 37) AND adding the synonyms to the `SYSTEM_PROMPT` advanced-degree list (line 118-121) WILL surface the target SOCs. Already 5 entries for pharmacy in the map — Bundle 5 is correctly characterized as "additive prompt + synonym map edits, no new architecture."
- **Bundle 2 placement.** Above the Pentagon section at line 942 with the GradCredentialNotice tile pattern is the right placement and right reuse. Banner is a pure-render gate; no new data on the wire.
- **Out-of-scope decisions.** All nine items in §2 are correctly out of scope. The `small_cohort_flag` schema-propagation deferral (item 1) is especially well-reasoned — the downstream null-pair predicate catches the same cases without an Iceberg schema spec gate.
- **`@fp-data-reviewer` SKIPPED rationale holds.** Confirmed: no Iceberg writes, no stat-formula changes, the one new file (`data/reference/school_aliases.yaml`) is a static curated lookup — same shape as the existing `major_to_cip.yaml` pattern. Skipping data-review for this bundle is correct.

##### Concerns

- **A1. `log_synthetic_event` helper not named in spec.** Bundle 4d (§4 line 292) says "log `call_site="set_your_course_html_prefilter"`" but doesn't reference the existing `gemma_client.log_synthetic_event` helper at `backend/app/services/gemma_client.py:506-532`. Without that hook, a naive implementer might try to forge a `_log_exchange` record directly or skip the log entirely. **Impact:** without using `log_synthetic_event`, the jsonl record won't have the `synthetic: true` marker that downstream consumers (audit tooling, demo telemetry) use to separate transport calls from synthetic ones. **Recommendation:** in §4 "Service Changes" for Bundle 4d, name the helper explicitly: "Log via `gemma_client.log_synthetic_event(call_site='set_your_course_html_prefilter', event='html_input_short_circuit', extra={'input_preview': major_text[:80]})`." Don't include the full input in the record — it might be an injection payload; truncate.

- **A2. Bundle 6a diagnosis is partially wrong about what's "uncaught."** Verified at `backend/app/services/prefetch.py:91-107`: `_compute_career` already wraps `stat_engine.compute_one` in `except Exception` and logs at WARNING. The LookupError described in TRIAGE.md #14b is being CAUGHT but the WARNING log level looks alarming in `/tmp/dev.log`. Same caller pattern at `backend/app/routers/builds.py:226` (POST /build) and 339 (build stream) — both already catch `LookupError` explicitly and return 404/SSE error to the frontend; no actual uncaught path exists. **Impact:** Spec describes a fix that's already partially implemented; the real issue is log-level cosmetics + missing structured context, not a missing try/except. **Recommendation:** restate §1 #6a as "downgrade `WARNING` to `INFO` and add structured `extra={"call_site": "prefetch_compute_one", "miss_reason": "lookup_error", "unitid": ..., "cipcode": ..., "soc_code": ...}` so the cache-miss provenance is auditable but the line doesn't trip alarms." The 5 LOC budget still applies, just in a different file location. No new try/except needed.

- **A3. `_program_count_for_unitid` cache cold-start cost.** Bundle 3's `_rank_key` (§4 Service Changes block, ~line 509) calls `_program_count_for_unitid(s.unitid)` for every result in the search. With 10 results and a cold cache, that's 10 DuckDB queries through the MCP layer on every fresh server's first search. The autocomplete debouncing on the frontend hides some of this, but a school-search latency budget under load matters. **Impact:** First-search-after-cold-start latency could spike by ~200-500ms (10 sequential DuckDB queries, even on Gold). **Recommendation:** prefer ONE pre-warmed query at module load time: `SELECT unitid, COUNT(DISTINCT cipcode) AS n FROM consumable_career_outcomes GROUP BY unitid` into a `dict[int, int]`. The result is ~6800 rows × 12 bytes ≈ 80 KB; trivial memory; one query lifetime. Refresh on cache-clear in tests. Code-review (@faang-staff-engineer) should validate the path before ship; flag explicitly in §8 Code Review focus areas.

- **A4. Bundle 3 sort consistency between MCP and service layer.** The spec adds match-rank tagging in `_handle_get_school_programs` (MCP layer) AND a `_rank_key` in `school_lookup.search_schools` (service layer). It's possible for these to disagree — MCP returns rows in `matcher-priority` order, then the service re-sorts by relevance rank without preserving the matcher priority. **Impact:** an alias hit in the MCP layer could get demoted by `_rank_key` if its institution_name length and program count don't line up favorably. **Recommendation:** make the matcher tier (alias / substring / acronym / token-overlap) the FIRST key in `_rank_key`, threaded through the row payload. Either tag rows server-side with a `_match_tier` int (0–3) and let `_rank_key` use it as primary key, or move ALL ranking to the MCP handler and remove `_rank_key` from `school_lookup`. Pick one source of truth.

- **A5. Bundle 2 banner predicate naming — see Blocker B1 below.** This is the load-bearing issue and is broken out as a blocker.

- **A6. Bundle 4 `narrowing_hint` length cap.** `narrowing_hint` is sanitized to 120 chars in `_fallback_resolve` (line 977) but the streaming path's `_build_intent_result_from_tail` (line 1144) does no length cap. If Gemma e4b emits a long hint via the streaming path AND alternatives is empty AND Bundle 4 renders it inline on SetYourCourseScreen, layout can break. **Impact:** UI overflow risk on the streaming path. **Recommendation:** apply the `[:120]` truncation at line 1144 too, OR cap at the React component side with `text-ellipsis line-clamp-2`. Either is fine; pick one and write the test.

- **A7. School aliases YAML with `canonical_unitid: null`.** The Le Cordon Bleu entry (§4 line 358-360) has `canonical_unitid: null` to flag "not in dataset." The loader code as written (§4 line 444-448 — `for entry in (data or {}).get("aliases", []):`) will add a null-unitid alias to `_load_school_aliases`'s output dict, and the matcher (§4 line 482 — `if alias_hit and r.get("unitid") == alias_hit.get("canonical_unitid"):`) will compare a real unitid against None and never match. That's fine functionally (no false-positive) but the result is silent — "Le Cordon Bleu" returns zero results with no "school not in our dataset" affordance. **Impact:** the test plan explicitly identified Le Cordon Bleu as a real-user input; current spec returns the same "no results" UX as for typos. **Recommendation:** either (a) write a follow-up spec for a "school not in our dataset" UX response that the alias loader can drive when `canonical_unitid is None`, or (b) drop the null entries from the YAML and add a comment that not-in-dataset schools are out of scope for this spec. Don't ship dead aliases.

- **A8. Bundle 1 `_safe_parse_tail` short-circuit before placeholder check.** `_fallback_resolve` line 957 currently does `if not parsed or not parsed.get("matched_cip"): return None`. Bundle 1 places its `_is_placeholder_resolution` check AFTER this guard, so an empty-string matched_cip already returns None — good. But `parsed.get("matched_cip") == "XX.XXXX"` truthy-passes the existing guard and would reach the placeholder check. Correct as drafted. **No action needed**, but call out in tests: `test_fallback_resolve_rejects_placeholder_cip` must use `"matched_cip": "XX.XXXX"` (not empty string) to actually exercise the new gate.

- **A9. Bundle 5 risk of false-positive postgrad classification.** Adding "mortician" and "funeral director" to advanced-degree intents in `soc_expansion.SYSTEM_PROMPT` line 118-121 is incorrect per BLS: morticians (39-4031) require an associate's degree, not a doctoral/professional. Categorizing them as "advanced degree intents" instructs Gemma to prefer doctoral/professional-level SOCs over associate's — exactly wrong for this case. **Impact:** the postgrad-tier rendering on `#tier-postgrad` would mis-frame Mortuary Science. **Recommendation:** split Bundle 5's prompt edit into two groups: (1) advanced-degree intents (pharmacist, slp, pt, dpt — all genuinely doctoral) added to the existing `SYSTEM_PROMPT` advanced-degree list; (2) intent_keywords additions for librarian (master's, distinct category), music therapist (bachelor's + cert), and mortician (associate's) — added to the synonym map and intent recognition, but NOT to the advanced-degree-preference rule. Re-check ED level for each profession before final prompt copy lands.

##### Blockers

- **B1. Banner trigger predicate references nonexistent fields.** §1 success criteria, §3 placement description, and §4 BuildResultsScreen edit all describe the predicate as `selectedCareer.stat_ern == null && selectedCareer.stat_roi == null`. Verified at `frontend/src/types/build.ts:22-92`: `selectedCareer` is typed as `CareerOutcome` (set in the build store, single field, type `CareerOutcome | null`), and `CareerOutcome` carries `stats: PentagonStats` (line 92), where `PentagonStats.ern` and `PentagonStats.roi` (lines 6-12) are the `number | null` fields the banner needs to gate on. The fields `stat_ern` / `stat_roi` AS TOP-LEVEL PROPERTIES only exist on `SchoolForCareerRow` (line 220-256), which is a *leaderboard row*, not the in-build career. **Impact:** spec-as-written will compile-error (`Property 'stat_ern' does not exist on type 'CareerOutcome'`) OR if the implementer changes the predicate to compile, will silently never fire in the cases TRIAGE.md identified (Howard / Architecture, Cincinnati State / Mortuary Science — both flow through the in-build career, not the leaderboard). This is the bug the entire bundle exists to fix. **Required fix:** rewrite §1 success criterion 2, §3 placement description, and §4 BuildResultsScreen edit row to use `career.stats.ern == null && career.stats.roi == null` (since BuildResultsScreen uses `career` not `selectedCareer` at the Pentagon render block — see line 954 `stats={career.stats}`). Update the test `shows_insufficient_data_banner_for_null_stats_career` (§4 P0 row) to set `stats.ern` and `stats.roi` to null on the fixture, not `stat_ern` / `stat_roi`. Also confirm: when the build store is populated (line 80 of `buildStore.ts`: `selectedCareer: data.selectedCareer ?? null`), is the `selectedCareer` payload the same object the Pentagon renders? If not, predicate must align with whichever value drives the Pentagon — single source of truth.

- **B2. Bundle 1's "matched_cip is real but not at this school" path also needs placeholder gate.** §4 says Bundle 1 gates inside `_build_intent_result_from_tail` at line 1121. But the function has a second early return at line 1095-1108 (the `not_in_school_universe` / `program_not_at_school` branch) that synthesizes `matched_title = matched_title or "Program not offered here"` — if Gemma returned `"Program Title"` as the literal and that branch fires, the spec's new gate at line 1121 never executes (the function returns at line 1108 with the placeholder title intact). **Impact:** edge-case leak path survives the gate. **Required fix:** in §4 "Service Changes" for Bundle 1, add a line: "Apply `_is_placeholder_resolution` check ALSO before the `not_in_school_universe` branch at line 1095, OR blank `matched_title` at line 1097 and 1108 when it equals a placeholder." Add a regression test: `test_build_intent_result_blanks_placeholder_title_when_program_not_at_school`.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions (CHANGES REQUESTED)

Resolve these before implementation starts. Most are spec-text edits, not redesigns — should be ~30 min total.

1. **B1 (blocking):** Fix the banner predicate field reference in §1 success criterion 2, §3 placement spec, §4 BuildResultsScreen row, and the §4 P0 test row. Use `career.stats.ern` / `career.stats.roi`, not `selectedCareer.stat_ern` / `selectedCareer.stat_roi`. Confirm against `BuildResultsScreen.tsx:954` that `career.stats` is the right object.
2. **B2 (blocking):** Extend Bundle 1's gate into `_build_intent_result_from_tail`'s `not_in_school_universe` branch (lines 1095-1108) so the "program not offered here" path also blanks `"Program Title"`. Add the missing regression test.
3. **A1:** Name `gemma_client.log_synthetic_event` explicitly in Bundle 4d's §4 service-change row. Truncate `input_preview` to 80 chars in the extra dict (defense vs injection payloads in jsonl).
4. **A2:** Rewrite §1 #6a and §4 Bundle 6a row from "catch uncaught LookupError" to "downgrade WARNING to INFO and add structured context" in `prefetch._compute_career`. The catch already exists at `prefetch.py:105`.
5. **A3:** Replace `_program_count_for_unitid`'s per-unitid query with a one-shot module-load `SELECT unitid, COUNT(DISTINCT cipcode) FROM consumable_career_outcomes GROUP BY unitid` cache. Spec text update + add the new helper signature.
6. **A4:** Pick one source of truth for Bundle 3 sort: either thread `_match_tier` from the MCP handler into the row payload and have `_rank_key` use it as the primary sort key, OR remove `_rank_key` and do all ordering inside `_handle_get_school_programs`. Document the choice in §4.
7. **A6:** Apply `narrowing_hint[:120]` truncation in `_build_intent_result_from_tail` (line ~1144) too, OR specify a `line-clamp-2` constraint on the new inline render in `SetYourCourseScreen.tsx`. Pick one and add a test.
8. **A7:** Decide on Le Cordon Bleu / null-unitid entries — either build a "not in our dataset" affordance (new follow-up spec, out of scope here) or drop null-unitid entries from the YAML with a comment.
9. **A9:** Split Bundle 5's prompt edits into "advanced-degree intents" (pharmacist, slp, pt, dpt) vs. "non-advanced postgrad / standalone credential intents" (librarian, music therapist, mortician). Don't tell `soc_expansion.SYSTEM_PROMPT` to prefer doctoral-level SOCs for morticians.

After these edits land, re-review is a 5-minute pass — no agent retraining of any kind required.

### Re-review (Pass 2)
**Status:** APPROVED
**Reviewed:** 2026-05-17

#### Scope of this pass

Verified the seven fix targets enumerated by the spec author (B1, B2, A1, A2, A3, A7, A9) plus a sweep of A4 and A6 (the two remaining first-pass concerns not in the explicit re-check list). Did not re-walk the rest of the architecture — first-pass findings remain in force for the unchanged surfaces (Sound list, A8 no-op, data-reviewer skip).

#### Per-item verification

| Item | Status | Evidence |
|------|--------|----------|
| **B1** banner predicate | RESOLVED | §1 success criterion 2 (line 156), §2 Decision 3 (line 175), §3 Placement (line 214), §4 BuildResultsScreen row (line 302), §4 testing-impact row for BuildResultsScreen (line 582), §4 P0 test row (line 628), §4 test data requirements (line 640) all use `career.stats.ern == null && career.stats.roi == null`. Lines 156 + 175 explicitly call out the distinction from `SchoolForCareerRow.stat_ern`/`stat_roi` so a future reader won't re-introduce the wrong predicate. Zero `selectedCareer.stat_ern` or `selectedCareer.stat_roi` references outside the historical first-pass review block. Banner test fixture (line 628) is `stats: { ern: null, roi: null, res: 4, grw: 7, aura: 8 }` — correct shape. |
| **B2** two-layer placeholder defense | RESOLVED | §4 file-changes row for `set_your_course.py` (line 295) describes both gates: (a) line-1097/1108 placeholder-aware conditionals replacing the truthy-or, and (b) the line-1121-1134 final regex-failure gate extended to short-circuit on placeholder detection. §4 Service Changes block (lines 420-455) shows both code blocks explicitly with rationale on line 455 ("future refactor that adds an early return at the branch can't accidentally reopen the leak"). Minor gap: the existing P0 test `test_build_intent_result_blanks_placeholder_title_when_cip_invalid` (line 612) only exercises layer (b); the test for layer (a) — `test_build_intent_result_blanks_placeholder_title_when_program_not_at_school` called out in the first-pass conditions — isn't in the P0 table. Not a blocker (the implementation is fully specified; @test-writer can add the missing test from the §4 description), but flagging it so it doesn't get lost. |
| **A1** `log_synthetic_event` | RESOLVED | §4 file-changes row (line 295) names `gemma_client.log_synthetic_event(call_site="set_your_course_html_prefilter", event="short_circuit", extra={...})` explicitly. §4 "Gemma-touching work" subsection (line 657) reinforces "Bundle 4d's pre-filter logs a synthetic entry with `call_site="set_your_course_html_prefilter"`...". Truncation of `input_preview` to 80 chars was called out in the first-pass A1 recommendation but isn't echoed in the spec text; the implementer should still apply that hygiene per the first-pass note, but this is implementation discipline rather than a contract-level miss. |
| **A2** prefetch log-level | RESOLVED in §4, residual misframing in §1 | §4 file-changes row for `prefetch.py` (line 307) is correctly rewritten: "_compute_career at line 91-107 already catches Exception (architect's A2 correction). The fix is log-level + context: catch LookupError separately and before the generic Exception clause, log at INFO with structured extra..." with explicit acknowledgement that no new try/except is needed. Residual: §1 #6a (line 151) still uses the original misframing "raises uncaught LookupError ... should catch and treat as cache-miss." Not blocking because §4 is the implementation source of truth, but worth a one-line edit so §1 doesn't contradict §4. |
| **A3** pre-warm program-count cache | RESOLVED | §4 Service Changes block (lines 545-566) introduces `_program_counts_by_unitid()` as `@lru_cache(maxsize=1)` over a single `SELECT unitid, COUNT(DISTINCT cipcode) AS n FROM consumable_career_outcomes GROUP BY unitid` query. `_program_count_for_unitid(unitid)` is now a dict lookup, not a per-unitid DuckDB query. Memory budget (~80 KB for ~6800 institutions) called out explicitly. Cache-clear hook for tests is documented. |
| **A7** drop null-unitid YAML entries | RESOLVED | §4 YAML data block (lines 360-363) replaces the `canonical_unitid: null` Le Cordon Bleu data entry with a comment explaining the omission and pointing to "Future spec can add a 'school not in our dataset' UX path." The loader no longer has dead aliases to ignore. |
| **A9** split mortician/music therapist out of advanced-degree intents | RESOLVED | §1 Problem Statement (lines 147-150) introduces Group A vs Group B explicitly. §1 success criterion (line 160) enumerates both groups and makes the routing distinction clear. §4 file-changes rows for `intent.py` (line 296) and `soc_expansion.py` (line 297) reflect the split: Group A SOCs (29-1051, 29-1127, 29-1123) ride the doctoral/professional-preference clause; Group B SOCs (25-4022, 29-1129, 39-4031) are surfaced without that preference and land in their natural BLS-defined education-level tier. Two new P0 tests (`test_mortician_intent_does_not_prefer_doctoral_socs` line 622, `test_music_therapist_intent_does_not_prefer_doctoral_socs` line 623) lock in the no-promotion behavior. The mortician/music-therapist mis-categorization that A9 flagged is now structurally impossible. |
| A4 (sweep) | NOT addressed in §4 | First-pass A4 (Bundle 3 sort consistency between MCP and service layer) was flagged as a concern in the first pass and is still in the conditions list (line 773), but §4 still has two ranking layers (the matcher-priority order in `_handle_get_school_programs` lines 504-525, and a separate `_rank_key` in `school_lookup.search_schools` lines 530-543) without threading `_match_tier` through. An alias hit can still be demoted by `_rank_key` when institution_name length or program count don't line up favorably. **Demoting this to a Pass 2 concern** rather than a re-blocker because: (i) it wasn't on the user's verify-this list, (ii) the impact is sort ordering, not correctness — alias hits will still appear in results, just possibly not first, (iii) the P0 tests at lines 614-617 (alias match, token-overlap, main-above-branch, flagship-above-namesake) will catch regressions empirically before code review. @faang-staff-engineer should still close the loop in §8 — see Conditions below. |
| A6 (sweep) | NOT addressed in §4 | First-pass A6 (`narrowing_hint` length cap on the streaming path) is still in the conditions list (line 774) and §4 does not specify either a `[:120]` truncation at `_build_intent_result_from_tail:1144` or a `line-clamp-2` class on the new SetYourCourseScreen inline render. **Demoting to a Pass 2 concern** for the same reason as A4 — wasn't on the verify list, impact is UI overflow on a narrow streaming-path edge case, not contract integrity. Trivial implementer fix; flag in §8 code review focus areas. |

#### Findings

##### Sound (Pass 2)

- **B1 fix is structurally complete.** Every surface that drives the banner gate now references `career.stats.ern` / `career.stats.roi`, and §1 + §2 both explicitly document the distinction from `SchoolForCareerRow.stat_ern`/`stat_roi` so a future reader can't re-introduce the wrong field. The Howard-Architecture and Cincinnati-State-Mortuary cases that motivated the bundle will now actually fire the banner.
- **B2 two-layer defense is bulletproof.** Both the `not_in_school_universe` branch (lines 1097, 1108) and the final regex-failure gate (line 1121-1134) now filter placeholder titles. Defense-in-depth rationale explicitly recorded at line 455 protects against a future early-return refactor reopening the leak.
- **A1 log_synthetic_event hook is named.** The implementer will not have to guess at how to log the pre-filter short-circuit; the call signature is in the spec.
- **A2 §4 diagnosis is now correct.** The fix description in §4 line 307 acknowledges the existing `except Exception` at `prefetch.py:91-107` and correctly scopes the work to a separate-before LookupError handler with structured `extra=`.
- **A3 cold-start cost is eliminated.** Single GROUP BY query at module load replaces 10 sequential per-unitid queries.
- **A7 doesn't ship dead aliases.** No null-unitid entries reach the loader.
- **A9 split is structurally clean.** Group A vs Group B is now a first-class distinction in §1, §4 file changes, AND the test plan — not a footnote. Morticians can't get promoted to doctoral preference even if a future implementer copy-pastes the wrong list.

##### Concerns (Pass 2)

- **A4 (carried over).** Bundle 3 still has two ranking layers without `_match_tier` threading. **Impact:** alias matches can be demoted in the final sort. **Recommendation:** thread `_match_tier` from `_handle_get_school_programs` into the row payload and use it as the primary key in `_rank_key`, OR collapse all ranking into `_handle_get_school_programs` and have `school_lookup.search_schools` just dedupe. This is a one-paragraph §4 edit; if it doesn't land in this pass, @faang-staff-engineer must verify the sort empirically against the test plan inputs in §8.
- **A6 (carried over).** `narrowing_hint` length cap not specified for the streaming path or the new inline render. **Impact:** UI overflow possible on long hints emitted by `_build_intent_result_from_tail`. **Recommendation:** add `narrowing_hint = (narrowing_hint or "")[:120]` at the streaming-path return site, OR specify `line-clamp-2` Tailwind class on the `narrowing-hint-inline` element. One-line spec edit; implementer-time fix if not in spec.
- **Minor — §1 #6a wording.** Line 151 still describes Bundle 6a as "raises uncaught LookupError ... should catch and treat as cache-miss" even though §4 line 307 correctly reframes it as a log-level + structured-context change. §4 is the implementation source of truth so this is cosmetic, but a one-line edit to §1 would prevent the contradiction.
- **Minor — missing B2 layer-(a) regression test in P0 table.** The first-pass B2 condition asked for `test_build_intent_result_blanks_placeholder_title_when_program_not_at_school`. The §4 P0 test table (line 612) has the layer-(b) test but not the layer-(a) one. @test-writer can derive it from §4 lines 422-438; flag it explicitly in §7 when tests land.

##### Blockers

None. All seven verify-list items resolved. The two carried-over concerns (A4, A6) and the two minor items are all implementer-time or @faang-staff-engineer scope — they do not block beginning implementation.

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

#### Implementation Order Confirmation

The original order in the Claude Code Prompt (6 → 1 → 5 → 3 → 4 → 2) still stands after the Group A / B split. The split is internal to Bundle 5: Group A and Group B touch the same two files (`backend/app/services/intent.py` SYNONYM_MAP + `backend/app/services/soc_expansion.py` candidate pool + SYSTEM_PROMPT) and land in the same diff. No new files, no new merge surface, no reordering needed. Implementer should land the Group A edits (advanced-degree-preference extension) and Group B edits (synonym-map-only additions) as a single coherent commit per Bundle 5.

#### Conditions

None blocking. Two carry-over recommendations for the implementer / @faang-staff-engineer to close out during implementation and code review:

1. **A4 (recommended):** Thread matcher tier through to `_rank_key`, or collapse ranking to the MCP handler. If not addressed in the spec edit, verify empirically with the §4 P0 school-search tests and call out in the §8 code review focus areas.
2. **A6 (recommended):** Apply `narrowing_hint[:120]` at `_build_intent_result_from_tail`'s streaming return, OR `line-clamp-2` on the new inline render. Either is fine; pick during implementation.
3. **Minor:** While editing §4, propagate the A2 rewording from line 307 up to §1 #6a line 151 so the problem statement matches the implementation plan. One-line edit.
4. **Minor:** Have @test-writer add `test_build_intent_result_blanks_placeholder_title_when_program_not_at_school` for the B2 layer-(a) gate when tests land.

Proceed to design vision (step 2).

### @fp-data-reviewer Review
**Status:** SKIPPED (no Iceberg schema changes, no stat formula changes, one new YAML lookup file)

### @fp-data-reviewer Review
**Status:** SKIPPED (no Iceberg schema changes, no stat formula changes, one new YAML lookup file)

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

**Status:** see-below (all P0 implemented; suite green)

### Tests Added

**Backend (24 new pytest tests across 5 files):**

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `backend/tests/services/test_set_your_course.py` | `test_fallback_resolve_rejects_placeholder_cip` | Stub Gemma → `matched_cip="XX.XXXX"`; `_fallback_resolve` returns `None` so the caller falls through to the low-confidence clarifier IntentResult. |
| `backend/tests/services/test_set_your_course.py` | `test_fallback_resolve_rejects_placeholder_title` | Partial leak (real cipcode + placeholder title) still rejects. |
| `backend/tests/services/test_set_your_course.py` | `test_fallback_resolve_rejects_na_variant` | `N/A` in both fields → rejection. |
| `backend/tests/services/test_set_your_course.py` | `test_build_intent_result_blanks_placeholder_title_when_cip_invalid` | Final regex-failure gate blanks `matched_title="Program Title"` and the cip. |
| `backend/tests/services/test_set_your_course.py` | `test_build_intent_result_blanks_placeholder_title_when_program_not_at_school` | **Architect's Pass-2 carry-over (B2 layer-a):** real cipcode NOT in school's universe + `matched_title="Program Title"` → title becomes `"Program not offered here"`, `program_not_at_school=True`. Strict assertion ensures the not_in_school_universe → national-crosswalk-hit branch fires (the exact branch B2 covers). |
| `backend/tests/services/test_set_your_course.py` | `test_html_prefilter_short_circuits` | `<script>alert(1)</script>` short-circuits BEFORE any Gemma call: `generate_stream_async` and `generate` are both stubbed to raise if reached; structured event carries the plain-English nudge; `log_synthetic_event` fires with `call_site="set_your_course_html_prefilter"`. |
| `backend/tests/services/test_school_lookup.py` | `test_school_search_ranks_main_above_branch` | Ohio State Main Campus (204796, 140 programs) ranks ABOVE Lima Campus (204671, 8 programs) for query "Ohio State". |
| `backend/tests/services/test_school_lookup.py` | `test_school_search_university_of_florida_ranks_flagship_first` | "University of Florida" (134130, flagship) ranks ABOVE "The Baptist University of Florida" (132408) — exact-name bucket wins over the bucket-2 fallback. |
| `backend/tests/services/test_school_lookup.py` | `test_returns_distinct_schools_after_sort_change_still_dedupes` | Regression guard: Bundle 3's new sort still dedupes by unitid. |
| `backend/tests/services/test_school_lookup.py` | `test_school_search_alias_match` | "Penn State" → canonical unitid 495767 surfaces via the YAML alias even though the canonical name is "The Pennsylvania State University". Runs against the live `data/reference/school_aliases.yaml` (cache cleared before/after). |
| `backend/tests/services/test_school_lookup.py` | `test_school_search_token_overlap` | "UC Berkeley" → University of California-Berkeley (110635) surfaces (either via alias or token-overlap; both are valid paths). |
| `backend/tests/services/test_soc_expansion.py` | `test_pharmacy_intent_surfaces_pharmacist_soc` | `intent_keywords=["pharmacy"]` → SOC 29-1051 (Pharmacists) in candidate pool with `education_level="Doctoral or professional degree"`. |
| `backend/tests/services/test_soc_expansion.py` | `test_pharmacy_intent_pre_pharm_alias_surfaces_same_soc` | `"pre-pharm"` synonym maps to same SOC. |
| `backend/tests/services/test_soc_expansion.py` | `test_slp_intent_surfaces_slp_soc` | `intent_keywords=["slp"]` → SOC 29-1127 (Speech-Language Pathologists). |
| `backend/tests/services/test_soc_expansion.py` | `test_slp_intent_speech_pathologist_synonym_surfaces_same_soc` | Full-name alias `"speech pathologist"` resolves to same SOC. |
| `backend/tests/services/test_soc_expansion.py` | `test_physical_therapy_intent_surfaces_pt_soc` | `intent_keywords=["physical therapy"]` → SOC 29-1123 (Physical Therapists). |
| `backend/tests/services/test_soc_expansion.py` | `test_physical_therapy_intent_dpt_alias_surfaces_same_soc` | `"dpt"` credential alias resolves to same SOC. |
| `backend/tests/services/test_soc_expansion.py` | `test_librarian_intent_surfaces_librarian_soc` | `intent_keywords=["librarian"]` → SOC 25-4022 with `education_level="Master's degree"`. |
| `backend/tests/services/test_soc_expansion.py` | `test_mortician_intent_does_not_prefer_doctoral_socs` | **Group B negative test:** mortician pool contains 39-4031 at associate's tier; no doctoral decoys (29-1228 Physicians, 25-1011 Business Teachers) leak in. |
| `backend/tests/services/test_soc_expansion.py` | `test_music_therapist_intent_does_not_prefer_doctoral_socs` | **Group B negative test:** music therapist pool contains 29-1129 at bachelor's tier; unrelated doctoral SOCs stay out. |
| `backend/tests/services/test_prefetch.py` | `test_compute_one_lookup_error_caught` | `stat_engine.compute_one` raises `LookupError` → task completes with `result.career=None` and `result.error` populated; no exception propagates. |
| `backend/tests/services/test_prefetch.py` | `test_compute_one_lookup_error_logged_at_info_not_warning` | The same LookupError logs at INFO (NOT WARNING) with structured extra (`call_site="prefetch_compute_one"`, `unitid`, `cipcode`, `soc_code`, `reason="soc_not_in_gold"`). Verifies architect's A2 log-level fix. |
| `backend/tests/routers/test_set_your_course_router.py` | `test_intent_stream_rejects_oversize_major_text` | 201-char `major_text` → 422 at Pydantic validator; handler never called. |
| `backend/tests/routers/test_set_your_course_router.py` | `test_intent_stream_accepts_exactly_200_chars` | Boundary check: 200 chars (at the cap) is accepted — confirms the constraint is inclusive. |

**Frontend (9 new vitest tests across 3 files; 1 file new):**

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `frontend/src/components/build-results/InsufficientDataBanner.test.tsx` *(new file)* | `renders_when_both_stats_null` | Banner mounts with title + body; interpolates `programTitle` and `schoolName` via `useT()` placeholder substitution. |
| `frontend/src/components/build-results/InsufficientDataBanner.test.tsx` | `renders with the caution-amber left stripe accent` | Brightpath visual cue (left border `border-l-accent-caution`) present. |
| `frontend/src/components/build-results/InsufficientDataBanner.test.tsx` | `does_not_render_when_either_stat_present` | Wrapper-gating contract: banner is suppressed when `stats.ern != null` OR `stats.roi != null` OR both present; renders when both are null. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | `shows_insufficient_data_banner_for_null_stats_career` | Integration: `career.stats={ern:null, roi:null, res:4, grw:7, aura:8}` + Howard University → banner visible above the "Build Stats" Pentagon header; body interpolates "Architecture" + "Howard University"; DOM-order check on `compareDocumentPosition`. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | `does_not_show_banner_when_stats_present` | Regression guard: existing fixtures (full stats) → banner does not fire. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | `does_not_show_banner_when_only_ern_is_null` | Predicate is AND, not OR: `{ern:null, roi:6}` → no banner. |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `renders_narrowing_hint_when_no_alternatives` | Resolution with non-empty `narrowing_hint` + empty `alternatives` → inline hint visible (testid `narrowing-hint-inline`); CipPicker NOT mounted. |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `does_not_render_inline_narrowing_hint_when_alternatives_present` | Mutual-exclusion: when CipPicker mounts (alternatives present), the inline hint hides — no duplication. |
| `frontend/src/screens/SetYourCourseScreen.test.tsx` | `extends_softnudge_to_medium_confidence` | Resolution with `confidence: "medium"` → soft-nudge UI surfaces (`testid="soft-nudge"`, text matches `/close call/i`); commit button stays enabled. |

### Edge Cases Covered

- [x] Placeholder echo on `matched_cip` alone (XX.XXXX leak).
- [x] Placeholder echo on `matched_title` alone with a real cipcode (partial leak).
- [x] `N/A` variant (both fields).
- [x] Final regex-failure gate blanking the title even when the cip already failed.
- [x] `not_in_school_universe → program_not_at_school` branch (B2 layer-a) — the historically truthy-or that preserved "Program Title".
- [x] HTML-shaped input short-circuit: NO Gemma call, synthetic log written.
- [x] Sort-rank: main campus > branch campus by program count.
- [x] Sort-rank: exact-name match wins over alphabetical neighbor.
- [x] Alias-only match (no substring overlap in canonical name).
- [x] Token-overlap multi-token query.
- [x] Group A intent → doctoral/professional credential SOC surfaces with the right education level.
- [x] Group B intent → non-doctoral SOC surfaces; doctoral decoys do not leak into the pool.
- [x] `LookupError` from `compute_one` caught separately, logged at INFO with structured `extra`.
- [x] Pydantic 200-char cap on `major_text`: oversize rejected, exactly-200 accepted.
- [x] Banner gating predicate (AND, not OR) for `stats.ern/roi == null`.
- [x] Banner i18n: program + school interpolation via `useT()`.
- [x] Narrowing-hint inline render only when alternatives are empty (mutual exclusion with CipPicker).
- [x] softNudge extends to `confidence === "medium"`; commit remains enabled.

### Test Results

| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (backend) | 1882 | 0 | 0 | 1882 |
| vitest (frontend) | 795 | 0 | 0 | 795 |

Suite delta:
- Backend: 1858 → 1882 (+24 new tests).
- Frontend: 786 → 795 (+9 new tests).

### Existing Tests Status

All tests in §4 "Existing Tests at Risk" stayed green — no regressions:
- `test_set_your_course.py` placeholder-fixture tests already used realistic CIPs; no rewrite needed.
- `test_set_your_course.py` `_fallback_resolve` tests pass with the new None-on-placeholder contract.
- `test_set_your_course.py` `_build_intent_result_from_tail` tests pass (title-blanking unchanged on valid inputs).
- `test_intent.py` prompt tests pass (Bundle 5 prompt extension is additive, not snapshot-asserted).
- `test_soc_expansion.py` existing tests pass (Group A + B entries are additive to the SYNONYM_MAP).
- `test_school_lookup.py` existing tests pass — note `test_sorted_by_name` survived because the test data has the program-count cache return `{}`, so the rank tiebreaker degrades to name length + alpha (matching the original behavior for the IUB fixture).
- `SetYourCourseScreen.test.tsx` existing low-confidence tests pass (medium-confidence is new, low-confidence path unchanged).
- `CipPicker.test.tsx` existing narrowing-hint tests pass (CipPicker still owns the hint when alternatives present; new inline render is in SetYourCourseScreen).
- `BuildResultsScreen.test.tsx` existing tests pass (banner gated on dual-null stats; existing fixtures have full stats).

### Gaps Identified

None of the P0 tests required implementation flex — the production code was already correctly written by the implementation step. Notes on test design choices:

1. **Group B doctoral-preference assertion is encoded structurally, not behaviorally.** Whether Gemma actually obeys SYSTEM_PROMPT rule 3 ("do not apply doctoral preference to Group B") is a prompt-quality concern, not a deterministic unit test. The negative tests instead assert that the **candidate pool** (what Gemma sees) doesn't accidentally include unrelated doctoral decoys via the synonym keyword. This is what an actual prompt regression would look like.

2. **Alias-match test runs against the live YAML.** Rather than mocking `_load_school_aliases`, the test clears the lru_cache and lets the real YAML load. This means the test couples to the curated file at `data/reference/school_aliases.yaml` — if the "Penn State" entry is ever removed, this test will fail. That's intentional: removing an alias entry is a UX regression worth catching.

3. **Token-overlap test passes via either alias OR token-overlap path.** "UC Berkeley" matches both — the alias maps to unitid 110635 AND the tokens "berkeley" + "california" appear in the canonical name. The test asserts the row surfaces; it does not pin which matcher fired. If we want to specifically test token-overlap-without-alias, we'd need a query like "Davis California" that's NOT in the alias YAML. Left as P1 follow-up.

4. **The `test_html_prefilter_passes_clean_input_through` P1 test was not implemented.** The reasoning: the existing happy-path test (`test_happy_path_streams_content`) already proves clean input flows through to Gemma — explicitly testing "doesn't trigger the pre-filter" would be testing the absence of a code path, which is theatre. The current `test_html_prefilter_short_circuits` proves the regex fires on HTML; the existing happy-path proves the regex doesn't fire on plain text.

5. **HTML pre-filter test only covers the streaming entry point.** `_fallback_resolve` also has the pre-filter defense in depth, but its call path requires more setup (gemma_client.generate, intent helpers, candidate pool). Given the streaming path is the primary surface and the defense-in-depth gate is a 5-line copy of the streaming gate, a single test was deemed sufficient. P1 follow-up if we ever see a path that reaches `_fallback_resolve` with HTML.

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@fp-design-auditor)
**Status:** COMPLETE
**Verdict:** CHANGES REQUESTED — one hardcoded pixel value at the mounting site; all other checks pass

---

#### Files audited

- `frontend/src/components/build-results/InsufficientDataBanner.tsx` (100 lines)
- `frontend/src/screens/BuildResultsScreen.tsx` — mounting site (~line 948)
- `frontend/src/i18n/strings.ts` — keys `build.insufficientData.title` / `build.insufficientData.body` in en / es / ar
- `frontend/src/screens/SetYourCourseScreen.tsx` — Bundle 4 edits (lowConfidence + narrowing_hint)
- `frontend/src/components/school/GradCredentialNotice.tsx` — sibling reference

---

## `frontend/src/components/build-results/InsufficientDataBanner.tsx`

### PASS

- **Surface tokens (check 1).** Container class chain matches §3 spec exactly: `relative rounded-xl bg-bp-mid/60 border border-border-subtle border-l-[3px] border-l-accent-caution p-4 tablet:p-5 shadow-md`. Every token is a Brightpath token — `bg-bp-mid` (DESIGN.md §Backgrounds), `border-border-subtle` (§Borders), `border-l-accent-caution` (§Accents), `shadow-md` (§Elevation), `rounded-xl` (§Border Radii). The `/60` opacity modifier is valid Tailwind usage, not a hardcoded value. No hex literals.
- **Typography — title (check 2).** `font-display text-body-lg font-semibold text-text-primary leading-tight` at line 86 matches the §3 spec table exactly. `font-display` = Fredoka (DESIGN.md §Font Families). `text-body-lg` = 18px scale token. `text-text-primary` = warm white token. `leading-tight` = 1.1 line-height token. All correct.
- **Typography — body (check 2).** `font-body text-body text-text-secondary leading-relaxed` at line 92. `font-body` = Nunito. `text-body` = 16px scale token. `text-text-secondary` = label/description token. `leading-relaxed` = 1.4 token. All correct. `mt-3 pl-8` match the §3 spec.
- **Spacing tokens (check 3).** `p-4 tablet:p-5` on container, `gap-3` on row-1 flex wrapper, `pl-8` on body `<p>`, `mt-3` on body `<p>`, `mt-0.5` on icon `<span>`. All are Tailwind spacing utilities on the 4px base (DESIGN.md §Spacing). No hardcoded pixel values inside the component.
- **Icon implementation (check 4).** Icon `<span>` carries `text-accent-caution opacity-90 w-5 h-5 shrink-0 mt-0.5` — exact match to §3. Inline SVG uses `stroke="currentColor"` and `fill="currentColor"` throughout (lines 72, 74, 76, 79) — color is token-controlled, no hex literal. ⓘ anatomy (circle + dot + stem) is centered in the 20×20 `viewBox="0 0 20 20"` with `width="20" height="20"`. The containing `<span>` is itself `w-5 h-5 inline-flex items-center justify-center`, which ensures the SVG sits flush in the 20×20 box.
- **Motion (check 5).** `springs.smooth` imported from `@/styles/motion` at line 19 — correct source. Initial variants: `{ opacity: 0, y: 12 }` for full motion and `{ opacity: 0 }` for reduced motion at line 40 — matches §3 Motion spec exactly. `animate={{ opacity: 1, y: 0 }}` is correct. The reduced-motion guard uses `useReducedMotion()` from framer-motion, consistent with GradCredentialNotice's idiom at line 161.
- **Accessibility (check 7).** `aria-labelledby="insufficient-data-banner-title"` on the `<motion.section>` container (line 43). `<h3 id="insufficient-data-banner-title">` at line 84. `data-testid="insufficient-data-banner"` on container (line 44). `data-testid="insufficient-data-banner-title"` on the `<h3>` (line 85). Icon `<span>` has `aria-hidden="true"` (line 56). All required accessibility attributes are present and correct.
- **Dark-first compliance (check 8).** No `light:` or `dark:` overrides. No hardcoded `#` hex or `rgb()` values anywhere in the component. All colors route through Brightpath tokens.
- **i18n placeholders (check 9).** en string at strings.ts:413 uses `{programTitle}` and `{schoolName}` — exact match to the prop names passed by the component at lines 93-96 (`t("build.insufficientData.body", { programTitle, schoolName })`). es string at strings.ts:1375 also uses `{programTitle}` and `{schoolName}`. ar string at strings.ts:2332 also uses `{programTitle}` and `{schoolName}`. All three locales consistent. "Department of Education" is kept as the English proper noun in es and ar with an appropriate parenthetical, consistent with §3 copy direction.

### FAIL

None in the component itself.

### WARNINGS

- **Reduced-motion animate target includes `y: 0` (line 41).** When `reducedMotion` is true, `initial` is `{ opacity: 0 }` (no y), but `animate` is always `{ opacity: 1, y: 0 }`. Framer Motion will animate the y property from its default (0) to 0 — effectively a no-op — so no visible motion violation occurs. This is functionally correct and matches GradCredentialNotice's identical pattern at line 180/182. Non-blocking.

---

## `frontend/src/screens/BuildResultsScreen.tsx` — mounting site

### PASS

- **Mounting predicate (check 10).** Line 948: `career.stats.ern == null && career.stats.roi == null` — AND operator, not OR. Strict per spec §1 Success Criteria. Correct.
- **Component import.** Line 21: `import { InsufficientDataBanner } from "@/components/build-results/InsufficientDataBanner"` — correct path alias.

### FAIL

- **Hardcoded pixel value at mounting wrapper (line 949):** `<div style={{ marginTop: 48 }}>`. The 48px value corresponds to Brightpath `space-12` (DESIGN.md §Spacing: `space-12 = 48px = mt-12`). This should be `className="mt-12"` — or the `<div>` wrapper should be eliminated and the `<motion.section>` root of InsufficientDataBanner should carry the margin directly. The surrounding Section 3 wrapper at line 960 has the same pattern (`style={{ marginTop: 48 }}`), which is a pre-existing issue outside this bundle's scope. This banner's wrapper is new code introduced by Bundle 2 and must use the token. **Expected:** `<div className="mt-12">` or margin applied via Tailwind on the banner's own root element. **Found:** `style={{ marginTop: 48 }}` at BuildResultsScreen.tsx:949. Contradicts DESIGN.md §Spacing ("Use Tailwind spacing utilities directly").

---

## Sibling consistency — `GradCredentialNotice.tsx` vs `InsufficientDataBanner.tsx` (check 6)

### PASS

- **Container class chain.** GradCredentialNotice: `relative rounded-xl bg-bp-mid/60 border border-border-subtle border-l-[3px] {stripeClass} p-4 tablet:p-5 shadow-md` (lines 185-191). InsufficientDataBanner: identical chain with `border-l-accent-caution` hardcoded in place of the dynamic stripe class (lines 46-50). Structural match confirmed.
- **Motion idiom.** Both use `springs.smooth` from `@/styles/motion`, `useReducedMotion()`, and the same `initial`/`animate` shape with y-translate disabled under reduced motion. GradCredentialNotice uses y:16 for entrance and y:-12 for exit; InsufficientDataBanner uses y:12 for entrance and no exit (no `AnimatePresence` wrapper needed — the banner has no exit animation per §3). The y-magnitude difference (12 vs 16) is intentional: GradCredentialNotice is a larger component and its y-travel is proportionally larger. Not a violation.
- **Reading rhythm.** Both components use the icon + title in a `flex items-start gap-3` row with a body `<p>` below indented to align with the title. The visual column alignment is consistent.
- **Structural divergence — `AnimatePresence` wrapper.** GradCredentialNotice wraps in `<AnimatePresence mode="wait">` because it has an exit animation and can swap in/out on tone change. InsufficientDataBanner omits `AnimatePresence` deliberately — per §3, no exit animation is needed. Not a violation; intentional architectural difference documented in the spec.

### WARNINGS

- None.

---

## `frontend/src/i18n/strings.ts` — i18n strings (check 9 extended)

### PASS

- **en title** (line 412): `"Earnings data isn't published for this program"` — matches primary recommendation in §3 copy table.
- **en body** (line 413): Matches §3 primary body copy verbatim, with `{programTitle}` and `{schoolName}` placeholders.
- **es title** (line 1374) and **es body** (line 1375): Two-beat structure (fact + reassurance) maintained. "Department of Education" kept as English proper noun with parenthetical Spanish gloss `(Department of Education)`. Formal neutral register. Placeholder names unchanged.
- **ar title** (line 2331) and **ar body** (line 2332): "Department of Education" kept in English in parentheses. Placeholder names unchanged.

---

## Bundle 4 — `frontend/src/screens/SetYourCourseScreen.tsx` (checks 11b)

### PASS

- **`lowConfidence` extended to medium (check 11a, lines 331-333).** Pattern is `currentResolution?.confidence === "low" || currentResolution?.confidence === "medium"` — OR of two strict equality checks, not a substring match. Correct per spec §3.
- **`narrowing-hint-inline` render (check 11b, lines 613-622).** Predicate: `currentResolution.narrowing_hint && (!initialResolution?.alternatives || initialResolution.alternatives.length === 0)`. This is "hint is non-empty AND alternatives array is empty-or-absent." Correct per spec §3. Testid `narrowing-hint-inline` present at line 618. The hint renders only when the conditions are met — mutually exclusive with CipPicker's existing hint rendering per the comment at line 608.

---

## Summary

| Check | File | Result |
|-------|------|--------|
| 1 Surface tokens | InsufficientDataBanner.tsx | PASS |
| 2 Typography | InsufficientDataBanner.tsx | PASS |
| 3 Spacing tokens | InsufficientDataBanner.tsx | PASS |
| 4 Icon implementation | InsufficientDataBanner.tsx | PASS |
| 5 Motion | InsufficientDataBanner.tsx | PASS |
| 6 Sibling consistency | InsufficientDataBanner.tsx vs GradCredentialNotice.tsx | PASS |
| 7 Accessibility | InsufficientDataBanner.tsx | PASS |
| 8 Dark-first compliance | InsufficientDataBanner.tsx | PASS |
| 9 i18n placeholders | strings.ts (en/es/ar) | PASS |
| 10 Mounting predicate | BuildResultsScreen.tsx:948 | PASS |
| 10 Mounting wrapper spacing | BuildResultsScreen.tsx:949 | FAIL |
| 11a lowConfidence OR pattern | SetYourCourseScreen.tsx:331-333 | PASS |
| 11b narrowing-hint-inline predicate | SetYourCourseScreen.tsx:613-615 | PASS |

**Required fix:** `BuildResultsScreen.tsx:949` — replace `<div style={{ marginTop: 48 }}>` with `<div className="mt-12">` to use the Brightpath `space-12` token (DESIGN.md §Spacing).

### Code Review (@faang-staff-engineer)
**Status:** COMPLETE
**Reviewed:** 2026-05-17

#### Summary

Six bundles, ~12k LOC of context reviewed against the diff list. The placeholder gate, HTML pre-filter, alias loader, prefetch log split, banner predicate, max_length adds, and Group A/B postgrad split are all implemented in line with the spec, and the test suite covers the edges I'd have asked for. The architectural blockers (B1, B2) and the seven concerns from the architect's first pass are resolved at the file level — I verified each independently against the actual code, not just the spec text.

There is one serious behavioral regression that the spec text itself baked in: the helper-call construction at `set_your_course.py:1244-1249` and `1261-1266` wipes legitimate `matched_title` values in the `not_in_school_universe` branch because `_is_placeholder_resolution("", title)` always returns True (the empty `cip` argument hits `_PLACEHOLDER_CIPS` on the OR side before `title` is evaluated). The previous truthy-or preserved real titles; the new conditional always overrides. Existing tests don't catch it. UX impact is visible at `SetYourCourseScreen.tsx:734` where the rendered "{program} isn't offered at {school}" message will now read "Program not offered here isn't offered at School X" instead of "Biology isn't offered at School X".

Two architect-flagged carry-overs (A4, A6) remain unaddressed in code — both acknowledged as implementer-time items in the Pass-2 review. Worth a one-line fix while we're here. Everything else: ship.

#### Findings

##### 🟠 Serious

###### F1. `_is_placeholder_resolution("", title)` short-circuits via OR and stomps real titles

**Impact:** In the `not_in_school_universe` branch (where Gemma resolved to a real CIP that isn't offered at the selected school), a legitimate `matched_title` like `"Biology"` is overwritten with `"Program not offered here"` even though it's not a placeholder. The frontend at `SetYourCourseScreen.tsx:733-734` interpolates the title into the user-facing message `t("syc.notOfferedAtSchool")` via `.replace("{program}", currentResolution.matched_title || majorText)`, so a student who types "Biology" at a school without a Biology program sees "Program not offered here isn't offered at School X" instead of "Biology isn't offered at School X". Pre-Bundle-1 the truthy-or `matched_title or "Program not offered here"` preserved real titles. The new construction does not.

**Location:** `backend/app/services/set_your_course.py:1244-1249` (the `not_in_school_universe → national-crosswalk-hit` branch) and `1261-1266` (the `not_in_school_universe → no-crosswalk-hit` branch).

**The Problem:** `_is_placeholder_resolution` at line 411-423 returns `cip in _PLACEHOLDER_CIPS or title in _PLACEHOLDER_TITLES`. `_PLACEHOLDER_CIPS` contains `""`. The call sites pass `""` as the cip argument because they only want to check the title:

```python
matched_title = (
    "Program not offered here"
    if not matched_title
    or _is_placeholder_resolution("", matched_title)
    else matched_title
)
```

For any non-empty real title (`"Biology"`, `"Computer Science"`, etc.), the helper evaluates `"" in _PLACEHOLDER_CIPS` → `True` → short-circuits and returns `True` without checking the title at all. The conditional collapses to `if True else matched_title` → always overrides.

I verified this with a literal eval of the helper against `"Biology"` — returns True. The test at `test_build_intent_result_blanks_placeholder_title_when_program_not_at_school` only exercises the placeholder case (`matched_title="Program Title"`); there's no companion test for "real title, branch fires, title is preserved." That gap is why this slipped through CI.

**The Fix:** Add a title-only variant to the helper, or check the title directly at the call sites. Either:

```python
def _is_placeholder_title(matched_title: str | None) -> bool:
    return (matched_title or "").strip() in _PLACEHOLDER_TITLES

# At line 1244:
matched_title = (
    "Program not offered here"
    if not matched_title or _is_placeholder_title(matched_title)
    else matched_title
)
# Same fix at line 1261.
```

Or inline:
```python
matched_title = (
    "Program not offered here"
    if (not matched_title
        or matched_title.strip() in _PLACEHOLDER_TITLES)
    else matched_title
)
```

Add a regression test: `test_build_intent_result_preserves_real_title_when_program_not_at_school` — pass `matched_title="Biology"` and a `matched_cip` that hits the `not_in_school_universe` branch; assert `result.matched_title == "Biology"` and `result.program_not_at_school is True`.

##### 🟡 Moderate

###### F2. Architect's A4 (sort-tier consistency) and A6 (narrowing_hint length cap) carry-overs not closed in code

**Impact (A4):** Bundle 3 has two ranking layers — `_handle_get_school_programs` in MCP land sorts by `program_name` then caps (futureproof_server.py:2376), then `school_lookup.search_schools` re-sorts by `_rank_key`. The matcher tier (alias vs substring vs acronym vs token-overlap) is not threaded through. For aliases that map to flagship/main schools (the curated set), the program-count tiebreak in `_rank_key` masks the issue because flagships have high program counts. For an alias that maps to a low-program-count institution — none today, but adding a small-college alias later would be sharp-edge territory — the alias hit can be demoted by a higher-program-count Bucket-2 token-overlap match. The architect flagged this in Pass 1; it was carried forward to me.

**Impact (A6):** `narrowing_hint` is truncated to 120 chars in `_fallback_resolve` at line 1120 (`...strip()[:120]`) but NOT in `_build_intent_result_from_tail` at line 1312 (`narrowing_hint = str(parsed.get("narrowing_hint", "") or "").strip()`). The new inline render at `SetYourCourseScreen.tsx:613-622` also has no `line-clamp-2`. If the streaming path returns a long hint from e4b, the UI will wrap into a wall of text under the matched-title line.

**Location:** `school_lookup.py:56-72` (`_rank_key`); `futureproof_server.py:2376` (program_name sort cap); `set_your_course.py:1312` (no `[:120]`); `SetYourCourseScreen.tsx:617` (no `line-clamp-2`).

**The Fix (A4):** Either:
1. Tag rows in `_handle_get_school_programs` with `_match_tier: int` (0=alias, 1=substring, 2=acronym, 3=token-overlap) and make `_rank_key` use it as the primary key, OR
2. Move all ranking into the MCP handler and let `search_schools` just dedupe.

Option 1 is the smaller patch — three lines in `_add` to set the tier on the row, then a `_rank_key` change to read it. Current behavior is empirically fine for the curated alias set, but the design is brittle.

**The Fix (A6):** Add `[:120]` at `set_your_course.py:1312`:
```python
narrowing_hint = str(parsed.get("narrowing_hint", "") or "").strip()[:120]
```
Mirrors the fallback path. One-line edit. Optionally also `line-clamp-2` on the inline render as defense in depth.

###### F3. `LookupError` catch in prefetch can mask programming bugs (KeyError/IndexError)

**Impact:** The new `except LookupError` clause at `prefetch.py:105` catches `KeyError` and `IndexError` as well — both are subclasses of `LookupError`. Today only `stat_engine.compute_one` at line 844 raises `LookupError` explicitly, but `compute_pentagon` → `_row_to_outcome` does `row["unitid"]`, `row["cipcode"]`, `row["soc_code"]` dict access at `stat_engine.py:502-506`. If MCP returns a malformed row missing one of those keys, the `KeyError` now gets logged at INFO as `reason="soc_not_in_gold"` instead of WARNING as a real fault. Wrong diagnosis, easy to miss in production logs.

The risk is low — MCP's contract should hold — but the new code is strictly more permissive than the spec intent ("benign cache-miss for SOC not in gold").

**Location:** `backend/app/services/prefetch.py:105-122`.

**The Fix:** Either narrow the catch to a custom sentinel exception (`stat_engine` raises `class SOCNotInGold(LookupError)` and prefetch catches that), or be more defensive at the call site by sniffing the exception message before downgrading to INFO. The custom sentinel is cleaner and self-documenting. Not blocking — the test at `test_compute_one_lookup_error_caught` covers the happy case, and a real KeyError-bug would still surface as a low-frequency anomaly worth chasing. Worth a follow-up either way.

##### 🔵 Minor

###### F4. Multiple unitid mismatches between spec §4 YAML block and the shipped `data/reference/school_aliases.yaml`

**Impact:** Spec text in §4 (lines ~444-486) lists Penn State as `214777`, Cal Poly SLO as `110556`, Florida A&M as `134097`, SUNY Cobleskill as `196158`. Shipped YAML at `data/reference/school_aliases.yaml` uses `495767`, `110422`, `133650`, `196033` respectively. Tests assert against the YAML values (`test_school_search_alias_match` uses `495767`). The team must have re-verified unitids against IPEDS during implementation, which is the right call — but §4's text is now stale relative to the source-of-truth YAML.

**Location:** `data/reference/school_aliases.yaml` (correct) vs. `docs/specs/bugfix-post-100-build-test-fixes-bundle.md §4 file changes block` (stale).

**The Fix:** Update the spec's example YAML block to match the shipped values, or add a one-line caveat noting the spec example was illustrative and the shipped values were re-verified. Documentation only — no code change.

###### F5. Empty string in `_PLACEHOLDER_TITLES` is correct but worth a code comment

**Impact:** `_PLACEHOLDER_TITLES` includes `""`, which means `_is_placeholder_resolution("13.1001", "")` returns True and rejects valid-cip-with-blank-title responses from the fallback path. This is the intended behavior (the UI has nothing to render without a title), but a future reader will see `""` in a set called `_PLACEHOLDER_TITLES` and wonder if it's a bug or a feature. Add a one-line comment at line 406-408 explaining the rationale: "Empty string is intentional — reject valid-cip-with-blank-title responses; the UI has no title to render."

**Location:** `set_your_course.py:405-408`.

##### What's Actually Good

I'm not going to pretend the rest of the diff is impressive just to seem balanced. It IS impressive:

- **HTML pre-filter regex (`set_your_course.py:432`)** is well-scoped. Empirically tested against `1<2`, `a<b<c`, `<3`, math expressions — all reject correctly. Tested against `<script>`, `<img src=x onerror=...>`, `<div>`, `</p>`, `<a href="x">`, `< b >` — all match. The pattern `<\s*/?[a-zA-Z][a-zA-Z0-9]*(\s|/?>|\s+[a-zA-Z]+=)` is strict enough that it requires a real tag-name + terminator/attr, not just `<`. Defense-in-depth at both streaming and fallback entry points. Synthetic-event logging via `gemma_client.log_synthetic_event` is exactly the right hook per architect A1.
- **Two-layer placeholder defense (Bundle 1).** The streaming path's `_build_intent_result_from_tail` has both the branch-level filter at `1244-1266` (modulo F1 above) AND the final regex-failure gate at `1283-1289` with the strict `safe_title` check. The fallback path's `_fallback_resolve` rejects placeholders at line 1094 before the IntentResult is built. The placeholder example values in all three prompts (lines 213, 288, 672 in `set_your_course.py` and line 148 in `intent.py`) were swapped to concrete fake-but-valid examples (`"11.0701"` / `"Computer Science"`) — exactly what e4b needs to stop echoing.
- **`_program_counts_by_unitid` pre-warm (`school_lookup.py:21-53`).** Single GROUP BY query at first call instead of N sequential per-unitid queries. ~80KB memory for ~6800 institutions, `@lru_cache(maxsize=1)`, defensive failure path returns `{}` and degrades to alpha tiebreak only. Architect's A3 concern is fully closed.
- **Alias loader (`futureproof_server.py:226-267`).** `@lru_cache(maxsize=1)` for one-shot YAML read. Three discrete failure paths: file-missing → INFO log + `{}`; `yaml.YAMLError` → WARNING log + `{}`; non-int / non-str entries silently skipped. No race conditions on first call (lru_cache is thread-safe for this signature). No null-unitid entries ship (architect A7 closed).
- **Bundle 5 Group A/B split.** `SYSTEM_PROMPT` rule 3 at `soc_expansion.py:151-157` is unambiguous to an LLM reader: lists Group B keywords explicitly, names the target SOCs and their real ED levels (39-4031 associate's; 25-4022 master's; 29-1129 bachelor's + cert), tells Gemma to "match the candidate at its real education level." `SYNONYM_MAP` at lines 67-91 wires all six Group A + Group B keyword families to title-substring expansions that hit the right SOC titles in the candidate pool. The negative tests (`test_mortician_intent_does_not_prefer_doctoral_socs`, `test_music_therapist_intent_does_not_prefer_doctoral_socs`) lock the no-promotion behavior in structurally — they assert the candidate pool composition, not Gemma obedience, which is the right test design for prompt-quality concerns.
- **Banner predicate + streaming-order race.** I worried about partial state flashing the banner on initial render. Verified at `BuildResultsScreen.tsx:733`: the entire results column short-circuits to `BuildLoadingScreen` when `isBuilding || !build`. The banner only mounts after `build` is fully populated. `career = build.career` is derived synchronously from the atomic build payload. No race window.
- **Bundle 6b max_length=200.** Longest legitimate `major_text` literal in the test suite is 44 chars (`"Mechanical and Aerospace Systems Engineering"`). Real BLS occupation titles cap around 70. 200 is loose enough that no legitimate input gets rejected, strict enough that absurd payloads (XSS attempts, multi-paragraph prose) bounce at validation. Frontend `maxLength={200}` on the input is the right belt-and-suspenders.

#### Required Changes

| Severity | Finding | Routing |
|----------|---------|---------|
| 🟠 Serious | F1 — `_is_placeholder_resolution("", title)` stomps real titles in `not_in_school_universe` branch | Claude Code (implementer) — add `_is_placeholder_title()` helper or inline the title check; add regression test |
| 🟡 Moderate | F2 — A4 sort-tier threading + A6 narrowing_hint cap | Claude Code (implementer) — thread `_match_tier` or move ranking; add `[:120]` at `set_your_course.py:1312` |
| 🟡 Moderate | F3 — narrow `LookupError` catch to a custom sentinel | Claude Code (implementer) — define `class SOCNotInGold(LookupError)` in stat_engine, catch that specifically in prefetch |
| 🔵 Minor | F4 — spec §4 YAML block has stale unitids | Spec author — update §4 to match shipped YAML or add caveat |
| 🔵 Minor | F5 — add comment explaining `""` in `_PLACEHOLDER_TITLES` | Claude Code (implementer) — 1-line comment |

#### Questions for the Author

- F1 is the only one I genuinely care about resolving before ship. Is there a reason the spec text spelled the helper-call construction the way it did, instead of a direct `title in _PLACEHOLDER_TITLES` check at the branch sites? If the intent was "use the helper for symmetry," I'd push back — the helper's OR semantics actively don't match the title-only check the branch sites need.
- F3 — has the team ever seen a `KeyError` or `IndexError` propagate out of `compute_pentagon` in prod logs? If never, the custom-sentinel refactor is a nice-to-have. If once or twice, it's a real safety net.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUIRED
- [ ] BLOCKER

F1 is the only required pre-merge fix. F2/F3 are moderate but the demo deadline tomorrow is real and these are tractable as a follow-up if F1 lands tonight. Route F1 to the implementer via §10. Once F1 is fixed and a regression test is in place, re-review is a 2-minute pass.

---

## §9 Verification

**Status:** ALL PASSED
**Verified:** 2026-05-17 23:24

### Backend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | 1 fixable I001 import-sort in `tests/services/test_school_lookup.py:293` — fixed (stdlib before third-party), re-run clean |
| Type check (mypy) | PASS | No errors — 64 source files |
| Tests (pytest) | PASS | 1884 passed, 0 failed |

### Frontend (@fp-builder)
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors |
| Tests (vitest) | PASS | 795 passed, 0 failed across 70 test files (includes 3 new InsufficientDataBanner tests) |
| Production build (Vite) | PASS | 878 modules transformed, build completed in 1.70s; pre-existing chunk-size advisory (1304 kB > 500 kB) — not a failure |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | ruff failed | I001 import block unsorted in `backend/tests/services/test_school_lookup.py:293` — stdlib `unittest.mock` and third-party `mcp_server` in wrong order | Moved `from unittest.mock import MagicMock` above `from mcp_server.futureproof_server import FutureProofMCPServer`, with blank-line separator per isort convention |
| 2 (re-run from top) | All checks passed | — | — |

---

## §10 Discussion

```
[2026-05-17] Initial spec drafted by Claude Code + Jeff Cernauske
Triage evidence: reports/chrome-agent-real-2026-05-17/TRIAGE.md
Bundles, decisions, and out-of-scope items all locked in during triage session.

[2026-05-17] @faang-staff-engineer review → CHANGES REQUIRED.
Routing to Claude Code (implementer):

  - F1 (Serious, blocking): _is_placeholder_resolution("", title) at
    set_your_course.py:1244-1249 and 1261-1266 always returns True due to
    OR short-circuit on empty cip. Real titles get stomped to "Program not
    offered here". UX impact visible at SetYourCourseScreen.tsx:733-734.
    Fix: add _is_placeholder_title(title) helper or inline the title-only
    check. Add regression test test_build_intent_result_preserves_real_title_
    when_program_not_at_school covering matched_title="Biology" + a cipcode
    that fires the not_in_school_universe branch.

  - F2 (Moderate, non-blocking): Architect A4 (sort-tier threading) +
    A6 (narrowing_hint[:120] on streaming path). Defer to follow-up if F1
    lands tonight; one-line fixes whenever there's time.

  - F3 (Moderate, non-blocking): consider narrowing prefetch's LookupError
    catch to a custom SOCNotInGold(LookupError) sentinel. Follow-up.

  - F4 (Minor, doc-only): spec §4 YAML example block has stale unitids
    relative to shipped data/reference/school_aliases.yaml. Update §4 or
    add a caveat. Spec author scope, not implementer.

  - F5 (Minor): add a one-line comment at set_your_course.py:405-408
    explaining why "" is in _PLACEHOLDER_TITLES.

Re-review after F1 fix is a 2-minute pass.
```

---

## §11 Final Notes

**Human Review:** PENDING

This bundle exists because a Chrome-in-LLM agent confabulated a previous test report. The real Playwright harness at `scripts/chrome_agent_e2e/` is now the source of truth for E2E evidence; consider keeping it around for future regression sweeps.

The aliases YAML will need maintenance as we add IPEDS releases. Worth a follow-up to autogenerate it from a curated input list rather than hand-editing.

If Bundle 1's gate ever fires in production with `call_site="set_your_course_html_prefilter"`, that's a signal we need to look at our input UX again — students shouldn't be typing markup-shaped content into the major field.
