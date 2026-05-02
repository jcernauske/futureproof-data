---
name: pentagon-stat-explanation
description: Write plain-English explanations of FutureProof's pentagon stats (ERN, ROI, RES, GRW, AURA) for a 16-year-old who's never seen CIP, SOC, BLS, IPEDS, EADA, or O*NET. Translates the actual scoring formulas into readable copy, with technical terms tucked in parentheses. Use when writing or revising stat popovers, legend blurbs, hover cards, or any user-facing copy that explains how a pentagon stat is computed. Triggers on "explain a stat", "stat copy", "stat popover", "stat documentation", "write a stat explanation", "rewrite the ERN/ROI/RES/GRW/AURA explanation".
---

# pentagon-stat-explanation

Write the plain-English explanation for any of FutureProof's five pentagon stats. The audience is a **16-year-old high school junior** who has never heard of CIP, SOC, BLS, IPEDS, EADA, or O*NET — but who can absolutely handle the truth if you just tell it to them clearly.

> **Reshape in flight (2026-05).** The pentagon-stat-reshape spec at `docs/specs/pentagon-stat-reshape.md` is mid-implementation on this branch. HMN ("Human Edge") has been removed; its O*NET signal is now folded into a **blended RES**. The freed 5th-axis slot is now **AURA** ("Brand Gravity"), an institution-level score from `consumable.institution_aura`. Until the reshape lands fully, verify the shipped formula files against the spec before writing copy.
>
> **Final pentagon: ERN, ROI, RES (blended), GRW, AURA.**

This skill does two things:

1. **Voice rules** — how to translate technical scoring into language a teenager reads as English.
2. **Surface inventory** — every place in the codebase where stat copy lives, so a copy change doesn't ship half-applied.

---

## Step 1 — Read the actual formula before writing a word

Don't paraphrase from memory. Open the real formula file. The five stats and where each is computed (post-reshape):

| Stat | Computed in | Function / column | Notes |
|------|-------------|-------------------|-------|
| **ERN** (Earning Power) | `src/gold/futureproof_engine.py` | `compute_stat_ern` | Per-career; 60% program rank + 40% occupation wage percentile. |
| **ROI** (Return on Investment) | `src/gold/futureproof_engine.py` | `compute_stat_roi` | Per-career; piecewise-linear DTE map. |
| **RES** (AI Resilience, *blended*) | `backend/app/services/stat_engine.py` | `_blend_res` (post-reshape) | Per-career; blends raw `stat_res` (Karpathy + Anthropic AI exposure, from `consumable.ai_exposure`) and raw `stat_hmn` (O*NET task profile, from `consumable.onet_work_profiles`). DRAFT formula = `round_half_up(0.5 × stat_res + 0.5 × stat_hmn)` with NULL fallthrough. The Fight AI scorer reads the **raw** row scores, not the blend (Decision 4 revised — see spec §2). |
| **GRW** (Growth Outlook) | `src/gold/bls_ooh_occupation_profiles.py` | `grw_score` (computed in SQL) | Per-career; BLS 10-year projection, percent-ranked. |
| **AURA** (Brand Gravity) | `backend/app/services/stat_engine.py` | `compute_pentagon` (institution-level lookup) | Institution-level — one MCP tool call per build, keyed on `unitid`. The same `aura_score` is stamped onto every `CareerOutcome` for that build. CIP substitution does not change AURA. NULL when the institution has no `consumable.institution_aura` row (no IPEDS-Finance + no EADA coverage). |

The single source-of-truth Gold table for AURA is `consumable.institution_aura` (landed by `docs/specs/full-pipeline-eada.md`). It is reached at chat time via the **`get_institution_aura`** MCP tool (`src/mcp_server/futureproof_server.py`). For "show the receipts" explainers, that tool returns the full row including `aura_score_basis` (`three_term`, `two_term_finance_only`, etc. — humanize via `_humanize_basis` in `receipts.py` before showing to the student).

Read the function or SQL block and identify, in this order:

1. **Inputs** — what fields are actually fed into the formula?
2. **Mechanism** — is it a percent-rank, a piecewise linear map, a weighted blend, a direct lookup?
3. **Universe** — what set of things is being ranked or compared against (all U.S. occupations? all programs in the same field of study? all task profiles?).
4. **Source dataset** — which federal data source the inputs come from (College Scorecard, BLS Occupational Outlook Handbook, O*NET, Karpathy AI Exposure, Anthropic Economic Index, BEA Regional Price Parities).

If you can't answer all four from reading the source code, stop and ask. The skill is useless if the explanation describes a formula that isn't the one running.

---

## Step 2 — Voice rules

### Rule 1 — Plain term first, technical term in parens

Lead with the language a 16-year-old uses. Tuck the official term in parens so a curious reader (or skeptical parent) can verify.

