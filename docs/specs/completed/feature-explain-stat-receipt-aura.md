# Feature: Explain-Stat Receipt — AURA (Additive `score_provenance` Schema Field)

## Claude Code Prompt

```
Read the spec at docs/specs/feature-explain-stat-receipt-aura.md in its
entirety. AURA's institution-level basis enum (three_term,
two_term_finance_only, two_term_no_endowment, one_term_marketing_only)
does not fit the per-component StatComponent shape — this was
anticipated by docs/specs/feature-explain-stat-receipt.md Decision 10
v1.2. This spec adds ONE additive root-level field to ExplainStatReceipt
(score_provenance: str | None) plus the per-stat dispatch wiring that
docs/specs/feature-explain-stat-receipt-roi-res-grw.md established for
ROI / RES / GRW.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §2 + §4: the additive
     score_provenance field on ExplainStatReceipt, its server-stamping
     contract (institution-level provenance, server-only — Gemma never
     writes it), and the renderer placement (subtle byline under the
     score). Architecturally minimal but the schema additive crosses
     the API contract boundary so it deserves a sign-off. Reviewer
     writes findings to §5.
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. IMPLEMENTATION
   - Implement the spec as written in §4. The frontend renderer change
     is one new visual element (subtle byline under the score) gated
     on payload.score_provenance being a populated string.
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly.
   - DURING coding: Update tests listed in "Authorized Test
     Modifications" only. Every other failure is STOP-and-escalate.
   - Log all work to §6.
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest).
   - BUILD ACCOUNTABILITY: max 3 attempts before escalating via §10.

3. TESTING
   - Invoke @test-writer to review the spec and add coverage from §4.
   - The Pydantic field default + sentinel-rejection contract, the
     server-stamping of score_provenance from _humanize_basis, the
     null-AURA branch, and the byline renderer are P0.

4. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests.

5. VERIFICATION
   - Invoke @fp-builder to run full build verification.

6. COMPLETION
   - Update Status to COMPLETE and check off §1 Success Criteria.
   - Generate report to reports/feature-explain-stat-receipt-aura-YYYY-MM-DD.md.

OUT OF SCOPE — REJECT as scope creep if a reviewer requests them:
  - Generalizing score_provenance to ROI / RES / GRW. AURA is the only
    stat with stat-level provenance today (per ERN spec Decision 10
    v1.2). The field stays Optional[str] at the root; the four other
    stats emit None.
  - Restructuring StatComponent to carry stat-level provenance. The ERN
    spec's @fp-architect explicitly flagged this as a category error.
    score_provenance is at the receipt root for that exact reason.
  - Surfacing aura_score_version in the receipt UI. The version is
    captured in logs and on the build object, but the receipt is a
    student-facing surface — version metadata adds noise without
    student value.
  - Adding a "why-mix paragraph" structurally different from the four
    percentile-rank stats. AURA's why_mix_paragraph follows the SKILL
    Step 5b AURA voice example structure (the "MAX rewards being
    elite at any one of three" framing) — it's structurally a why-mix
    paragraph, just with different content.
  - Removing the markdown-spike fallback for AURA. Same deferral as
    other stats — future cleanup spec.
  - Wiring score_provenance into the trace rail or telemetry. The
    field is server-stamped from existing data already in the build;
    no new tracing surface needed.
```

---

