# Session Log — Copywriter — feature-pdf-report-exports

| Field | Value |
|---|---|
| Session ID | 2026-05-06-copywriter-feature-pdf-report-exports |
| Timestamp | 2026-05-06 |
| Agent | @fp-copywriter |
| Spec | `docs/specs/feature-pdf-report-exports.md` |
| Status going in | DESIGN VISION |
| Status going out | DESIGN VISION (visionary done, copywriter done; @genai-architect still owed §10 review of the Gemma prompt) |

## Brief

Design Vision pass — write all in-PDF copy and the runtime Gemma system prompt for the PDF Report Exports feature. The PDF voice is NOT the in-app voice; per Decision #4, all RPG language is translated to advisory language for the printed surface.

## Inputs read

- `docs/specs/feature-pdf-report-exports.md` — full spec, including:
  - §1 success criteria, especially the static-mandatory college questions wording and the "no QR" / "no Gemma prose in comparison" rules.
  - §2 Decision #4 — RPG → advisory translation table (non-negotiable).
  - §2 Decisions #6 (5/audience cap, 1 floor, 2 mandatory college) and #7 (voice rules per audience).
  - §3.4 (5-level palette including the new Insufficient-data chip).
  - §3.5 (page-1 risk profile + data-coverage caveat templates).
  - §3.6 (comparison page).
  - §3.10 + §3.11 Design Vision Refinement (visionary's round-2 visual decisions, especially the asymmetric spacing on the caveat and the cost-strip refinements).
  - §4 — `pdf_copy.py` function signatures, `pdf_questions.py` async signature, `gemma_client.py` extension contract.
  - §4 Gemma-touching surfaces — timeout posture, JSON-mode contract, fallback paths, JSONL observability.
  - §5 architect + data-reviewer reviews — especially the per-boss threshold table, the field-by-field source-of-truth table, and the Insufficient-data ruling.
- `docs/reference/voice-guide.md` — voice characteristics, anti-patterns, locked vocabulary, register-by-surface table. The PDF gets the new "PDF / printed report" override row (added in §8 completion phase, not by this pass).
- `backend/app/services/next_steps.py` (`_SYSTEM` constant) — reference pattern for a Next-Steps-register Gemma prompt that drops the RPG metaphor.

## Deliverables produced

All written into the spec at the locations specified by the brief.

### Item 1 — Verdict-line template (§3.11.1)

- Locked the parameterization: `pdf_copy.verdict_line(build)` reads `Build.career.debt_to_earnings_annual` plus the `RiskLevel` distribution across the 5 risk factors. No Gemma involvement.
- 5 risk-summary buckets (`mostly_low`, `mixed_moderate`, `mostly_elevated`, `multiple_high`, `insufficient`) with first-match-wins selection rules.
- 5 ROI-summary buckets aligned to the categorical bins already used by `roiLabelKey()` in `FinancesCard.tsx` (Strong / Solid / Caution / Risky thresholds at 8% / 18% / 30% of `debt_to_earnings_annual`).
- Capitalization rule: lowercase continuation after the colon, sentence-case for the second clause.
- 4 worked examples covering all 4 risk-summary buckets the brief asked for (mostly-Low, mixed-Moderate, mostly-Elevated, multiple-High) plus a 5th (insufficient) for completeness.

### Item 2 — Risk one-liner copy (§3.11.2)

- 5 bosses × 5 levels = 25 strings, each ≤ 120 chars after substitution.
- Each non-Insufficient cell carries one concrete data anchor pulled from `Build.career` (no recomputation).
- Confirmed the "Insufficient data" row uses the same lone string for all 5 bosses (`Data unavailable for this program.`) — per-boss variants would not aid a counselor scanning the table.
- Anchor field names per boss: `ai_exposure_percentile`, `debt_to_earnings_annual`, `bls_growth_pct`, `onet_burnout_top_driver`, `earnings_75th_pct`. These match the §5 source-of-truth table.
- Null-anchor fallback: when a boss's `raw_score` is non-null but the named anchor is `None`, drop the data clause cleanly (level word survives). New unit test: `test_risk_one_liner_handles_null_anchor`.

### Item 3 — Glossary entries (§3.11.3)

- 8 entries: CIP, SOC, ERN, ROI, RES, GRW, AURA, "Career risk".
- Each definition ≤ 120 chars, written for a 16-year-old who has not seen these acronyms before.
- Followed the spirit of `pentagon-stat-explanation` skill (parenthetical technical anchor) but more compressed for the 8pt body grid.
- "Career risk" replaces "boss fight" per Decision #4.

### Item 4 — Static fallback questions per audience (§3.11.4)

- **Ask the college (2 mandatory + 1 fallback)**:
  - Lightly refined the §1 draft of mandatory question 1 from `"Which majors at [School] will yield [Career]?"` to `"Which majors at {school} most often lead graduates into {career}?"` — same factual question, less transactional register, reads better aloud, no implied guarantee. Documented the rationale inline.
  - Mandatory question 2 unchanged in meaning, tightened phrasing to actively name what the counselor's office can offer ("through coursework, clubs, or internships you already offer?").
  - 1 fallback covering published outcomes data ("median earnings one year out, employment rate, average debt at graduation").
- **Ask your parents (2 fallbacks, audience-first voice)**: Both reference the parent (`our family`, `you watch up close`), use action verbs (`carry`, `spare`), avoid student-internal markers. Question 1 anchors to page-1 cost strip; question 2 turns the conversation toward lived experience.
- **Ask yourself (2 fallbacks, student-first voice)**: Both start with `Will I` / `Am I`, anchor to specific page-1 elements, resist easy answers.
- All within the 200-char cap.

### Item 5 — Data-coverage caveat copy (§3.11.5)

- Two variants for `match_quality ∈ {scorecard_only, partial_no_onet}`, both ≤ 140 chars.
- Refinements over the §3.5 spec drafts:
  - Lead with `Note:` instead of em-dash (more scannable at 7.5pt italic muted).
  - Each variant names the actually-missing dataset specifically rather than generic "career-task data."
  - Both end with the same reassurance clause about earnings/cost/debt being full coverage — that's the load-bearing fact and it ends the line, not the warning.

### Item 6 — "Where each school pulls ahead" template (§3.11.6)

- 3-bucket selection: ≥2 lead cells, 1 lead cell, 0 lead cells.
- Refined the 0-leader case from a bare `"no clear leader on these factors."` to `"no clear leader on these factors; trade-offs are even."` — the addition reframes "leads on nothing" as a positive observation about a balanced comparison rather than as a put-down.
- Tie handling: per `@fp-data-reviewer` round-1 ruling, ties produce no leading cell on a row, so they reduce a build's lead count without needing a separate tie clause in the copy.
- `{factor}` placeholders use human-readable labels (`Earnings`, `ROI`, `4-year cost`, `AI displacement risk` …) — never the stat code. Stat-priority order specified for the >2-leads case.

### Item 7 — Gemma system prompt + JSON schema (§4 new subsection "Gemma System Prompt and JSON Schema")

- Single system prompt as a Python string literal ready to paste into `pdf_questions.py` as `_SYSTEM`. Target ~250 tokens (under the 300-token cap).
- Schema: 3 audience arrays, 0–3 entries each (NOT 1–5; static fallbacks fill the floor, the 2 mandatory college questions are inserted by service code at indices [0, 1]).
- Voice rules pin per-audience starts:
  - `ask_the_college`: audience-first, action verbs, school name, NEVER `Will I` / `Am I`.
  - `ask_your_parents`: audience-first, family referent, NEVER `Will I` / `Am I`.
  - `ask_yourself`: student-first, MUST start with `Will I` / `Am I` / `Do I` / `Would I`.
- Forbidden vocabulary list quoted verbatim from Decision #4 + the in-app stat codes (ERN/ROI/RES/GRW/AURA/HMN). The prompt also names the *replacement* terms ("debt-to-earnings", "AI displacement", "this program"), so the model has a path forward when it would have reached for forbidden vocabulary.
- Build-context payload scoped to ~80 tokens: school, major, career, top-2 risks, top-2 strengths. Nothing else. Per `feedback_scoped_llm_contexts.md`.
- Failure-mode mapping covers all 5 `gemma_path` values and adds a forbidden-term post-hoc filter (returns `fallback_malformed` if any RPG term leaks past the system prompt).
- 0-to-3 floor (instead of 1-to-3) is intentional: gives Gemma a no-filler license. Static fallbacks fill any gap.

## Decisions made (not unilaterally — flagged where I stretched)

1. **Mandatory college question 1 wording.** Refined from `"will yield"` to `"most often lead graduates into"` — same question, better register. Documented inline; visible to product partner for veto.
2. **Insufficient-row context copy is uniform across bosses.** Per-boss variants would add noise without aiding a counselor scan. Flagged in §3.11.2.
3. **0-to-3 questions per audience from Gemma (not 1-to-3).** This is a register decision: forced "say something" produces filler. Floor of 1 is satisfied by static fallback constants. Documented in §4.
4. **ROI-summary thresholds at 8% / 18% / 30%.** Aligned to the existing `roiLabelKey()` bins so the PDF and on-screen ROI label can never disagree. Asks `@fp-data-reviewer` to re-confirm if the bins drift.
5. **0-leader template adds `; trade-offs are even`.** Refines the spec draft. Documented inline.
6. **Forbidden-term post-hoc filter inside `pdf_questions.py`.** Not in the spec drafts but the right defense-in-depth: even with the forbidden list in the system prompt, the renderer should refuse to ship a PDF with an RPG term in a question. Adds a fallback path; documented in §4.

## Disagreements flagged (not overridden)

- None. The brief explicitly invited refinement of spec drafts where wording was provisional, and I refined within the documented voice rules. No structural disagreements with §2 decisions.

## Files modified

| File | Section(s) | Change |
|---|---|---|
| `docs/specs/feature-pdf-report-exports.md` | §3.11 (new subsection) | Added §3.11 Copy Specifications with 6 sub-subsections (verdict template, 25-string risk one-liner table, glossary, static fallback questions, data-coverage caveat, "Where each school pulls ahead"). Inserted between §3.10 / Design Vision Refinement and `### Interactions`. |
| `docs/specs/feature-pdf-report-exports.md` | §4 (new subsection "Gemma System Prompt and JSON Schema") | Added the Gemma `_SYSTEM` prompt, scoping rules, token budgets, JSON schema, user-message template with worked example, failure-mode handling, and rationale block. Inserted right after `### Gemma-touching surfaces` and before `### Testing Impact Analysis`. |
| `docs/sessions/2026-05-06-copywriter-feature-pdf-report-exports.md` | (new file) | This log. |

No other files modified. No code written. No tests touched.

## Handoffs

- **`@genai-architect`** — owes a §10 review of the Gemma system prompt (`_SYSTEM`) at §4 "Gemma System Prompt and JSON Schema", per Claude Code Prompt step 2. Specifically: confirm the JSON schema, confirm the forbidden-vocabulary list is complete, confirm the 0-to-3 floor decision.
- **Implementation phase** — every string in §3.11 is paste-ready. The `_SYSTEM` Python literal is also paste-ready (escapes verified for the JSON-shape line).
- **`@test-writer`** — the new tests `test_risk_one_liner_handles_null_anchor` and a forbidden-term-leak test against Gemma output (mocked) should be added during the TESTING phase. Existing P0/P1 tests in §4 already cover the major paths (verdict line length, voice-marker tests, RPG-term regex).
- **`@fp-data-reviewer`** — should reconfirm the ROI-summary threshold bins (8% / 18% / 30%) match `roiLabelKey()` if `FinancesCard.tsx` drifts.

## Voice-guide compliance check

- [x] Cool. Confident. Data-honest. Coach, not cheerleader.
- [x] Locked vocabulary respected — stat codes appear ONLY in the page-2 glossary; everywhere else the body uses the human label (Earnings, ROI, AI Resilience, Growth, Brand Gravity).
- [x] No exclamation points anywhere.
- [x] No "oops," "your journey," "empower," "unlock," "transform."
- [x] Loss is contemplative, win is matter-of-fact register preserved (the high-risk verdict line is "the data flags multiple risk factors worth a closer look" — sober, not punishing).
- [x] Decision #4 RPG translation table enforced — no instance of `boss`, `gauntlet`, `Fight [X]`, `WIN/DRAW/LOSE`, `won/lost/draw`, `reroll`, `build` in any in-PDF copy or in any string Gemma is permitted to emit.
- [x] PDF register: Receipts (label : value) for data sections, Next Steps (verb-led) for questions. Confirmed.

## Notes for §11 follow-ups

- If the marketing/judging round wants the comparison PDF to include a comparison-level Gemma-generated summary, the `where_each_pulls_ahead` deterministic template is the right default — Gemma prose can be added as a follow-up spec; the deterministic line should remain even after Gemma is added (the model writes commentary, not the structural summary).
- If `match_quality` taxonomy gains a new value (e.g. `partial_no_bls`), `pdf_copy.data_coverage_caveat` needs a new branch and a new copy line. Not in scope here.
- The "Will I" / "Am I" voice markers in `ask_yourself` make `ask_yourself` strings translate awkwardly. Hackathon scope is English-only, but the next localization pass should reformulate as imperatives to round trip cleanly.