> ❌ "Compares the program's CIP family earnings rank against the SOC-level wage percentile."
>
> ✅ "Compares how graduates of *your school's program* rank against graduates of the *same program at other schools* (within the same field of study, technically called a Classification of Instructional Programs family, or CIP family)."

### Rule 2 — Expand acronyms once, then use freely

First mention: full name, then acronym in parens. After that, the acronym is fine.

> ✅ "...published by the Bureau of Labor Statistics, or BLS. The BLS updates this data every two years..."

### Rule 3 — Concrete examples beat definitions

A 0.92 percentile rank means nothing on its own. *"Software Developer scores 0.92 — about 92% of all U.S. careers pay less"* does the work. Pick two examples per stat: one near the top, one near the bottom.

### Rule 4 — Always answer "why this metric?"

Most explainers stop at *what* the metric is. The trust-building part is *why* — what would be misleading if we used a simpler version. Use a "Picture two students…" contrast to make the gap visible.

> "If we only used the school comparison, a top-ranked Philosophy program would score the same as a top-ranked Computer Science program. That'd be misleading — Philosophy graduates earn less, and that's not the school's fault, it's just what the career pays."

### Rule 5 — No sanitizing the bad news

If the formula penalizes a thing, say it penalizes that thing. Don't soften "your career is heavily exposed to AI" into "this career has automation considerations." The whole product is built on giving students the unvarnished signal.

### Rule 6 — Voice anchors

- **Honest**, not corporate. *"Cashier scores around 0.05 — almost every career pays more."*
- **Confident**, not hedged. Avoid *"may", "could", "potentially"* unless the data genuinely is uncertain.
- **Direct**, not breezy. The reader is making a six-figure life decision, not picking a flavor of LaCroix.

---

## Step 3 — Standard structure for every stat explanation

Every pentagon-stat explanation has the same four sections, in this order. Don't reinvent the structure per stat — consistency is the documentation feature.

### Section 1: The one-line definition

What the score actually measures, in one sentence. This is the "legend blurb" version — short enough to fit under the stat name in a list.

> ERN: *"Compares what graduates of this program at this school earn against peers in the same field, blended with how this career's wages rank among all U.S. occupations."*

### Section 2: How it works

The mechanism, with concrete example numbers. Two examples — one high, one low. If the formula is a weighted blend, name the weights and what each piece measures.

> "Two pieces, mixed together:
> - **60%** — How does *your school's program* rank against the *same program at other schools*?
> - **40%** — How does *this career's pay* rank against *every other career in America*?
> Software Developer ends up around 0.92 (about 92% of careers pay less). Cashier lands near 0.05."

### Section 3: Where the data comes from

The federal data source, in plain English with the official name in parens. If the source updates on a known cadence, mention it.

> "The U.S. government's official jobs handbook (the Occupational Outlook Handbook, published by the Bureau of Labor Statistics, or BLS). Same source your guidance counselor uses — we just compute the ranking for you. Updated every two years."

### Section 4: Why we built it this way

The "Picture two students…" contrast. This is the section that earns trust. Show what naive version we rejected and why.

> "If we only used the school comparison, two #1-ranked programs in different fields would score the same — even if one leads to careers that pay twice as much. The 40% occupation blend grounds the score in real American salaries, not just how you stack up against your classmates."

---

## Step 4 — Apply to every surface

Pentagon-stat copy lives in **at least seven places** (plus AURA-specific UI states post-reshape). Updating one and forgetting the others is the most common bug in this area. Update all of them in the same change, or none of them.

> **Companion reference.** `docs/reference/stat-display-surfaces.md` is the full, audited index of every place a stat is shown to a user. It tags each surface with whether an "Ask Gemma to explain this" affordance already exists and locks the chat-scope contract for new affordances. Use it as the deeper checklist; the table below is the fast-glance summary.
>
> **Rendering authority for the structured-receipt path.** `frontend/src/components/menu/ExplainStatReceipt.tsx` is where the SKILL's prose-field outputs (`one_liner`, `components[*].explainer`, `why_mix_paragraph`) actually render once Gemma emits valid JSON. The voice rules below dictate the words; the component dictates the visual structure. Per `docs/specs/feature-explain-stat-receipt.md`.

### Live UI surfaces (user-visible)

| File | What it powers |
|------|----------------|
| `frontend/src/data/statExplanations.ts` | The legend blurb shown under each stat name in the build results pentagon. (Section 1 — the one-line definition.) |
| `frontend/src/i18n/strings.ts` | i18n mirror of `statExplanations.ts` — must match. |
| `frontend/src/components/build-results/bossData.ts` (`STAT_INFO`) | The "?" info popover that opens when a user clicks the question-mark icon next to a stat. (Sections 2–4 — the long-form explanation.) |

### Gemma-facing context (changes what the LLM says about your stats)