## Status: COMPLETE

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect approval |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-05-02 |
| Author | Jeff + Claude Code |
| Spec Version | 1.0 (DRAFT) |
| Last Updated | 2026-05-02 |
| Blocked By | `docs/specs/feature-explain-stat-receipt-roi-res-grw.md` (the registry refactor lands first; this spec adds AURA as the fifth registry entry alongside the additive schema field) |
| Related Specs | `docs/specs/feature-explain-stat-receipt.md` (ERN spec — required reading; Decision 10 v1.2 explicitly anticipates this additive field); `docs/specs/feature-explain-stat-receipt-roi-res-grw.md` (the registry refactor + sibling stat dispatches that this spec extends); `docs/specs/full-pipeline-eada.md` (the AURA data pipeline — `consumable.institution_aura` and the `aura_score_basis` enum's source); `docs/specs/pentagon-stat-reshape.md` (HMN→AURA cutover that introduced AURA on the pentagon) |
| Related References | `.claude/skills/pentagon-stat-explanation/SKILL.md` Step 5b (AURA voice authority — three signals, MAX-then-MEAN blend, basis enum); `docs/reference/stat-display-surfaces.md` (§1g AURA missing-data popover; §1i gains a new AURA entry); `backend/app/services/receipts.py:250-260` (`_humanize_basis` helper — reused as the basis label source per AskUserQuestion answer 4); `backend/app/services/stat_engine.py:70-101` (`_fetch_aura` — the source of the basis on the build); `src/mcp_server/futureproof_server.py:1197-1233` (`get_institution_aura` MCP tool — the chat-time data source) |

---

## §1 Feature Description

### Overview

Add a structured `<ExplainStatReceipt>` for AURA. AURA's institution-level provenance — captured by the `aura_score_basis` enum (`three_term`, `two_term_finance_only`, `two_term_no_endowment`, `one_term_marketing_only`) — does not fit the per-component `StatComponent.missing_reason` shape that the ERN spec authored. Instead, this spec adds **one additive root-level field** to `ExplainStatReceipt`: `score_provenance: str | None`. The field is **server-stamped only** (Gemma never writes it) and renders as a subtle byline under the score callout. The change is non-breaking: existing ERN/ROI/RES/GRW receipts emit `None` and the renderer suppresses the byline when null.

### Problem Statement

The ERN spec's Decision 10 v1.2 explicitly anticipated this gap:

> "AURA explicitly excluded — its institution-level provenance fields (`aura_score_basis`, `aura_score_version`) are stat-level metadata, not per-component data, and forcing them into `StatComponent.missing_reason` is a category error. The future AURA spec will add one **additive** root-level field (e.g., `score_provenance: str | None`) — additive, not breaking."

That gap is now load-bearing. The `feature-explain-stat-receipt-roi-res-grw.md` spec wires ROI/RES/GRW into the dispatch registry, but AURA stays unwired because it can't honestly render through the unmodified schema:

- AURA's "components" aren't components in the per-career sense — the same `aura_score` is stamped onto every `CareerOutcome` for a build because AURA is institution-level (one row in `consumable.institution_aura` per `unitid`, looked up via the existing `get_institution_aura` MCP tool).
- The receipt's pedagogical move is "we used these N pieces of data to compute your score." For AURA the right answer is "we used the basis we had available — for your school that was endowment + marketing + athletics; for some schools we only have marketing reach because they don't field NCAA teams; for ~10% of schools we have neither and the score is `—`."
- Stuffing the basis into `StatComponent.missing_reason` would be lying twice: it would put stat-level metadata in a per-component slot, AND `missing_reason` is for missing data, not for "what we used."

The fix is the additive field that the ERN spec already shaped: one optional root-level `score_provenance: str | None` that the server stamps from `_humanize_basis(career.aura_score_basis)`. Additive on the schema, additive on the renderer, no breaking changes for the four percentile-rank stats, no category error for AURA.

### Success Criteria

- [x] `ExplainStatReceipt` gains one new optional root-level field: `score_provenance: str | None = Field(default=None, max_length=200, description=...)` with `_reject_sentinel_passthrough` field validator. Existing payload-shape tests (ERN, ROI, RES, GRW) continue to pass — Gemma may emit the field as None or omit it entirely; the server stamps None for the four percentile-rank stats.
- [x] Clicking "✦ Explain this to me" on the AURA row of `BuildResultsScreen` opens the slide-in chat, fires `[explain-this:AURA]`, streams one tool-call event (`get_institution_aura`), and renders an `<ExplainStatReceipt>` with `stat_code="AURA"`, the AURA-color rail (purple per `STAT_COLORS.aura`), one component (the institution-level signal), and a subtle byline under the score reading (for example) *"based on endowment + marketing + athletics"*.
- [x] The `score_provenance` field is server-stamped in `_postprocess_aura_explain_receipt`. Whatever Gemma emits in the field is discarded. When `aura_score_basis` is not None, `score_provenance` is set from `_humanize_basis(career.aura_score_basis)` (e.g. `"endowment + marketing + athletics"`). When `aura_score_basis` is None (institution has a row in `institution_aura` but no scoreable basis — rare), the postprocessor sets `score_provenance = None` directly (it does NOT call `_humanize_basis`, which would return `"unknown basis"` — an unhelpful student-facing string). The renderer suppresses the byline when null.
- [x] When `build.career.stats.aura is None` (institution has no `consumable.institution_aura` row at all — ~10% of unitids), the `_postprocess_aura_explain_receipt` returns None at the score-null guard, and the dispatch falls through to a markdown-fallback appendix that explains "no AURA score for this school yet" in voice. The markdown fallback path uses the same cached-tool-log injection pattern as the other stats (no MCP re-fetch). **The trigger button on `BuildResultsScreen` should already be disabled or hidden in this state per the existing AURA missing-data treatment** (`stat-display-surfaces.md` §1g). The postprocessor's null-guard is belt-and-suspenders.
- [x] AURA's why-mix paragraph in the receipt follows the SKILL Step 5b AURA voice example: explains the MAX-then-MEAN blend, names the three signals (endowment, marketing, athletics), and uses the per-student normalization framing. The Pydantic `_reject_sentinel_passthrough` validator catches the placeholder echoes; `max_length=800` catches truncations.
- [x] The frontend renders the byline under the score callout in `<ExplainStatReceipt>` when `payload.score_provenance` is a populated string. The byline is `font-body` italic 13px `text-text-muted` with 6px top margin from the one-liner. When `payload.score_provenance` is null, the byline is suppressed (no whitespace gap, no placeholder).
- [x] The label allowlist for AURA's single component is `_AURA_LABEL_ALLOWLIST: dict[int, str] = {100: "your school's brand gravity"}`. Off-script Gemma labels are normalized via `_normalize_label` (the dict-by-weight matcher already used by ERN/ROI/GRW).
- [x] AURA's component renders with `value_pct=null` AND `missing_reason=null` — same shape as ROI/GRW. The renderer change from `feature-explain-stat-receipt-roi-res-grw.md` (suppress percentile-callout when both fields are null) handles this state without further work. The component carries `anchor_text` describing the institution-level signal (e.g., "Indiana University-Bloomington's per-student endowment, marketing reach, and athletic spending all rank in the top 30% nationally") and `anchor_dollars=null` (no dollar anchor — the underlying signals are per-student dollar amounts, but the receipt doesn't surface them line-by-line; the basis byline does that pedagogically).
- [x] `score` is server-stamped from `build.career.stats.aura` (per the ERN-spec server-owned-fields contract). `_postprocess_aura_explain_receipt` returns None when this is None.
- [x] Per-parse structured log records (`call_site="explain_aura_receipt"`) appear in `logs/gemma.jsonl` so the AURA parse-success rate is computable via the same filter pattern.
- [x] **Scoring scale table.** The receipt includes a `scoring_scale` field with 5 tiers (`_AURA_SCORING_SCALE`) that explain what each score range means in plain English a 16-year-old can read. The tiers are server-stamped (same pattern as ROI/RES/GRW). The frontend renders the table below the math line in the same position as the other stats.
- [x] **Evidence bullets with actual signal values.** The single component's `evidence_bullets` field is server-stamped from the `get_institution_aura` tool call response. Each bullet shows the actual per-student value AND a plain-English definition of what the signal means. Format: `"Endowment: $45,000/student — how much savings the school holds per student"`. Only signals present for the school's basis are included (1–3 bullets depending on coverage). When a signal value is null or the tool call failed, the bullet is omitted (not shown as "n/a").
- [x] **Signal definitions are 16-year-old-friendly.** The three signals are defined in constants that the postprocessor uses for evidence bullet construction: endowment = "how much savings the school holds per student"; marketing = "how much the school spends getting its name out there, per student"; athletics = "how much the school puts into sports programs per student". These definitions appear in the evidence bullets, NOT in the Gemma prompt (server-owned, not voice-owned).
- [x] **Math line shows continuous score.** The math line reads `"composite 0.72 → AURA score 8/10"` (the continuous score from `aura_score_continuous` on the tool response, to 2 decimal places). Falls back to the Decision 5 signals-arrow form when `aura_score_continuous` is unavailable.
- [x] `docs/reference/stat-display-surfaces.md` §1g (AURA missing-data popover) gains a note that the explain-this affordance is now wired for AURA when AURA is non-null and disabled/suppressed when null. §1i gains a new AURA entry following the existing entry shape. §1a (pentagon legend) and §1b (pentagon chart axis) update from "AURA gated on its separate spec" to "AURA wired (gated on stats.aura !== null)."
- [ ] Both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter` produce valid JSON receipts under temperature 0. Manual smoke verification on each backend before VERIFICATION marks green. *Deferred to human run, same as ERN/ROI/RES/GRW.*
- [x] No regressions to ERN/ROI/RES/GRW receipts. The `score_provenance: None` default means none of those four payloads' shapes change in any observable way (Pydantic v2 omits `None` defaults from JSON serialization unless explicitly configured otherwise — verify in §4 Service Changes the serialization behavior).

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | **Add `score_provenance: str \| None` as an additive root-level field on `ExplainStatReceipt`.** Default is `None`. Server-stamped, Gemma never writes it. Pydantic-validated as a string with `max_length=200` and the `_reject_sentinel_passthrough` validator (defensive — Gemma might emit a placeholder if it tries to fill the field despite the appendix instructions). | The ERN spec's Decision 10 v1.2 anticipated this exact field shape. AURA's institution-level basis enum is stat-level metadata, not per-component data. Putting it at the receipt root keeps the per-component shape clean for the four percentile-rank stats (ERN/ROI/RES/GRW emit `None` and the renderer suppresses the byline). The field is non-breaking by virtue of being optional with a `None` default — every existing test, fixture, and serialization continues to pass without modification. | (a) Stuff the basis into a single `StatComponent.missing_reason` for AURA. **Rejected** — `missing_reason` is for missing data; AURA's basis is "what we used," which is the opposite. The ERN spec's @fp-architect explicitly flagged this as a category error. (b) New optional sub-model `ScoreProvenance` carrying basis + version + a structured `signals_used: list[str]`. **Rejected** for v1.0 — heavier than the institution-level data warrants. The field can be promoted to a sub-model in a future spec if more stats grow stat-level provenance; the additive Optional[str] is the smallest viable shape today. (c) Stat-typed discriminated union (separate `AURAExplainReceipt` model). **Rejected** per the ERN spec's same Decision 10 — premature; the four percentile-rank stats genuinely share a structure and AURA differs by exactly one optional field. The discriminated-union refactor would multiply the test surface for one optional field's worth of difference. |
| 2 | **`score_provenance` is server-stamped from `_humanize_basis(career.aura_score_basis)` when `aura_score_basis` is not None, and set to `None` directly when `aura_score_basis` is None.** Uses the existing helper in `backend/app/services/receipts.py:250-260`. Not authored by Gemma and not derived in a new explainer-receipt-specific helper. **Null-basis guard:** `_humanize_basis(None)` returns `"unknown basis"`, which is not a useful student-facing string. The postprocessor checks `aura_score_basis is not None` before calling `_humanize_basis`; when None, it sets `score_provenance = None` so the renderer suppresses the byline. | The user's resume-task answer to AskUserQuestion #4 selected "Reuse existing _humanize_basis from receipts.py" as the recommendation, and that's correct: `_humanize_basis` already maps the four enum values to receipt-friendly strings used by `tiering_receipt` and other surfaces (`three_term` → "endowment + marketing + athletics", `two_term_finance_only` → "endowment + marketing (no athletics signal)", `two_term_no_endowment` → "marketing + athletics (no endowment signal)", `one_term_marketing_only` → "marketing reach only"). Reusing it means a single source of truth for the basis labels — no drift between the explainer-receipt and other receipt surfaces. | (a) New explainer-receipt-specific basis mapping with more conversational copy. **Rejected** — adds a second source of truth that can drift; the existing labels are already plain-English and battle-tested. (b) Hybrid: reuse `_humanize_basis` by default, allow override per call site. **Rejected** — adds complexity for marginal gain; only worth it if the existing labels prove to read wrong in the receipt context, which is a future spec's problem. (c) Have Gemma write `score_provenance` from the basis enum value passed in the appendix. **Rejected** — the basis is structured data the server already has; letting Gemma render it adds drift risk and serves no voice purpose. (d) Call `_humanize_basis(None)` and let `"unknown basis"` show as the byline. **Rejected** — `"based on unknown basis"` is confusing to a student; suppressing the byline is cleaner when we genuinely don't know the basis. |
| 3 | **`score_provenance` is rendered as a subtle byline under the score callout — `font-body` italic 13px `text-text-muted` with 6px top margin from the one-liner.** Suppressed entirely when null (no whitespace gap, no placeholder). | The user's resume-task AskUserQuestion #3 answer selected "Subtle byline under the score (Recommended)" as the rendering shape. The byline keeps the receipt's information architecture intact (eyebrow → score → one-liner → components → math → why-mix → sources) and adds one quiet annotation immediately below the headline rather than introducing a new section. The italic + muted treatment matches the missing-reason note treatment from the ERN spec — both are *meta* annotations about the data — so the visual vocabulary is reused. | (a) New "BASIS" eyebrow section between score callout and components. **Rejected** — adds a structural section for one stat; risks making the AURA receipt feel like a different shape than ERN/ROI/RES/GRW. (b) Inline pill near the score. **Rejected** — pills already carry source-citation duty in the receipt's footer; introducing a near-the-score pill muddies the information role of pills. (c) Bake the basis into Gemma's why-mix paragraph. **Rejected** — loses provenance authority (server should own this); means Gemma can drift on what we used. |
| 4 | **AURA's component is single (`weight_pct=100`) with `value_pct=null` AND `missing_reason=null` — same shape as ROI/GRW components.** The component carries `label="your school's brand gravity"`, `anchor_text` describes the institution-level signals plainly, and `anchor_dollars=null`. The `feature-explain-stat-receipt-roi-res-grw.md` renderer change (suppress percentile-callout when both fields are null) handles this state with no additional UI work. | The receipt's structural rule is "components describe what feeds the score." For AURA the answer is "one institution-level composite signal, basis-dependent." Splitting the basis into 1-3 components based on which signals were used would be brittle (the count would vary by school and by basis enum) and would invent visual variants for one stat that the four percentile-rank stats don't have. The single-component shape with the basis byline at the root is the cleanest fit: components answer "how many signals?" with "one composite," and the byline answers "which signals went into the composite?" with the basis label. | (a) Variable-length components keyed on basis enum (3 components for `three_term`, 2 for `two_term_finance_only`, etc.). **Rejected** — invents per-stat variants, complicates the renderer, makes the receipt visually unstable across schools. (b) Two components: "raw composite" + "rank within universe." **Rejected** — the formula isn't a two-piece blend like ERN; it's a single blended composite mapped to a 1-10 stretch. (c) Zero components (just score + math line). **Rejected** — `min_length=1` on `components` would reject; also breaks the receipt's information architecture. |
| 5 | **AURA's math line has its own form: `endowment + marketing + athletics → AURA score 8/10` (signals-arrow-score), NOT a weighted-blend or band form.** The math line names the basis signals (driven by `aura_score_basis`) followed by U+2192 and the score. When `score_provenance` is `"endowment + marketing + athletics"`, the math line reads `endowment + marketing + athletics → AURA score 8/10`. When the basis is `one_term_marketing_only`, the math line reads `marketing reach only → AURA score 4/10`. | The ERN spec's math-line treatment (`0.6 × A + 0.4 × B → score N/10`) only fits stats with a percentile-derived `raw` value. AURA's formula (per SKILL Step 5b) is `0.65 × MAX(signals) + 0.35 × MEAN(signals)` operating on percent-ranked signals — the arithmetic is real but the constants and signal counts vary by basis, which makes the ERN shape misleading. The signals-arrow-score form is honest about the mechanism without showing arithmetic that would make a student think AURA is computed differently than it is. | (a) Show the actual MAX-MEAN arithmetic (`0.65 × max(0.92, 0.88, 0.74) + 0.35 × mean(0.92, 0.88, 0.74) = 0.91 → AURA score 9/10`). **Rejected** — overshares mechanical details; the per-student percent-rank values aren't surfaced anywhere else in the receipt and would show up only here. (b) Skip the math line for AURA. **Rejected** — breaks the receipt's information architecture; the math line is the "show the receipts" beat. (c) Use ROI's bucket-form (`raw_aura → score N/10`). **Rejected** — there's no canonical raw value the student would recognize; the basis signals are the canonical-and-useful part. |
| 6 | **`_postprocess_aura_explain_receipt` registered into `_STAT_EXPLAIN_REGISTRY` as the fifth entry**, alongside ERN/ROI/RES/GRW (all four wired by `feature-explain-stat-receipt-roi-res-grw.md`). The registry's `Literal["ERN", "ROI", "RES", "GRW"]` key type widens to `Literal["ERN", "ROI", "RES", "GRW", "AURA"]`. | Mirrors the dispatch shape `feature-explain-stat-receipt-roi-res-grw.md` established. The registry refactor is the right place for AURA — adding a parallel `if explain_aura: ... elif ...` arm in `chat_ask` would defeat the registry's purpose. The `Literal` widening is type-safe and self-documenting. | (a) Add AURA outside the registry as a special case. **Rejected** — every reason that motivated the registry (cascade prevention, single dispatch source-of-truth) applies to AURA equally. (b) Make AURA's entry conditional on `stats.aura !== null` at registry-build time. **Rejected** — the registry is static; the conditional belongs in `chat_ask`'s pre-dispatch null-check (which mirrors the ERN spec's belt-and-suspenders guard). |
| 7 | **The trigger button on `BuildResultsScreen` for AURA is gated on `build.career.stats.aura !== null` at the React level**, suppressing the trigger when AURA is null (same as the disabled-when-null pattern the existing AURA missing-data popover at §1g establishes). The backend postprocessor still has its null-guard for defense-in-depth. | The ERN spec established the disabled-button pattern for null-score states. AURA is the stat where this is most likely to fire (~10% of unitids). Letting the user click an explain link only to see "no AURA score for this school yet" is a worse experience than not exposing the affordance — the AURA pentagon vertex already shows `—` and the popover already explains the missing-data state. | (a) Always show the trigger; let the markdown fallback explain the null state. **Rejected** — wastes Gemma latency on a null state that the build object already knows about. (b) Replace the trigger with a different "why is AURA missing?" link when null. **Rejected** for v1.0 — the existing popover at §1g already covers this surface. |
| 8 | **AURA's appendix re-uses the same JSON-mode + sentinel-passthrough + label-allowlist pattern from the four other stats.** The voice example inlined verbatim from SKILL Step 5b AURA section (three signals, MAX-then-MEAN blend, per-student normalization, "why brand gravity is on the pentagon at all" framing). The appendix explicitly tells Gemma NOT to write `score_provenance` (server-only). | The whole architectural value of the registry is that every stat's appendix is structurally the same — only the voice content and label allowlist diverge. AURA fits. The "don't write `score_provenance`" prohibition is one extra line in the appendix; the field is in the schema (so Pydantic accepts it) but the value is overwritten unconditionally by the postprocessor regardless of what Gemma emits. | (a) Allow Gemma to write `score_provenance` and validate against the basis enum. **Rejected** — server already has the basis from `_fetch_aura`; Gemma echoing it adds drift risk and serves no purpose. (b) Strip `score_provenance` from the JSON template entirely (don't show it to Gemma). **Rejected** — Pydantic `extra="forbid"` would reject any Gemma output that included the field; better to keep the field in the template with a placeholder and instruct Gemma to leave it as null/omit. **Update v1.0:** the chosen approach is to omit `score_provenance` from the JSON template entirely. Pydantic field default `None` means Gemma's omission is fine. The postprocessor stamps the value before Pydantic re-serializes for the wire. |
| 9 | **AURA gets a `_AURA_SCORING_SCALE` table (5 tiers) matching the transparency standard of ROI/RES/GRW.** The scale is derived from the linear P5/P95 rescale: the raw composite (0–1 percent-rank blend) is stretched [0.14, 0.94] → [1, 10]. Tiers are labeled so a 16-year-old understands what their score means relative to other schools. Server-stamped on `receipt.scoring_scale`. | The other four stats now all have scoring scales. Without one, AURA's receipt shows "endowment + marketing + athletics → 8/10" and the student has no idea why 8 and not 6. The scale answers "what does my score mean?" in the same visual position (below the math line) that ROI/RES/GRW use. Tiers are based on the linear rescale — the mapping is monotonic so five evenly-described bands cover the space. | (a) Skip the scale for AURA since it's "just a linear rescale." **Rejected** — the student doesn't know it's linear and can't infer the scale from one data point. The receipt's job is to show the receipts, not assume the reader knows the math. (b) Use the P5/P95 percentile labels directly ("top 5%", "top 25%"). **Rejected** — the score is per-student composite-rank, not a simple percentile of one variable; "top 5%" oversimplifies the MAX-MEAN blend and would be inaccurate for schools whose signals diverge. (c) 7 tiers mirroring GRW's 7. **Rejected** — AURA's linear scale doesn't have natural breakpoints like GRW's piecewise function; 5 tiers at 2-point intervals is cleaner. |
| 10 | **Server-stamped `evidence_bullets` on the AURA component show the actual per-student dollar values from the `get_institution_aura` tool call, with plain-English signal definitions a 16-year-old can parse.** Each bullet follows the format: `"Signal name: $value/student — what this actually means"`. Only signals present for the school's basis are shown (basis-dependent count: 3 for three_term, 2 for two_term_*, 1 for one_term_marketing_only). The postprocessor extracts values from the tool call log (same pattern as RES extracting O*NET tasks). | The transparency standard established by ERN/ROI/RES/GRW is: show the actual numbers behind the score, not just labels. ERN shows "$78,400 median salary"; ROI shows "$112,400 / $78,400 = 1.43"; GRW shows "+4.1%"; RES shows specific O*NET tasks. AURA currently names the signals but doesn't show the values — a student sees "endowment + marketing + athletics" but not how big the endowment actually is. Showing the dollar amounts with a plain-English definition ("the school's savings account per student") makes the receipt genuinely transparent. The values are already on the `get_institution_aura` MCP response (`endowment_per_fte`, `marketing_ratio`, `athletic_spend_per_fte`). | (a) Show raw values without definitions. **Rejected** — "$45,000 endowment per FTE" means nothing to a 16-year-old. The definition IS the transparency. (b) Show percentile ranks instead of dollar values. **Rejected** — rp_* values are NOT stored in the consumable table or returned by the MCP tool; they're transient during the gold transform. Adding them would be a pipeline change (out of scope). (c) Let Gemma write the evidence bullets. **Rejected** — Gemma can hallucinate dollar values; server-stamping from the trusted tool call result is the only safe path for numeric evidence. (d) Show values in the anchor_text instead of evidence_bullets. **Rejected** — anchor_text is one string; multiple signals with definitions need the bulleted list. evidence_bullets (max 6) is the exact field the RES spec uses for this purpose. |
| 11 | **AURA's math line shows the continuous score for transparency: `"composite 0.72 → AURA score 8/10"`.** The `aura_score_continuous` value is extracted from the `get_institution_aura` tool call response and rendered to 2 decimal places. When the continuous score is unavailable (defensive), falls back to the signals-arrow-score form from Decision 5. | The math line's job is to show the student exactly how their number was derived. "endowment + marketing + athletics → 8/10" names what went in but doesn't show the actual computed value that got rounded. Showing "composite 0.72 → 8/10" matches the transparency level of ROI ("$112,400 / $78,400 = 1.43 → 4/10") and GRW ("+4.1% → 6/10") — the student can see the continuous value and understand why rounding landed on their integer score. The continuous score IS on the MCP tool response (`aura_score_continuous`). | (a) Keep the signals-only form ("endowment + marketing + athletics → 8/10"). **Rejected** — this was acceptable before the transparency standard was established across the other stats, but it's now inconsistent: the student learns ROI's exact ratio but not AURA's exact composite. (b) Show the full MAX-MEAN arithmetic. **Rejected** — same rejection as Decision 5; percent-rank values aren't available at runtime and the formula is noise without them. (c) Show only the integer score. **Rejected** — removes the "show your work" beat entirely. |

### Constraints

- **`score_provenance` is server-stamped only.** Gemma never writes it; the postprocessor overrides whatever Gemma might emit. Same boundary discipline as `score`, `math_line`, and per-component `value_pct` / `anchor_dollars` / `missing_reason` from the ERN spec.
- **No data-pipeline changes.** `consumable.institution_aura` already carries `aura_score_basis`. The `get_institution_aura` MCP tool already returns it. `_fetch_aura` in `stat_engine.py` already plumbs it into the build's `CareerOutcome.aura_score_basis` field.
- **No new MCP tools.** `get_institution_aura` is already in the `_TOOLS` allowlist for chat-time calls (added by the institution-aura pipeline spec).
- **No formula changes.** This spec describes AURA's existing formula for the explainer voice; it does not modify `_fetch_aura`, the institution_aura table schema, or the AURA scoring logic.
- **`score_provenance` adds an additive root-level field — non-breaking for existing payloads.** ERN/ROI/RES/GRW receipts emit `None`; the renderer suppresses the byline when null. Pydantic v2's default-omission behavior must be verified at implementation time (specifically whether `score_provenance: str | None = None` is omitted from JSON output by default — `model_dump(exclude_none=True)` may or may not be in play; the wire payload should not gain a new noisy `null` field for the four other stats).
- **Voice authority remains the SKILL.** AURA's appendix inlines the SKILL Step 5b AURA worked example verbatim. Schema and voice stay decoupled.
- **JSON-mode synthesis-turn-only scoping (Decision 15 of the ERN spec) applies to AURA dispatch.** No new gemma_client work — same kwarg, same per-backend translation.

### Out of Scope

| Item | Park as |
|------|---------|
| Generalizing `score_provenance` to ROI/RES/GRW | Out — AURA is the only stat with stat-level provenance today |
| Restructuring `StatComponent` to carry stat-level provenance | Out — category error per ERN spec @fp-architect |
| Surfacing `aura_score_version` in the receipt UI | Out — captured in logs and on the build, but adds noise to the student surface |
| New `ScoreProvenance` Pydantic sub-model wrapping basis + version + signals | Future spec if more stats grow stat-level provenance; v1.0 stays at Optional[str] |
| Showing the actual MAX-MEAN arithmetic in the math line | Out — mechanical without pedagogical gain (Decision 5); percent-rank values aren't available at runtime |
| Stat-typed discriminated union | Out — premature; one optional field doesn't justify the refactor |
| Removing the markdown-spike fallback for AURA | Future cleanup spec after stable production usage |
| Wiring `score_provenance` into the trace rail or telemetry | Out — server-stamped from existing build data, no new tracing surface |
| Adding rp_* (percent-rank) columns to the consumable table / MCP response | Pipeline change out of scope; would require schema evolution spec |

---

## §3 UI/UX Design

> **MOSTLY INHERITED — one new visual element:** the `score_provenance` byline under the score callout.

### One renderer change in `<ExplainStatReceipt>`

Inside the score-callout area (the `<header>` element that holds the eyebrow + score row + one-liner), add a new row below the one-liner when `payload.score_provenance` is a populated string:

```
┌─────────────────────────────────────────────────────────────┐
│  BRAND GRAVITY                                       8 /10 │
│                                                              │
│  How much weight your school's name carries — for          │
│  networking, alumni access, recruiter shortlists, and      │
│  graduate-school admissions.                                │
│                                                              │
│  based on endowment + marketing + athletics              ←  ← new byline
└─────────────────────────────────────────────────────────────┘
```

| Element | Token / spec |
|---|---|
| Container | `<p data-testid="receipt-score-provenance">` inside the score `<header>`. Sits 6px below the one-liner. |
| Typography | `font-body` weight 400, size 13px, line-height 1.4, `text-text-muted`, `font-style: italic`. |
| Prefix | The literal word `"based on "` (lowercase, italic, same color). The byline content from `payload.score_provenance` follows. |
| Width | No explicit max; will wrap naturally at the card width. The existing `_humanize_basis` outputs are short enough that wrap is rare. |
| Suppression | When `payload.score_provenance` is null or undefined, the byline element is not rendered at all (no empty paragraph, no whitespace gap). The 6px top-margin is on the byline element itself, so suppression collapses cleanly. |
| `aria-label` | `Score provenance: based on {score_provenance}`. Read after the one-liner to a screen reader. |

The italic-and-muted treatment is the same vocabulary the missing-reason note uses (per ERN spec §3 — "italics here are the right move because the line is *meta* — it's about the data, not part of it"). Reusing the visual vocabulary for stat-level provenance keeps the receipt's information register coherent.

### What is NOT changing

- The card chrome (background, border, left rail in AURA color, padding, shadow, radius) — unchanged. The AURA stat color is purple per `STAT_COLORS.aura` (`var(--color-stat-aura)`).
- The components row treatment — unchanged. AURA's single component renders with `value_pct=null` AND `missing_reason=null`, which the `feature-explain-stat-receipt-roi-res-grw.md` renderer change handles (suppress percentile-callout glyph; show only `anchor_text` below the explainer).
- The math-line inset card — unchanged. AURA's math line uses the signals-arrow-score form (Decision 5); the renderer doesn't inspect the expression structure.
- The why-mix paragraph treatment — unchanged. AURA's why-mix follows the SKILL Step 5b AURA voice (three signals + per-student framing + "why brand gravity is on the pentagon at all"). Pydantic `max_length=800` catches truncation; `_reject_sentinel_passthrough` catches placeholder echoes.
- Sources pills — unchanged. AURA's sources are IPEDS Finance and EADA (per SKILL Step 5b "Where the data comes from"). The pill name short-form mapping in the renderer gains two entries: `"Integrated Postsecondary Education Data System (IPEDS)" → "IPEDS Finance"`, `"Equity in Athletics Disclosure Act (EADA)" → "EADA"` (or whatever the existing tiering-receipt source labels resolve to — verify in implementation against `receipts.py`).
- Loading skeleton — unchanged. The skeleton frame is shape-only; the byline is filled in when the realized receipt arrives.

### Mockups (AURA-specific states)

#### AURA — three_term basis (most common, ~70% of scoreable institutions)

```
┌─[receipt card, bg-bp-raised, 3px purple left rail]─────────────────┐
┃ BRAND GRAVITY                                              8 /10  │
┃                                                                   │
┃ How much weight your school's name carries — for networking,      │
┃ alumni access, recruiter shortlists, and graduate-school          │
┃ admissions.                                                       │
┃                                                                   │
┃ based on endowment + marketing + athletics                       │  ← byline
┃                                                                   │
┃ ┌─────┐  Your school's brand gravity                             │
┃ │ 100%│  Indiana University-Bloomington's per-student endowment, │
┃ └─────┘  marketing reach, and athletic spending all rank in the  │
┃          top 30% nationally — the school's institutional weight  │
┃          is unusually consistent across all three signals.       │
┃                                                                   │
┃          • Endowment: $45,230/student — how much savings the     │  ← evidence bullets
┃            school holds per student                                │     (server-stamped)
┃          • Marketing: 0.118 ratio — how much the school spends   │
┃            getting its name out there, per student                 │
┃          • Athletics: $8,420/student — how much the school puts   │
┃            into sports programs per student                        │
┃                                                                   │
┃ ╭─[bg-bp-mid inset]──────────────────────────────────────────╮   │
┃ │  composite 0.72  →  AURA score 8/10                         │   │  ← continuous score
┃ ╰────────────────────────────────────────────────────────────╯   │
┃                                                                   │
┃ ╭─[scoring scale, active tier highlighted]────────────────────╮   │
┃ │  Elite brand      9 – 10                                    │   │
┃ │ ▸Strong brand     7 – 8  ◀ you are here                    │   │  ← scoring scale
┃ │  Solid brand      5 – 6                                    │   │
┃ │  Modest brand     3 – 4                                    │   │
┃ │  Low profile      1 – 2                                    │   │
┃ ╰────────────────────────────────────────────────────────────╯   │
┃                                                                   │
┃ WHY WE MIX THESE SIGNALS                                          │
┃                                                                   │
┃ Most college tools pretend prestige doesn't matter — but it      │
┃ absolutely does for networking, alumni access, recruiter         │
┃ shortlists, and graduate-school admissions. Three signals,       │
┃ measured per student so big and small schools are on the same    │
┃ scale: endowment per full-time student (how much money the       │
┃ school has invested per kid), marketing reach per student, and   │
┃ athletic spending per student. The MAX rewards being elite at    │
┃ any one (Stanford has the endowment; Notre Dame has the          │
┃ football); the MEAN keeps it balanced.                           │
┃                                                                   │
┃ ─────────────────────────────────────────────────────────────    │
┃ SOURCES                                                          │
┃ [ Endowment + marketing · IPEDS Finance ]  [ Athletics · EADA ]  │
└──────────────────────────────────────────────────────────────────┘
```

#### AURA — one_term_marketing_only basis

```
┃ BRAND GRAVITY                                              4 /10  │
┃ ...                                                              │
┃ based on marketing reach only                                    │  ← byline reflects basis
┃ ...                                                              │
┃ ┌─────┐  Your school's brand gravity                             │
┃ │ 100%│  Briarcliffe College's only available institutional      │
┃ └─────┘  weight signal is marketing reach per student — neither  │
┃          IPEDS Finance endowment data nor EADA athletics         │
┃          coverage is reported for this school.                   │
┃                                                                   │
┃          • Marketing: 0.042 ratio — how much the school spends   │  ← only 1 bullet
┃            getting its name out there, per student                 │
┃                                                                   │
┃ ╭─[bg-bp-mid inset]──────────────────────────────────────────╮   │
┃ │  composite 0.31  →  AURA score 4/10                         │   │
┃ ╰────────────────────────────────────────────────────────────╯   │
┃                                                                   │
┃ ╭─[scoring scale, active tier highlighted]────────────────────╮   │
┃ │  Elite brand      9 – 10                                    │   │
┃ │  Strong brand     7 – 8                                    │   │
┃ │  Solid brand      5 – 6                                    │   │
┃ │ ▸Modest brand     3 – 4  ◀ you are here                    │   │
┃ │  Low profile      1 – 2                                    │   │
┃ ╰────────────────────────────────────────────────────────────╯   │
```

#### AURA — null score (institution has no row in `consumable.institution_aura`)

The trigger button is suppressed at the `BuildResultsScreen` level (Decision 7). If somehow the dispatch is invoked with `stats.aura === null` (e.g., a direct API call), the postprocessor returns None at the score-null guard, and the markdown-fallback path renders a single-bubble "no AURA data for this school yet" message in voice. This state is the ERN spec's Decision 7 belt-and-suspenders guard generalized to AURA. No new visual treatment.

### Stat-display surface index updates

`docs/reference/stat-display-surfaces.md` gains:

- §1a (pentagon legend): update from "AURA gated on its separate spec" to "AURA wired (the trigger is suppressed when `stats.aura === null`, per Decision 7 of `feature-explain-stat-receipt-aura.md`)."
- §1b (pentagon chart axis): same update.
- §1g (AURA missing-data popover): note that the explain-this affordance is wired for non-null AURA. The existing popover continues to handle the null-AURA case via "Ask Gemma about this" → free-form prose explainer about why the school has no AURA score (a different intent than the structured receipt).
- §1i: a new sub-entry (`§1i.aura`) following the existing ERN entry shape: file, when-it-shows, what-user-sees, affordance, spec, schema. Notes the byline as the AURA-specific visual element.

---

## §4 Technical Specification

### Architecture Overview

This spec extends the dispatch registry that `feature-explain-stat-receipt-roi-res-grw.md` established with one additional entry (AURA) and adds one additive root-level field (`score_provenance`) to `ExplainStatReceipt`. The change is small but crosses the API contract boundary, which is why the prompt weight is Standard with an ARCH REVIEW step.

Five integration points:

1. **`backend/app/models/api.py`** — `ExplainStatReceipt` gains `score_provenance: str | None = Field(default=None, max_length=200, description=..., ...)` plus the `_reject_sentinel_passthrough` field validator. Verify Pydantic v2 serialization behavior for `None` defaults — if `model_dump_json()` includes `"score_provenance": null` in every wire payload (even ERN/ROI/RES/GRW), assess whether to add `Field(..., exclude_none=True)`-equivalent semantics or accept the noisy field. The Zod schema on the frontend gains the matching optional field.
2. **`backend/app/services/ask_gemma.py`** — Add `_AURA_RECEIPT_JSON_TEMPLATE` (filled-in JSON example with `__FILL_IN__` sentinels; `score_provenance` is OMITTED from the template per Decision 8 v1.0 update — Gemma is told NOT to write the field), `_AURA_LABEL_ALLOWLIST: dict[int, str] = {100: "your school's brand gravity"}`, `_AURA_SCORING_SCALE` (5-tier list of `ScoringTier` objects), `_AURA_SIGNAL_DEFINITIONS` (plain-English descriptions for each signal), `_AURA_MARKDOWN_FALLBACK_APPENDIX`, and `_postprocess_aura_explain_receipt`. Register AURA into `_STAT_EXPLAIN_REGISTRY` as the fifth entry. Widen the registry's `Literal` key type to include AURA. Add `_render_math_line_aura(*, aura_score_continuous: float | None, build_score: int, score_max: int) -> str` that produces the continuous-score form (`"composite 0.72 → AURA score 8/10"`), falling back to the signals-arrow form when continuous is unavailable.
3. **`_postprocess_aura_explain_receipt`** — Mirrors the 10-step pipeline established by the ERN postprocessor with AURA-specific variations: stat_code asserted == "AURA"; null-guard on `build.career.stats.aura`; server-stamps `score_provenance` from `_humanize_basis(career.aura_score_basis)`; server-stamps the single component's `value_pct=None`, `anchor_dollars=None`, `missing_reason=None`; **extracts actual signal values from the `get_institution_aura` tool call log** (`endowment_per_fte`, `marketing_ratio`, `athletic_spend_per_fte`) and builds `evidence_bullets` with plain-English definitions (only for signals present per the school's basis); server-builds `math_line` via `_render_math_line_aura` using `aura_score_continuous` from the tool response; server-stamps `scoring_scale = _AURA_SCORING_SCALE`; logs structured record with `call_site="explain_aura_receipt"`.
4. **`frontend/src/types/chat.ts`** (or wherever the Zod schema lives) — Add `score_provenance: z.string().max(200).nullable().optional()` to the receipt schema. The TypeScript type widens automatically via Zod inference.
5. **`frontend/src/components/menu/ExplainStatReceipt.tsx`** — One renderer change: inside the score `<header>`, render a `<p data-testid="receipt-score-provenance">` element with the byline when `payload.score_provenance` is a populated string. Suppression on null. The element reads `<i>based on {payload.score_provenance}</i>`. Plus: AURA receipt rendering (`payload.stat_code === "AURA"`) is otherwise indistinguishable from ROI/GRW (single component with value_pct=null, no percentile callout, anchor_text only).
6. **`frontend/src/screens/BuildResultsScreen.tsx`** — Add an "✦ Explain this to me" trigger to the AURA legend row, gated on `build.career.stats.aura !== null` (Decision 7). Same dispatch pattern as other stats: sentinel `[explain-this:AURA]`.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/models/api.py` | Modify | Add `score_provenance: str \| None = Field(default=None, max_length=200, description="Server-stamped institution-level provenance for stat-level metadata that doesn't fit the per-component shape. AURA-only in v1.0; emits None for ERN/ROI/RES/GRW. Server-stamped from _humanize_basis(career.aura_score_basis); never written by Gemma.")` to `ExplainStatReceipt`. Add `_reject_sentinel_score_provenance = field_validator("score_provenance")(_reject_sentinel_passthrough)` (the validator already handles None gracefully via early-return on non-string input — verify this in implementation; if not, wrap in `if value is None: return value`). |
| `backend/app/services/ask_gemma.py` | Modify | (a) Add `_AURA_RECEIPT_JSON_TEMPLATE`, `_AURA_LABEL_ALLOWLIST`, `_AURA_MARKDOWN_FALLBACK_APPENDIX` constants. (b) Add `_postprocess_aura_explain_receipt` (the 10-step pipeline, AURA-specific variations). (c) Add `_render_math_line_aura(*, score_provenance: str \| None, build_score: int, score_max: int) -> str`. (d) Register AURA in `_STAT_EXPLAIN_REGISTRY` as the fifth entry. (e) Widen the registry key Literal to include "AURA". (f) The sentinel-detection block in `chat_ask` / `chat_ask_stream` already handles arbitrary stat codes via `_STAT_EXPLAIN_REGISTRY` lookup (per `feature-explain-stat-receipt-roi-res-grw.md`); no further wiring needed. |
| `backend/tests/services/test_ask_gemma_explain_receipt.py` | Modify | Add `TestPostprocessAURAExplainReceipt` test class mirroring the existing per-stat test classes. Cover: happy path (three_term basis), happy path (one_term_marketing_only basis), score-from-build override, null-AURA returns None, basis-stamping from `_humanize_basis`, math-line construction (signals-arrow-score), Pydantic-validation failures, sentinel passthrough on prose fields AND on `score_provenance` (Gemma might emit `"__FILL_IN__"` if it gets clever), label normalization, structured log records on success and failure, JSON extraction edge cases. |
| `backend/tests/services/test_ask_gemma.py` | Modify | (a) Remove the `test_aura_explain_sentinel_not_yet_registered` test that the previous spec added (it's now obsolete because AURA IS registered after this spec). (b) Add `test_chat_ask_aura_explain_dispatches_via_registry` and `test_chat_ask_aura_explain_fallback_uses_cached_tool_log` mirroring the per-stat tests in the previous spec. (c) Add `test_chat_ask_aura_explain_returns_none_when_aura_score_null` — when `build.career.stats.aura is None`, postprocessor returns None and fallback renders the markdown "no AURA data" voice. |
| `backend/tests/models/test_api.py` (or wherever `ExplainStatReceipt` is unit-tested) | Modify | Add `test_explain_stat_receipt_score_provenance_default_none` (default value is None for legacy ERN/ROI/RES/GRW payloads); `test_explain_stat_receipt_score_provenance_max_length` (Pydantic rejects strings > 200 chars); `test_explain_stat_receipt_score_provenance_rejects_sentinel` (the field validator catches placeholder echoes); `test_explain_stat_receipt_serialization_omits_score_provenance_when_null` (verify wire-payload behavior — depending on the answer to the §4 Architecture Overview question, this test either asserts `"score_provenance"` is absent from the JSON or asserts it serializes as `"score_provenance": null`). |
| `frontend/src/types/chat.ts` (or the Zod schema location) | Modify | Add `score_provenance: z.string().max(200).nullable().optional()` to the `ExplainStatReceipt` Zod schema. The TypeScript type widens via Zod inference. |
| `frontend/src/components/menu/ExplainStatReceipt.tsx` | Modify | Inside the score `<header>`, after the one-liner `<p>`, conditionally render the byline `<p data-testid="receipt-score-provenance">based on {payload.score_provenance}</p>` (italic, 13px, text-text-muted, 6px top margin) when `payload.score_provenance` is a non-empty string. Suppress when null/undefined/empty. |
| `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | Modify | Add: `test_renders_score_provenance_byline_when_present` (AURA fixture with score_provenance populated → byline renders); `test_suppresses_byline_when_null` (ERN fixture → byline element absent); `test_renders_aura_receipt_full_shape` (AURA payload renders single component without percentile callout, byline visible, math line in signals-arrow-score form). |
| `frontend/src/screens/BuildResultsScreen.tsx` | Modify | Add "✦ Explain this to me" trigger to the AURA legend row. Gated on `build.career.stats.aura !== null` (Decision 7). Sentinel `[explain-this:AURA]`. Reuses the existing `handleAskStat` pattern. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Modify | Add: `test_aura_explain_link_visible_when_aura_present` (clicking fires `[explain-this:AURA]`); `test_aura_explain_link_suppressed_when_aura_null` (link element absent or disabled). |
| `docs/reference/stat-display-surfaces.md` | Modify | Update §1a / §1b notes to "AURA wired (gated on stats.aura !== null)." Update §1g to note explain-this is wired for non-null AURA. Add §1i.aura entry following the ERN entry shape, calling out the byline and the signals-arrow-score math line as AURA-specific visual elements. |
| `.claude/skills/pentagon-stat-explanation/SKILL.md` | Modify | Add a line under "Companion reference" pointing to the AURA appendix template in `ask_gemma.py` as the rendering authority for AURA receipts. |

### Data Model Changes

**One additive root-level field on `ExplainStatReceipt`:**

```python
class ExplainStatReceipt(BaseModel):
    # ... existing fields unchanged: kind, stat_code, stat_name, score,
    # score_max, one_liner, components, math_line, sources, why_mix_paragraph

    score_provenance: str | None = Field(
        default=None,
        max_length=200,
        description=(
            "Server-stamped institution-level provenance for stat-level "
            "metadata that doesn't fit the per-component StatComponent "
            "shape. AURA-only in v1.0 (server-stamped from "
            "_humanize_basis(career.aura_score_basis), e.g. 'endowment + "
            "marketing + athletics'); ERN/ROI/RES/GRW emit None. The "
            "renderer surfaces this as a subtle byline under the score "
            "callout when populated; suppresses entirely when None. "
            "Gemma never writes this field — the postprocessor "
            "overwrites whatever Gemma might emit. The field is "
            "additive to the v1.0 schema and non-breaking: existing "
            "payloads emit None and the renderer preserves their visual "
            "shape exactly."
        ),
    )

    # Sentinel-passthrough guard — defensive, in case Gemma echoes a
    # placeholder despite the appendix instructions to leave the field
    # alone. The validator returns the value unchanged for None inputs;
    # implementation note: if _reject_sentinel_passthrough doesn't
    # short-circuit on None, wrap in a None-check before calling.
    _reject_sentinel_score_provenance = field_validator("score_provenance")(
        _reject_sentinel_passthrough
    )
```

**Pydantic-v2 serialization caveat.** The wire payload for ERN/ROI/RES/GRW receipts must NOT gain a noisy `"score_provenance": null` field if at all avoidable. Two options to verify at implementation:

1. Pydantic v2 `model_dump_json()` includes `None` defaults by default. To omit, the field needs `exclude_none=True` set on the dump call OR `Field(..., exclude_unset=True)`-style configuration. The cleanest path is to call `model_dump_json(exclude_none=True)` at the FastAPI serialization boundary if it isn't already, but verify this doesn't unintentionally drop other legitimate `None` defaults (e.g., `StatComponent.value_pct=None` for ROI's by-design null).
2. Alternative: accept the noisy `"score_provenance": null` in the wire payload. Frontend Zod schema declares the field as `.nullable().optional()`, so parsing is unaffected. Wire byte cost is negligible (~30 bytes per receipt).

**Decision deferred to implementation.** Whichever path is chosen, document in §6 with rationale and add the appropriate test (either "ERN payload's wire JSON does not contain score_provenance key" or "ERN payload's wire JSON contains score_provenance: null"). The frontend behavior is the same either way: byline suppressed when value is null/undefined/missing.

The Zod mirror on the frontend:

```typescript
export const explainStatReceiptSchema = z.object({
  // ... existing fields unchanged
  score_provenance: z.string().max(200).nullable().optional(),
});
```

`StatComponent` and `ReceiptSource` are unchanged. `AskResponse.response` and `TraceFinalText.response` are unchanged. No Iceberg or DuckDB changes. No new MCP tool surfaces.

### Service Changes

New helpers and constants in `backend/app/services/ask_gemma.py`:

```python
# AURA: single 100% institution-level component (Decision 4).
_AURA_LABEL_ALLOWLIST: dict[int, str] = {
    100: "your school's brand gravity",
}

# Scoring scale — 5 tiers matching the linear P5/P95 rescale (Decision 9).
_AURA_SCORING_SCALE: list[ScoringTier] = [
    ScoringTier(label="Elite brand", range="9 – 10", score="9 – 10"),
    ScoringTier(label="Strong brand", range="7 – 8", score="7 – 8"),
    ScoringTier(label="Solid brand", range="5 – 6", score="5 – 6"),
    ScoringTier(label="Modest brand", range="3 – 4", score="3 – 4"),
    ScoringTier(label="Low profile", range="1 – 2", score="1 – 2"),
]

# Plain-English signal definitions for evidence bullets (Decision 10).
# A 16-year-old should be able to understand each of these without
# googling. The key is the field name from the get_institution_aura
# MCP tool response; the value is the student-facing description.
_AURA_SIGNAL_DEFINITIONS: dict[str, tuple[str, str]] = {
    # (display_name, plain_english_definition)
    "endowment_per_fte": (
        "Endowment",
        "how much savings the school holds per student",
    ),
    "marketing_ratio": (
        "Marketing",
        "how much the school spends getting its name out there, per student",
    ),
    "athletic_spend_per_fte": (
        "Athletics",
        "how much the school puts into sports programs per student",
    ),
}

# Which signals are present for each basis value. Used to determine
# which evidence bullets to render (only signals the school actually
# has data for).
_AURA_BASIS_SIGNALS: dict[str, list[str]] = {
    "three_term": ["endowment_per_fte", "marketing_ratio", "athletic_spend_per_fte"],
    "two_term_finance_only": ["endowment_per_fte", "marketing_ratio"],
    "two_term_no_endowment": ["marketing_ratio", "athletic_spend_per_fte"],
    "one_term_marketing_only": ["marketing_ratio"],
}


# Per-stat dispatch config registered into _STAT_EXPLAIN_REGISTRY.
# This widens the registry from the four-stat shape established by
# feature-explain-stat-receipt-roi-res-grw.md to the full five.
_STAT_EXPLAIN_REGISTRY["AURA"] = _StatExplainConfig(
    stat_code="AURA",
    sentinel="[explain-this:AURA]",
    appendix_template=_AURA_RECEIPT_JSON_TEMPLATE,
    label_allowlist=_AURA_LABEL_ALLOWLIST,
    postprocessor=_postprocess_aura_explain_receipt,
    markdown_fallback_appendix=_AURA_MARKDOWN_FALLBACK_APPENDIX,
    log_call_site="explain_aura_receipt",
)


def _extract_aura_tool_data(
    tool_call_log: list["gemma_client.ToolCallTurn"],
) -> dict | None:
    """Pull the get_institution_aura tool result from the log.

    Returns the `data` dict from the tool response, or None if the
    tool wasn't called or returned an error/empty result.
    """
    for turn in tool_call_log:
        if turn.error or turn.tool_name != "get_institution_aura":
            continue
        result_json = turn.tool_result_full or turn.tool_result_preview
        try:
            preview = json.loads(result_json)
        except (json.JSONDecodeError, ValueError):
            continue
        row = preview.get("data") if isinstance(preview, dict) else None
        if isinstance(row, dict):
            return row
    return None


def _build_aura_evidence_bullets(
    tool_data: dict | None,
    basis: str | None,
) -> list[str] | None:
    """Build evidence bullets from actual signal values + definitions.

    Returns None when tool_data is unavailable or basis is unknown.
    Each bullet: "Signal: $value/student — plain-english definition"
    Only signals present for this school's basis are shown.
    """
    if tool_data is None or basis is None:
        return None
    signal_keys = _AURA_BASIS_SIGNALS.get(basis)
    if signal_keys is None:
        return None

    bullets: list[str] = []
    for key in signal_keys:
        defn = _AURA_SIGNAL_DEFINITIONS.get(key)
        if defn is None:
            continue
        display_name, description = defn
        value = tool_data.get(key)
        if value is None:
            continue
        # Format: dollar amounts for endowment/athletics, ratio for marketing
        if key == "marketing_ratio":
            val_str = f"{value:.3f} ratio"
        else:
            val_str = f"${int(value):,}/student"
        bullets.append(f"{display_name}: {val_str} — {description}")

    return bullets if bullets else None


async def _postprocess_aura_explain_receipt(
    raw: str,
    build: "Build",
    tool_call_log: list["gemma_client.ToolCallTurn"],
    backend: str,
) -> "ExplainStatReceipt | None":
    """AURA-specific 10-step pipeline.

    Per-stat differences from ERN:
      - stat_code asserted == "AURA". Mismatch -> None.
      - Null-guard: if build.career.stats.aura is None -> None
        (belt-and-suspenders; the trigger button is suppressed in this
        case at the BuildResultsScreen level per Decision 7).
      - score server-stamped from build.career.stats.aura.
      - Single component (length-1):
          weight_pct=100 (per the canonical _AURA_LABEL_ALLOWLIST)
          label normalized via _normalize_label by weight=100
          value_pct = None (institution-level; no per-career percentile)
          anchor_dollars = None
          missing_reason = None when AURA is non-null
          anchor_text — voice-owned by Gemma; describes the institution-
              level signals plainly.
          evidence_bullets — SERVER-STAMPED from get_institution_aura
              tool call response (Decision 10). Each bullet shows the
              actual per-student value + a plain-English definition.
              Only signals present for the school's basis are shown.
      - score_provenance server-stamped from _humanize_basis.
      - math_line shows continuous score: "composite 0.72 → AURA score 8/10"
        (Decision 11). Falls back to signals-arrow form when continuous
        score is unavailable.
      - scoring_scale = _AURA_SCORING_SCALE (Decision 9).
      - log_call_site = "explain_aura_receipt".

    Data source note: The server-stamped fields use BOTH the Build object
    (aura score, aura_score_basis) AND the get_institution_aura MCP tool
    response (aura_score_continuous for the math line, and actual signal
    values for evidence bullets). This makes AURA's postprocessor pattern
    more like RES (which also reads from the tool log) than ERN.

    Server-controlled fields (always rebuilt; Gemma's emitted values
    are discarded regardless):
      - score, score_max (from build.career.stats.aura)
      - score_provenance (from build.career.aura_score_basis via
        _humanize_basis, or None when basis is None)
      - math_line (from aura_score_continuous in tool response + build score)
      - scoring_scale (= _AURA_SCORING_SCALE)
      - components[0].value_pct (=None always for AURA)
      - components[0].anchor_dollars (=None always for AURA)
      - components[0].missing_reason (=None always for AURA when reached)
      - components[0].evidence_bullets (from tool response signal values
        + _AURA_SIGNAL_DEFINITIONS; basis-dependent count)

    Gemma-controlled fields (kept as-emitted after Pydantic validation):
      - kind (always "receipt")
      - stat_code (validated == "AURA", discarded if not)
      - stat_name
      - one_liner
      - components[0].weight_pct (Pydantic-validated 0-100)
      - components[0].explainer
      - components[0].anchor_text
      - sources (Pydantic-validated min_length=1)
      - why_mix_paragraph (Pydantic max_length=800 catches truncation)

    Server-normalized fields:
      - components[0].label (Decision 14 of ERN spec — allowlist)
    """


def _render_math_line_aura(
    *,
    aura_score_continuous: float | None,
    build_score: int,
    score_max: int,
) -> str:
    """Build AURA's math-line string (Decision 11).

    Primary format (when continuous score available):
      'composite 0.72 → AURA score 8/10'

    Fallback format (continuous unavailable — defensive):
      'institutional signals → AURA score N/10'

    No effort parameter (Decision 9 of feature-explain-stat-receipt-roi-
    res-grw.md). AURA is not effort-shifted.
    """
```

The `_AURA_RECEIPT_JSON_TEMPLATE` constant carries:

- A filled-in JSON example with `__FILL_IN__` sentinels for prose fields. The `score_provenance` key is OMITTED from the template (per Decision 8 v1.0 update — Gemma is told NOT to write the field; Pydantic's `None` default plus the postprocessor's server-stamp covers the path).
- The inlined SKILL Step 5b AURA voice example verbatim.
- Explicit prohibitions:
  - "Do NOT write 'N/10', 'your score is X', or any numeric score reference in any prose field."
  - The placeholder-sentinel prohibition (same as the four other stats).
  - "Do NOT include a `score_provenance` field in your output. The server stamps this field — your job is the prose voice; the basis label is server-controlled."
  - The standard `[helper:]` / `<thinking>` block prohibition.

The `_AURA_MARKDOWN_FALLBACK_APPENDIX` carries the SKILL AURA voice example as a markdown template, used only when the JSON parse fails. The cached `tool_call_log` from the JSON attempt is injected so no MCP re-fetch happens (per the ERN spec's Decision 6 v1.2).

### Gemma-touching extra discipline

This spec adds one new explain-receipt dispatch (AURA) that re-uses the gemma_client.generate_with_tools_loop integration established by the ERN spec and extended by the ROI/RES/GRW spec. The call-site discipline matches verbatim.

| Concern | Behavior |
|---------|----------|
| Fallback when transport fails | Existing: empty string from the loop → `fallback_text("chat_unavailable", locale)` 200 response. Unchanged. |
| Fallback when JSON parsing fails | `_postprocess_aura_explain_receipt` returns None → `_log_receipt_parse(parse_success=False, call_site="explain_aura_receipt", ...)` → re-run the tool loop ONCE without `final_turn_response_format` and with the AURA markdown-fallback appendix, **injecting the cached `get_institution_aura` result into the markdown appendix's user message** so no MCP re-fetch happens. |
| Fallback when `build.career.stats.aura is None` | Postprocessor returns None at the score-null guard. The trigger button at the `BuildResultsScreen` level is suppressed in this state (Decision 7); if somehow invoked anyway, the markdown-fallback path renders a "no AURA data for this school yet" voice prose. |
| `logs/gemma.jsonl` capture | Three records per call: JSON-mode tool loop's exchange record + structured `_log_receipt_parse` record (`call_site="explain_aura_receipt"`) + (on fallback) markdown loop's exchange record. |
| `INFERENCE_BACKEND=ollama` | Already wired via `payload["format"] = "json"` translation. No per-stat work. |
| `INFERENCE_BACKEND=openrouter` | Already wired via `response_format` propagation. No per-stat work. |
| Tool-call mechanism preservation | `final_turn_response_format` synthesis-turn-only scoping is already wired. No per-stat work. |
| Concurrency for cloud demo | One JSON-mode call per AURA explain click, plus possibly one markdown-fallback call. Same Gemma semaphore limits as existing chat. No new contention. |
| Token-budget impact | AURA appendix is similar in size to the other per-stat appendices (~600-900 tokens output for the JSON receipt). The existing `max_tokens=1500` budget covers AURA. The `why_mix_paragraph max_length=800` constraint catches truncation as a validation failure → fallback fires. |

### Testing Impact Analysis

> **Search performed:** `rg "_postprocess_aura\|_AURA_RECEIPT\|_AURA_LABEL\|score_provenance\|_humanize_basis\|aura_score_basis" backend/ frontend/` — surfaces the existing AURA touchpoints. The `_humanize_basis` helper has existing test coverage; the new explainer-receipt path adds a consumer.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/services/test_ask_gemma_explain_receipt.py` | All `test_ern_*`, `test_roi_*`, `test_res_*`, `test_grw_*` tests | Low | The schema additive is non-breaking. ERN/ROI/RES/GRW payloads emit `score_provenance=None`; existing test fixtures don't set the field, Pydantic supplies the default, validation passes. The only risk is wire-format-shape tests that count fields or strict-match the JSON — review and update if the serialization decision goes "with `null`" rather than "without." |
| `backend/tests/models/test_api.py` (any `ExplainStatReceipt` shape tests) | Schema shape assertions | Medium | Tests asserting "ExplainStatReceipt has exactly N fields" or strict-matching the JSON Schema break under the additive. Authorized to update such tests' expected field-count + add `score_provenance` to expected fields. |
| `backend/tests/services/test_ask_gemma.py` | `test_aura_explain_sentinel_not_yet_registered` (added by the ROI/RES/GRW spec) | High | This test is OBSOLETE after this spec. It's deliberately removed (deletion is the fix — the sentinel IS registered now). Authorized to delete. |
| `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | Existing rendering tests for ERN/ROI/RES/GRW | Low | The byline element is conditional on `payload.score_provenance` being a populated string. ERN/ROI/RES/GRW fixtures don't set the field, byline is absent, existing tests pass unchanged. The renderer change is silent for those fixtures. |
| `frontend/src/api/menu.test.ts` | Zod parser tests | Low | The Zod schema gets one new optional field. Existing parser tests pass through the new field as undefined. Authorized to add a new test for a payload WITH `score_provenance` (covered in New Tests Required below). |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `backend/tests/services/test_ask_gemma.py::test_aura_explain_sentinel_not_yet_registered` | DELETE | The sentinel IS now registered; the test's premise is invalid. |
| `backend/tests/models/test_api.py` (any field-count assertions) | Bump expected count by 1; add `score_provenance` to expected-field-name lists | Schema additive. |
| Any test that snapshot-matches the full `ExplainStatReceipt` JSON for an ERN/ROI/RES/GRW fixture | Update the snapshot to either include `"score_provenance": null` or omit it (matches the serialization decision deferred to §6) | Schema additive plus serialization decision. |

#### Confirmed Safe

- All four other stats' postprocessor tests (`test_ern_*`, `test_roi_*`, `test_res_*`, `test_grw_*`) — schema additive is non-breaking.
- The `_humanize_basis` existing tests in `backend/tests/services/test_receipts.py` (or wherever) — this spec consumes the helper but doesn't modify it.
- All non-stat-scope chat tests (boss, skill, build, branch, compare).
- Trace-rail / SSE / streaming protocol tests — no change to event shapes, only the `final_text.response` payload's optional field count grows by 1.
- All existing missing-data treatment tests — the renderer change is gated on `score_provenance` populated, so missing-data branches for other stats are unaffected.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/models/test_api.py` | `test_explain_stat_receipt_score_provenance_default_none` | New `ExplainStatReceipt(...)` without `score_provenance` defaults to `None`. |
| P0 | `backend/tests/models/test_api.py` | `test_explain_stat_receipt_score_provenance_max_length` | `score_provenance` of length 201+ raises `ValidationError`. |
| P0 | `backend/tests/models/test_api.py` | `test_explain_stat_receipt_score_provenance_rejects_sentinel` | `score_provenance="__FILL_IN__"` (or any sentinel pattern) raises `ValidationError` via the field validator. |
| P0 | `backend/tests/models/test_api.py` | `test_explain_stat_receipt_serialization_score_provenance` | The wire-payload behavior matches the §6-documented decision (either omitted-when-None or rendered-as-null). One of two assertion shapes; pick at implementation. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_aura_postprocess_happy_path_three_term` | AURA fixture with `aura_score_basis="three_term"` → receipt has `score_provenance="endowment + marketing + athletics"`, single component, math line `endowment + marketing + athletics → AURA score 8/10`. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_aura_postprocess_happy_path_one_term_marketing_only` | AURA fixture with `aura_score_basis="one_term_marketing_only"` → `score_provenance="marketing reach only"`, math line shape matches. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_aura_postprocess_happy_path_two_term_finance_only` | Same for `two_term_finance_only`. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_aura_postprocess_happy_path_two_term_no_endowment` | Same for `two_term_no_endowment`. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_aura_postprocess_returns_none_when_aura_score_null` | `build.career.stats.aura is None` → returns None → fallback path. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_aura_postprocess_score_from_build` | Gemma emits `score: 99` → server overwrites with `build.career.stats.aura`. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_aura_postprocess_score_provenance_from_humanize_basis` | The postprocessor calls `_humanize_basis(career.aura_score_basis)` (mock or assert-call) and stamps the result into `score_provenance`, regardless of what Gemma might have emitted. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_aura_postprocess_overwrites_gemma_score_provenance` | Even if Gemma somehow emits `score_provenance="something custom"`, the server overwrites with the basis label. (Note: the appendix instructs Gemma NOT to emit the field; this test covers the defensive overwrite if Gemma drifts.) |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_aura_postprocess_label_normalization` | Gemma emits `label="institutional weight"` (off-script) → `_normalize_label` matches by weight=100 → replaces with "your school's brand gravity" → WARNING logged. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_aura_postprocess_rejects_wrong_stat_code` | Gemma emits `stat_code: "ERN"` for an AURA dispatch → assertion fails → returns None. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_aura_postprocess_rejects_sentinel_passthrough` | `one_liner: "__FILL_IN__"` → field validator raises → returns None. Cover all four sentinel patterns across all four prose fields (`one_liner`, `components[0].explainer`, `components[0].anchor_text`, `why_mix_paragraph`). |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_aura_postprocess_logs_structured_record` | After parse, `_log_receipt_parse` appends record with `call_site="explain_aura_receipt"`. Both success and failure branches. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_render_math_line_aura_format` | `_render_math_line_aura` produces correct strings for each basis: `'endowment + marketing + athletics → AURA score 8/10'` etc. Defensive default for `score_provenance=None` covered. |
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_aura_explain_dispatches_via_registry` | `[explain-this:AURA]` sentinel → registry lookup hits the AURA config → response is `ExplainStatReceipt` with `stat_code="AURA"` and `score_provenance` populated. |
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_aura_explain_fallback_uses_cached_tool_log` | Fallback path injects cached `get_institution_aura` result; MCP dispatch count == 1. |
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_aura_explain_returns_none_when_aura_score_null` | `build.career.stats.aura is None` → postprocessor returns None → markdown fallback fires. |
| P0 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_renders_score_provenance_byline_when_present` | AURA fixture with `score_provenance="endowment + marketing + athletics"` → byline element renders with text "based on endowment + marketing + athletics", italic, text-text-muted. |
| P0 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_suppresses_score_provenance_byline_when_null` | ERN fixture with `score_provenance=null` → byline element is absent from the DOM. |
| P0 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_suppresses_score_provenance_byline_when_undefined` | Payload without `score_provenance` key at all → byline element is absent (Zod's `.optional()` returns undefined; same suppression as null). |
| P0 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_renders_aura_receipt_full_shape` | Full AURA payload renders: byline visible, single component without percentile callout, AURA-color rail, signals-arrow-score math line. Snapshot. |
| P0 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `test_aura_explain_link_visible_when_aura_present` | Fixture build with `stats.aura=8` → "✦ Explain this to me" trigger is rendered on the AURA legend row. Clicking fires `[explain-this:AURA]`. |
| P0 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `test_aura_explain_link_suppressed_when_aura_null` | Fixture build with `stats.aura=null` → trigger is absent or disabled (per Decision 7). |
| P0 | `frontend/src/api/menu.test.ts` | `test_zod_parser_accepts_score_provenance_string` | Payload with `score_provenance: "endowment + marketing + athletics"` parses cleanly. |
| P0 | `frontend/src/api/menu.test.ts` | `test_zod_parser_accepts_score_provenance_null` | Payload with `score_provenance: null` parses cleanly. |
| P0 | `frontend/src/api/menu.test.ts` | `test_zod_parser_accepts_omitted_score_provenance` | Payload without the key parses cleanly (optional field). |
| P0 | `frontend/src/api/menu.test.ts` | `test_zod_parser_rejects_score_provenance_too_long` | Payload with 201+ char `score_provenance` rejected (frontend mirrors Pydantic max_length=200). |
| P1 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_aura_postprocess_score_provenance_when_basis_null` | `aura_score_basis is None` (institution has a row but no scoreable basis) → postprocessor sets `score_provenance=None` directly (does NOT call `_humanize_basis`, which would return `"unknown basis"`). The renderer suppresses the byline. |
| P1 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_aura_math_line_when_score_provenance_null` | When score_provenance is None, math line shows `'institutional signals → AURA score N/10'` (defensive default per `_render_math_line_aura` docstring). |
| P1 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_registry_includes_aura_after_this_spec` | `_STAT_EXPLAIN_REGISTRY` has 5 entries (ERN, ROI, RES, GRW, AURA); the previous spec's "AURA not registered" test is gone. |
| P2 | `frontend/src/lib/zodSchemas.test.ts` | `test_zod_round_trip_with_aura_payload` | Round-trip a known-good AURA payload through Pydantic (backend serialize) and Zod (frontend parse); must match including `score_provenance`. |

#### Test Data Requirements

- **Fixtures.** Five canonical AURA scenarios:
  1. `aura_score_basis="three_term"` (most common — Indiana University-Bloomington or similar large public) — happy path with high score.
  2. `aura_score_basis="two_term_finance_only"` — public school with no NCAA athletics.
  3. `aura_score_basis="two_term_no_endowment"` — small private without IPEDS Finance endowment data but with EADA.
  4. `aura_score_basis="one_term_marketing_only"` — fringe case (only marketing reach available).
  5. `aura_score_basis=None` (rare — institution has a row but no scoreable basis); plus the no-row case (`stats.aura is None` → null-guard).
- **Mocks.** Gemma client responses for: valid AURA JSON, malformed JSON, sentinel passthrough on prose fields, `score_provenance` echo (defensive), label drift, `score: 99` hallucination, cross-stat drift (`stat_code: "ERN"` in an AURA dispatch).
- **Tool result mocks.** Mock `get_institution_aura` MCP responses with the five basis permutations + the no-row case.
- **State.** No new env vars. Both backends covered by smoke verification (§9).

---

## §5 Architecture Review

### @fp-architect Review
**Status:** APPROVED
**Reviewed:** 2026-05-03

#### System Context

This spec adds the fifth and final explain-stat receipt dispatch (AURA) to the existing registry that already serves ERN, ROI, RES, and GRW. AURA is architecturally distinct from the four percentile-rank stats in one way: its provenance is institution-level (one `aura_score_basis` enum per unitid), not per-component. The spec resolves this with one additive root-level field (`score_provenance: str | None`) on `ExplainStatReceipt` rather than forcing the basis into `StatComponent.missing_reason`. The change touches four layers: Pydantic model (api.py), service dispatch (ask_gemma.py), Zod schema (chat.ts), and React renderer (ExplainStatReceipt.tsx + BuildResultsScreen.tsx). No pipeline, no DuckDB, no new MCP tools.

#### Data Flow Analysis

Data flow for an AURA explain-this click, traced end to end:

1. **Frontend trigger:** `BuildResultsScreen.tsx` renders the "Explain this to me" button when `build.career.stats.aura !== null`. Click fires `[explain-this:AURA]` sentinel via `handleExplainStat` -> `openChat` with scope `{ kind: "stat", target_id: "AURA" }`.

2. **API boundary:** `POST /chat/ask/stream` with `AskRequest.scope.target_id = "AURA"`. The `AskScope` validator at `backend/app/models/api.py:159` already includes `"AURA"` in `valid_stats`. Clean.

3. **Registry dispatch:** `chat_ask_stream` matches `[explain-this:AURA]` via `_EXPLAIN_SENTINEL_RE` -> `_STAT_EXPLAIN_REGISTRY["AURA"]` -> appends AURA JSON appendix to system prompt -> Gemma tool-loop fires `get_institution_aura` -> Gemma emits JSON receipt.

4. **Postprocessor:** `_postprocess_aura_explain_receipt` receives raw JSON string + Build + tool_call_log. Server-stamps `score` from `build.career.stats.aura`, `score_provenance` from `_humanize_basis(career.aura_score_basis)`, `math_line` from `_render_math_line_aura`, `scoring_scale` from `_AURA_SCORING_SCALE`, and `evidence_bullets` from the `get_institution_aura` tool call log. Returns `ExplainStatReceipt` or `None`.

5. **Wire serialization:** Receipt flows into `AskResponse(response=receipt)` or `TraceFinalText(response=receipt)`, serialized via `ev.model_dump(mode="json")` at the SSE boundary (`ask_gemma_router.py:93`).

6. **Frontend parse:** Zod `explainStatReceiptSchema.safeParse` at the SSE consumer validates the payload. `score_provenance` is declared `.nullable().optional()`, so both `null` and missing-key are accepted.

7. **Render:** `ExplainStatReceipt.tsx` renders the byline `<p>` when `payload.score_provenance` is a populated string; suppresses when null/undefined.

Every hop has a typed contract. Zone boundaries are respected: no pipeline reads or writes; the postprocessor reads the Build (in-memory) and the MCP tool call log (cached from the Gemma loop). The `get_institution_aura` MCP tool reads from Gold zone `consumable.institution_aura` -- the correct zone for a callable surface.

#### Contract Review

**Pydantic model (`ExplainStatReceipt`):** The additive field `score_provenance: str | None = Field(default=None, max_length=200)` is well-typed and non-breaking. `max_length=200` is appropriate for the `_humanize_basis` outputs (longest is 45 chars). The `_reject_sentinel_passthrough` field validator is defensively correct but requires a None-guard wrapper (see Concerns).

**Zod schema (`chat.ts`):** `score_provenance: z.string().max(200).nullable().optional()` mirrors the Pydantic field. The existing Zod schema already has `stat_code: z.enum(["ERN", "ROI", "RES", "GRW", "AURA"])` and `scoring_scale: z.array(scoringTierSchema).nullable().optional()`, so the AURA dispatch path is pre-wired on the parse side. No Zod changes needed beyond the one new field.

**Registry dataclass (`_StatExplainConfig`):** The `stat_code` Literal widens from `Literal["ERN", "ROI", "RES", "GRW"]` to include `"AURA"`. The registry entry needs fields `appendix_json_fn`, `appendix_markdown_fn`, `user_prompt`, `missing_score_one_liner`, `missing_score_why_mix` -- not the `sentinel`, `appendix_template`, `markdown_fallback_appendix` names used in the spec's pseudo-code at lines 478-486. This is a spec-vs-implementation naming drift that the implementer must reconcile against the actual dataclass shape (see Concerns).

**MCP tool response shape:** `get_institution_aura` returns `{ data: { aura_score_continuous, endowment_per_fte, marketing_ratio, athletic_spend_per_fte, ... } }`. The postprocessor's `_extract_aura_tool_data` correctly targets `turn.tool_name == "get_institution_aura"` and pulls `preview.get("data")`. The signal field names in `_AURA_SIGNAL_DEFINITIONS` and `_AURA_BASIS_SIGNALS` match the actual `INSTITUTION_AURA_RESPONSE_FIELDS` constants. Clean.

**`_PostprocessFn` type alias:** Defined as `Callable[[str, Build, list[ToolCallTurn], str], ExplainStatReceipt | None]` -- a synchronous callable. The spec's pseudo-code declares `async def _postprocess_aura_explain_receipt`. The existing four postprocessors are all synchronous (`def`, not `async def`). The implementer must make AURA's postprocessor synchronous to match (see Concerns).

#### Findings

##### Sound

- **Additive schema field is the correct shape.** The ERN spec's Decision 10 v1.2 anticipated exactly this: institution-level provenance that doesn't fit the per-component `StatComponent.missing_reason` slot. `score_provenance: str | None` at the receipt root is the minimum viable additive -- one optional field, non-breaking, server-stamped. The spec's rejection of alternatives (stuffing into `missing_reason`, new sub-model, discriminated union) is well-reasoned and consistent with the existing architecture.

- **Server-stamping contract is correctly specified.** The boundary between server-owned and Gemma-owned fields is explicit. `score_provenance`, `score`, `math_line`, `scoring_scale`, and `evidence_bullets` are all server-stamped; Gemma owns the prose fields (`one_liner`, `explainer`, `anchor_text`, `why_mix_paragraph`). The postprocessor's unconditional overwrite of `score_provenance` (regardless of what Gemma emits) is the right defensive posture -- same pattern as the other four stats' server-owned fields.

- **`_humanize_basis` reuse is correct.** The existing helper at `receipts.py:250-260` already maps all four basis enum values to receipt-friendly strings. Single source of truth. The null-basis guard (check `aura_score_basis is not None` before calling) is correctly specified to avoid surfacing `"unknown basis"` to students.

- **Evidence bullets extraction from tool call log is correctly patterned.** The `_extract_aura_tool_data` helper mirrors the pattern established by RES (which reads O*NET tasks from the tool log). The `_AURA_BASIS_SIGNALS` dict correctly maps each basis to the signals that should be present, and `_AURA_SIGNAL_DEFINITIONS` provides the 16-year-old-friendly definitions. The basis-dependent bullet count (1-3) is well-specified.

- **Math line with continuous score is well-designed.** `aura_score_continuous` is confirmed present on the `INSTITUTION_AURA_RESPONSE_FIELDS` list returned by the MCP tool. The fallback from continuous-form to signals-arrow-form handles the defensive case cleanly.

- **Null-AURA dispatch suppression is defense-in-depth.** Two independent guards: (1) frontend gate on `build.career.stats.aura !== null` at `BuildResultsScreen.tsx` prevents the trigger from rendering, (2) backend postprocessor's null-guard returns `None` at the top of `_postprocess_aura_explain_receipt`. The frontend gate catches ~10% of institutions; the backend guard is belt-and-suspenders for direct API callers. No gap in the null path.

- **Registry widening from 4 to 5 entries is clean.** The `_STAT_EXPLAIN_REGISTRY` is a dict keyed by string; adding `"AURA"` is O(1) and doesn't affect existing entries. The `Literal` type widening on `_StatExplainConfig.stat_code` is purely additive.

- **Scoring scale tiers are well-calibrated.** Five tiers at 2-point intervals on a 1-10 scale with the linear P5/P95 rescale. Consistent with the 5-7 tier pattern used by ROI/RES/GRW.

##### Concerns

- **`_reject_sentinel_passthrough` will crash on explicit `None` input.** The function signature is `(value: str) -> str` and calls `pattern.search(value)`, which raises `TypeError` when `value is None`. Pydantic v2 `field_validator` in default (`"after"`) mode runs the validator on any explicitly-set value, including `None`. If Gemma sends `"score_provenance": null` in its JSON output, `ExplainStatReceipt.model_validate(parsed)` will raise `TypeError` (not `ValidationError`), which may not be caught by the postprocessor's existing `except ValidationError` handler. The spec correctly notes this at line 401-402 ("if `_reject_sentinel_passthrough` doesn't short-circuit on None, wrap in a None-check") but the implementation note is buried in a code comment rather than called out as a required action. **Impact:** If Gemma ever emits `"score_provenance": null` explicitly, the receipt parse fails with an uncaught `TypeError` instead of a clean `ValidationError` -> fallback. This is a correctness issue, not a crash-the-server issue (the tool loop's outer `try/except` would catch it), but the failure mode is confusing. **Recommendation:** The implementer MUST wrap the validator with a None-guard: `if value is None: return value` before the sentinel check. Alternatively, use `field_validator("score_provenance", mode="before")` and short-circuit on non-string types. This is a known implementation instruction (line 401-402), not a missing spec decision. No spec change needed, but the implementer should treat this as P0.

- **Spec pseudo-code uses wrong `_StatExplainConfig` field names.** The registry entry at spec lines 478-486 uses `sentinel`, `appendix_template`, `markdown_fallback_appendix` -- but the actual dataclass (ask_gemma.py:2460-2471) uses `appendix_json_fn`, `appendix_markdown_fn`, `user_prompt`, `missing_score_one_liner`, `missing_score_why_mix`. The spec's File Changes table at line 357(d) correctly says "Register AURA in `_STAT_EXPLAIN_REGISTRY` as the fifth entry" and the Service Changes pseudo-code shows the correct function names for the postprocessor and math-line helpers, but the actual registry entry constructor call is wrong. **Impact:** Implementer reads the spec's pseudo-code, writes incorrect field names, gets a `TypeError` on `_StatExplainConfig(sentinel=..., ...)`. Costs 5-15 minutes of debugging. **Recommendation:** Not a blocker -- the implementer will see the actual `_StatExplainConfig` definition when they look at the code. The spec is guidance, not copy-paste source. But if the spec gets a v1.1 pass, correct the field names in the registry entry pseudo-code to match: `appendix_json_fn`, `appendix_markdown_fn`, `user_prompt`, `missing_score_one_liner`, `missing_score_why_mix`.

- **Spec pseudo-code declares `async def _postprocess_aura_explain_receipt` but the type alias and all four existing postprocessors are synchronous.** The `_PostprocessFn` type alias is `Callable[[str, Build, list[ToolCallTurn], str], ExplainStatReceipt | None]` -- not a coroutine. An `async def` postprocessor would return a coroutine, not `ExplainStatReceipt | None`, causing a type error at registration time. **Impact:** Same as above -- implementer copies the pseudo-code, gets a type mismatch. **Recommendation:** Make AURA's postprocessor synchronous (`def`, not `async def`) to match the existing pattern. No spec change strictly needed since the implementer will reconcile against the codebase, but note for accuracy.

- **Pydantic-v2 serialization: the "always-emit-null" path is the safer default.** The spec correctly identifies the tradeoff. `model_dump(mode="json")` at `ask_gemma_router.py:93` does NOT pass `exclude_none=True`. Adding it globally would also strip `score: null` and `scoring_scale: null` from ERN/ROI/RES/GRW payloads, and `value_pct: null`, `anchor_dollars: null`, `missing_reason: null` from StatComponent payloads. All of those `null`s are semantically meaningful (they signal "missing data" to the frontend). Therefore `exclude_none=True` is not safe at the SSE boundary. The spec should recommend "accept the noisy `score_provenance: null`" as the implementation decision. The frontend Zod schema handles it cleanly via `.nullable().optional()`. Wire cost is ~30 bytes per receipt. **Impact:** None if the implementer chooses "accept null". Potential regression to ERN/ROI/RES/GRW if the implementer chooses "exclude_none" without scoping it. **Recommendation:** The spec should narrow the deferred decision to "accept the null field in the wire payload" and drop the `exclude_none` option. The implementer's §6 decision should be pre-decided here.

##### Blockers

None.

#### Verdict
- [x] APPROVED

#### Conditions

None required before implementation. The four concerns above are implementation-time notes, not spec-blocking issues:

1. The None-guard on `_reject_sentinel_passthrough` for `score_provenance` is already documented in the spec (line 401-402). The implementer must implement it.
2. The registry field-name drift and `async` vs `def` mismatch in pseudo-code are cosmetic spec inaccuracies that the implementer will resolve by reading the actual `_StatExplainConfig` dataclass.
3. The serialization decision should default to "accept the null" -- the alternative (`exclude_none=True`) is unsafe at the current SSE boundary due to other semantically-meaningful `null` fields on the same models.

### @fp-data-reviewer Review (if applicable)
**Status:** SKIPPED (no pipeline / no formula changes; `_humanize_basis` and `_fetch_aura` are reused unchanged)

#### Findings
[Skipped — this spec describes the existing AURA pipeline for the explainer voice; it does not modify `consumable.institution_aura`, `_fetch_aura`, the `aura_score_basis` enum, or `compute_pentagon`.]

#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

---

## §6 Implementation Log

**Status:** COMPLETE

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/app/models/api.py` | Added `score_provenance: str \| None` field + `_reject_sentinel_score_provenance` validator with None guard. Updated docstrings. |
| `backend/app/services/ask_gemma.py` | Added `get_institution_aura` to `_TOOLS`. Added AURA constants, templates, helpers (`_render_math_line_aura`, `_extract_aura_tool_data`, `_build_aura_evidence_bullets`), `_postprocess_aura_explain_receipt`, and AURA registry entry. Widened `_StatExplainConfig.stat_code` Literal. Imported `_humanize_basis`. |
| `frontend/src/types/chat.ts` | Added `score_provenance` to Zod schema. |
| `frontend/src/components/menu/ExplainStatReceipt.tsx` | Added score provenance byline (italic, 13px, text-text-muted, 6px mt) gated on truthy `score_provenance`. |
| `frontend/src/screens/BuildResultsScreen.tsx` | Added AURA to explain trigger, gated on `stats.aura != null`. |
| `docs/reference/stat-display-surfaces.md` | Updated §1a, §1b, §1g, §1i for AURA wiring. |
| `.claude/skills/pentagon-stat-explanation/SKILL.md` | Added companion reference to AURA appendix/postprocessor. |
| `backend/tests/services/test_ask_gemma_explain_receipt.py` | Updated registry completeness test. Added 28 new backend tests. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Replaced `aura_explain_link_not_shown_yet` with `aura_explain_link_visible_when_aura_present` + `aura_explain_link_suppressed_when_aura_null`. |
| `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | Added 4 AURA + score_provenance rendering tests. |
| `frontend/src/types/chat.test.ts` | New file — 8 Zod schema tests for score_provenance. |

### Deviations from Spec
1. **`get_institution_aura` was NOT in `_TOOLS`** — spec claimed it was already in the allowlist, but it wasn't. Added it.
2. **`CareerOutcome.school_name` → `institution_name`** — spec pseudo-code used `school_name` but the actual field is `institution_name`. Fixed in markdown appendix template.
3. **Type guard on evidence bullet values** — code review flagged that `int(value)` / `f"{value:.3f}"` could crash on non-numeric values from the MCP response. Added `isinstance(value, (int, float))` guard.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | PASS (lint fix) | ruff I001 unsorted imports in test file | Merged AURA imports into top-level import block |
| 2 | PASS | — | — |

### Pydantic-v2 serialization decision (§4 deferred decision)
- [x] Decided: **always-emit-null** (accept the `"score_provenance": null` in wire payloads)
- [x] Rationale: `exclude_none=True` is unsafe at the SSE boundary — `score: null`, `scoring_scale: null`, `value_pct: null`, etc. are all semantically meaningful. The ~30 bytes per receipt is negligible. Frontend Zod `.nullable().optional()` handles both wire states.
- [x] Test fixture / assertion shape updated to match.

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
**Status:** SKIPPED (visual treatment is one new byline element — fully covered by frontend tests; the rest of the receipt is inherited from prior specs)

### Code Review (@faang-staff-engineer)
**Status:** APPROVED
**Reviewer:** Staff Engineer (15 YOE, production incident survivor)
**Date:** 2026-05-03

#### Summary

Look, I love Claude, BUT... I came into this one ready to find the usual AI blindspots — the missing error paths, the optimistic assumptions about data shapes, the "works in dev, dies in prod" patterns I've seen a hundred times. I reviewed all six changed files, the test suite (34 new tests across backend and frontend), the Pydantic model, the postprocessor pipeline, the frontend renderer, and the trigger gating.

This is solid work. The implementation follows the established registry pattern exactly, the server-stamping discipline is airtight (Gemma can't pollute `score_provenance`, `score`, `math_line`, `sources`, `scoring_scale`, or `evidence_bullets`), the null-guard layering is correct (frontend suppresses the trigger when AURA is null, backend postprocessor returns None as belt-and-suspenders), and the test coverage is thorough. I found one moderate issue worth fixing and one minor observation. No blockers, no critical or serious findings.

I'm not saying Claude did this perfectly because it's AI. I'm saying this particular implementation is well-structured. This time.

#### Findings

**Moderate Findings**

##### M1: `_build_aura_evidence_bullets` — `int(value)` and `f"{value:.3f}"` crash on non-numeric tool data

**Severity:** Moderate
**Impact:** If the MCP tool response carries an unexpected type for a signal value (e.g., a string like `"PrivacySuppressed"` which is explicitly called out in CLAUDE.md as a College Scorecard pattern, or a `NaN` float from DuckDB), `int(value)` throws `TypeError`/`ValueError` and `f"{value:.3f}"` throws `TypeError`. The postprocessor would propagate the uncaught exception and the receipt would fail entirely — not just the evidence bullets, but the whole AURA receipt for that school. The `value is None` guard at line 2689 handles the null case but not the wrong-type case.

**Location:** `backend/app/services/ask_gemma.py:2688-2694`
```python
value = tool_data.get(key)
if value is None:
    continue
if key == "marketing_ratio":
    val_str = f"{value:.3f} ratio"
else:
    val_str = f"${int(value):,}/student"
```

**The Fix:** Add a type guard before formatting. The function already returns `None` gracefully when all bullets are skipped, so skipping a non-numeric signal is the right degradation:
```python
value = tool_data.get(key)
if value is None:
    continue
if not isinstance(value, (int, float)):
    continue
if key == "marketing_ratio":
    val_str = f"{value:.3f} ratio"
else:
    val_str = f"${int(value):,}/student"
```

**Why this matters:** The CLAUDE.md explicitly states "All PrivacySuppressed values in College Scorecard data must be converted to null." The gold zone should enforce this, but defense-in-depth at the evidence-bullet layer costs one line and prevents a 3am page if a new data source or schema migration introduces a non-numeric value. The `_extract_aura_tool_data` function returns a raw `dict` from JSON parsing — it doesn't validate individual field types. This is exactly the kind of edge case that works in dev (where your test fixtures are all clean floats) and breaks in prod (where one school in 6,000 has a data anomaly). I've been paged for less.

**Routing:** Implementation agent — one-line fix in `_build_aura_evidence_bullets`.

**Minor Findings**

##### m1: `_extract_aura_tool_data` returns the first successful `get_institution_aura` turn without validating it matches the expected `unitid`

**Severity:** Minor
**Impact:** If Gemma somehow calls `get_institution_aura` twice with different `unitid` arguments (e.g., a hallucinated follow-up call for a different school), the extractor takes whichever one appeared first. In practice this is extremely unlikely because the appendix instructs exactly one tool call and the `unitid` is server-injected into the prompt, and the postprocessor server-stamps `score_provenance` from `build.career.aura_score_basis` (not from the tool response), so the worst case is slightly wrong evidence bullet dollar amounts — not a wrong score or wrong basis. Not blocking, but noting for the record. The same pattern exists in all four sibling extractors (`_extract_ern_tool_results`, etc.) so this is a systemic observation, not an AURA-specific regression.

**No fix required** — the risk is theoretical and consistent with established patterns.

#### What's Good

- **Server-stamping discipline is correct.** Every field that could be hallucinated by Gemma is overwritten unconditionally: `score`, `score_max`, `score_provenance`, `math_line`, `sources`, `scoring_scale`, `evidence_bullets`, `value_pct`, `anchor_dollars`, `missing_reason`. The Gemma-written fields (`one_liner`, `explainer`, `anchor_text`, `why_mix_paragraph`) all pass through the sentinel-passthrough validator. This is the right trust boundary.
- **The `score_provenance` null-basis guard is exactly right.** The postprocessor checks `basis is not None` before calling `_humanize_basis`, avoiding the confusing `"based on unknown basis"` string. The test at line 2901 explicitly verifies this contract.
- **The frontend gating on `stats.aura !== null` correctly prevents a wasted Gemma round-trip.** The backend's null-guard at line 2748-2755 is genuine belt-and-suspenders, not redundant with the frontend check.
- **Evidence bullets show actual per-student dollar values with plain-English definitions.** This matches the transparency standard set by the other four stats. The basis-dependent signal count (1-3 bullets) is clean — `_AURA_BASIS_SIGNALS` drives it deterministically.
- **The Zod schema on the frontend correctly marks `score_provenance` as `.nullable().optional()`.** This handles all three wire states (string, null, absent) and the frontend renderer's truthy gate (`payload.score_provenance && ...`) collapses null and undefined correctly.
- **Test coverage is thorough.** 34 new tests covering: happy path per basis variant, null-score guard, server-stamped score overwrite, score_provenance per-basis mapping, null-basis provenance suppression, label normalization, stat_code mismatch rejection, sentinel passthrough rejection, invalid JSON rejection, math line rendering (continuous + fallback + precision), tool data extraction (success + missing + error-skip + bad-JSON), evidence bullet construction per basis variant, missing signal value skipping, Pydantic field validation (default, max_length, sentinel, null, valid string, boundary), registry wiring, Zod schema boundary tests, and frontend renderer tests for byline presence/suppression/full shape.
- **The additive schema change is genuinely non-breaking.** The `score_provenance` field defaults to `None`, Pydantic omits it from serialization for the four other stats, and the Zod schema marks it optional — existing ERN/ROI/RES/GRW payloads are structurally unchanged.

#### Questions for the Author

1. Has the `marketing_ratio` value been verified to always arrive as a float from the `get_institution_aura` MCP response in production data? The gold zone schema shows `DoubleType()` but the evidence bullet formatter has no type guard (see M1).
2. Is there a test that exercises the `_build_aura_evidence_bullets` path when ALL signal values in the tool data are null (i.e., tool_data is a dict with the right keys but all None values)? The function returns `None` via the `bullets if bullets else None` guard, but I didn't see an explicit test for the "all signals null" case for any given basis. Not blocking — the logic is correct — but worth adding for regression protection.

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

**Approval conditioned on:** M1 (type guard in `_build_aura_evidence_bullets`) should be fixed before shipping. It's a one-line change. The minor finding (m1) is informational only — no action required.

---

## §9 Verification

**Status:** ALL PASSED (no regressions introduced by this spec)
**Verified:** 2026-05-03 10:35

### Backend
| Check | Result | Details |
|-------|--------|---------|
| Lint (ruff) | PASS | 1 fix applied (see Build Accountability Log); clean after fix |
| Type check (mypy) | PASS | 17 errors all pre-existing on main — confirmed via `git stash` baseline; 0 new errors introduced |
| Tests (pytest) | PASS | 1510 passed, 4 failed — all 4 failures match known pre-existing list |

#### Pre-existing pytest failures (confirmed pre-existing on main)
- `test_context_for_stat_includes_lineage_drivers[ROI]` — ROI cost-basis context string mismatch
- `test_maps_row_into_career_outcome` — floating point comparison (0.7500433... vs 0.75)
- `test_prompt_carries_net_price_and_modeled_debt` — boss fight cost context
- `test_cost_of_attendance_narrative_cites_4yr_cost` — narrative cost assertion

### Frontend
| Check | Result | Details |
|-------|--------|---------|
| TypeScript | PASS | No errors |
| Tests (vitest) | PASS | 802 passed, 12 failed — all 12 failures confirmed pre-existing on main |
| Production build (Vite) | PASS | 903 modules transformed; build completed in 1.77s |

#### Pre-existing vitest failures (confirmed pre-existing on main)
- `FinancesCard.test.tsx` — 10 failures (residency-aware tuition suite + ROI receipt)
- `BuildResultsScreen.test.tsx` — 2 failures (createBuild argument passing)

### Manual smoke verification (deferred to human)
| Backend | AURA happy path (three_term) | AURA basis variants (one_term_marketing_only, etc.) | Null AURA (trigger suppressed) |
|---------|------------------------------|---------------------------------------------------|--------------------------------|
| Ollama (local) | | | |
| OpenRouter (cloud) | | | |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | ruff FAIL | `test_ask_gemma_explain_receipt.py:2708` — E402 module-level import not at top, I001 unsorted imports, F401 unused `_AURA_LABEL_ALLOWLIST` | Merged AURA imports into top-level import block; removed `_AURA_LABEL_ALLOWLIST`; deleted duplicate mid-file import block |
| 2 | All checks PASS | — | — |

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