| File | What it powers |
|------|----------------|
| `backend/app/services/boss_fights.py` | Stat lines fed into boss-fight context. Gemma reads these to explain how a stat affects a specific boss outcome. Keep the framing consistent with the popover. |
| `backend/app/services/ask_gemma.py` | "Drivers" blocks that follow up the stat score with the underlying numbers (median earnings, occupation wage, etc.). Header strings here must match the stat name in `_STAT_ALIAS`. |

### Wrapped / share renders (export surface)

| File | What it powers |
|------|----------------|
| `backend/app/services/wrapped_renderer.py` | `_STAT_NAMES`, `_STAT_COLORS`, `_STAT_CONTEXT` maps + the template-context emit. Keys must match the live `StatKey` set (post-reshape: `aura`, not `hmn`). |
| `backend/templates/wrapped/*.html` | Stat-label strings and the `{{ stat_aura }}` template var (post-reshape). Grep before editing: `rg 'stat_hmn|\bHMN\b' backend/templates/`. |

### Documentation (lower priority, but should track reality)

| File | What it powers |
|------|----------------|
| `docs/futureproof_hackathon_prd_v8.md` | PRD definitions table. Update when the formula changes, not when the copy is just polished. |
| `docs/specs/feature-build-results-screen.md` | Spec-level definitions. Same rule. |
| `README.md` | Marketing-facing claims. Cross-check against `docs/reference/voice-guide.md`. |

### AURA-specific surfaces (post-reshape, missing-data state)

About 1 in 10 institutions has no `consumable.institution_aura` row. AURA renders as `None` in those cases, which has its own UI handling — these are surfaces the standard four-section explainer won't reach because the score doesn't exist:

| Surface | Behavior when `stats.aura is None` |
|---------|-------------------------------------|
| Pentagon vertex (`PentagonChart`) | Open ring at outer perimeter, no fill, `text-muted` stroke. Geometry stays a regular pentagon. |
| Vertex label | `AURA —` (em-dash suffix). No `—/10`, no `0/10`. |
| `STAT_INFO` popover | Renders the standard AURA card body, plus an appended line: *"Not enough institutional data for {school name} to score this yet."* This is the **only** missing-data sentence in the UI — no banner, no toast, no card-edge tint (per `feedback_no_substitution_caveat.md`). |
| Receipt strings | `AURA — (no brand-gravity data for this school yet)`. |

If you change the **formula**, all of the above need to change. If you're only polishing the **copy**, the three live UI surfaces and the two Gemma-facing files are the minimum.

---

## Step 5 — Worked example: Earning Power (ERN)

Reference example showing the four sections applied. Use this as the calibration target when writing the other four stats.

> ### Earning Power (ERN)
>
> **The one-liner.** Compares what graduates of this program at this school earn against peers in the same field, blended with how this career's wages rank among all U.S. occupations.
>
> **How it works.** Two pieces, mixed together:
> - **60%** — How your school's program ranks against the same program at other schools, by graduate earnings (within the same field of study, called a Classification of Instructional Programs family, or CIP family).
> - **40%** — How this career's median pay ranks against every other career in the country (each career has an official ID called a Standard Occupational Classification code, or SOC code — there are about 800 of them).
>
> A few examples:
> - **Software Developer** lands at ~0.92 on the occupation piece — about 92% of U.S. careers pay less.
> - **Cashier** lands at ~0.05 — almost every career pays more.
>
> **Where the data comes from.** Two federal sources:
> - Graduate earnings come from the **College Scorecard** (U.S. Department of Education).
> - Occupation wages come from the **Occupational Outlook Handbook**, published by the **Bureau of Labor Statistics** (BLS). It's the same dataset your guidance counselor uses.
>
> **Why we mix both pieces.** Picture two students: one from the #1-ranked Computer Science program in the country, one from the #1-ranked Philosophy program. Both are top of their field. But Computer Science graduates earn far more than Philosophy graduates — that's not because one school is better, it's just what those careers pay. If we only used the school comparison (the 60%), both students would get the same Earning Power score. The 40% occupation blend grounds your score in what your career actually pays in the real world.

---

## Step 6 — Before declaring done

Run this checklist:

- [ ] Read the actual formula in the source file before writing.
- [ ] All four sections present (one-liner, how it works, where data comes from, why this design).
- [ ] At least two concrete numerical examples (one high, one low).
- [ ] Every acronym (CIP, SOC, BLS, O*NET, BEA, etc.) expanded on first use.
- [ ] Every technical term has a plain-English version in front of it; the technical term sits in parens.
- [ ] No softened bad news. If the data says a career is exposed, the copy says it's exposed.
- [ ] Updated all three live UI surfaces (`statExplanations.ts`, `strings.ts`, `bossData.ts`).
- [ ] Updated Gemma-facing context (`boss_fights.py`, `ask_gemma.py`) if the framing changed.
- [ ] If formula changed (not just copy): docs in `docs/specs/` and `docs/futureproof_hackathon_prd_v8.md` updated too.
- [ ] No drift between the legend blurb and the popover — they're describing the same metric, just at different lengths.

If any item fails, the explanation isn't done.
