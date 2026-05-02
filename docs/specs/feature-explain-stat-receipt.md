# Feature: Explain-Stat Receipt — Structured JSON Renderer for Stat Explanations (ERN)

## Claude Code Prompt

```
Read the spec at docs/specs/feature-explain-stat-receipt.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review §1-§4 (Pydantic schema design, JSON-mode
     plumbing through gemma_client.generate_with_tools_loop, server-side
     post-processing pipeline, API response shape extension, frontend
     chat-history-item discriminator).
   - Invoke @genai-architect for the JSON-mode prompt + schema review:
     verify the system appendix rewrite produces parseable JSON
     reliably under both INFERENCE_BACKEND=ollama and openrouter, and
     that the schema is generic enough that ROI/RES/GRW future specs
     reuse the same shape without breaking changes.
   - Both write findings to §5.
   - If APPROVED: proceed to step 2.
   - If CHANGES REQUESTED (Significant): STOP, alert human.
   - If REJECTED (Blocker): STOP, alert human.

2. DESIGN VISION
   - Invoke @fp-design-visionary to fill §3 with the pixel-perfect
     <ExplainStatReceipt> component design: typography, source pills,
     missing-data treatment ("—" or subtle inline note), responsive
     behavior, dark-first Brightpath token usage, and how the receipt
     bubble visually distinguishes from a plain-text Gemma reply in the
     chat history.

3. IMPLEMENTATION
   - Implement the spec as written in §3 (UI/UX) and §4 (Technical Spec).
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly.
   - DURING coding: Update any broken tests listed in "Authorized Test
     Modifications" — every other failure is a STOP-and-escalate event.
   - Log all work to §6.
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest).
   - BUILD ACCOUNTABILITY: max 3 attempts before escalating via §10.

4. TESTING
   - Invoke @test-writer to review the spec and add coverage from §4.
   - The JSON parser, the score-from-build override, the missing-data
     branches, and the parse-failure fallback are P0.

5. DESIGN AUDIT
   - Invoke @fp-design-auditor for token compliance on the new receipt
     component (Brightpath tokens, focus state, missing-data state,
     dark-first enforcement).

6. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests.

7. VERIFICATION
   - Invoke @fp-builder to run full build verification.

8. COMPLETION
   - Update Status to COMPLETE and check off §1 Success Criteria.
   - Generate report to reports/feature-explain-stat-receipt-YYYY-MM-DD.md.

OUT OF SCOPE — REJECT as scope creep if a reviewer requests them:
  - Extending the structured-receipt path to ROI, RES, GRW, or AURA. Each
    is a separate spec authored after this one ships and the spike is
    validated end-to-end with real users. The ExplainStatReceipt schema is
    designed to fit all five, but only ERN populates it in this spec.
  - Replacing the existing free-form Ask Gemma chat for stat scope. The
    JSON path triggers ONLY on the sentinel opener "[explain-this:ERN]"
    dispatched from the "✦ Explain this to me" link. A user typing their
    own question still routes to the existing markdown-prose handler.
  - Backporting structured JSON output to other Ask Gemma scopes (boss,
    skill, build, branch, compare). Different problem domain — those
    surfaces are conversational, not receipt-shaped.
  - Adding a new MCP tool for stat breakdowns. The existing
    get_career_paths and get_occupation_data tools already return
    cip_family_earnings_rank, earnings_1yr_median, wage_percentile_overall,
    and median_annual_wage — no new tool surface needed.
  - Removing the existing ERN-explain spike code path before the JSON
    path is fully validated. The spike's markdown appendix becomes the
    fallback path when JSON parsing fails, until @fp-builder verifies the
    JSON path is reliable across both inference backends.
```

---

## Status: DRAFT

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect + @genai-architect approval |
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
| Created | 2026-05-02 |
| Author | Jeff + Claude Code |
| Spec Version | 1.1 (DRAFT) |
| Last Updated | 2026-05-02 |
| Blocked By | — (was: `pentagon-stat-reshape.md`; reshape reached COMPLETE on 2026-05-02 — unblocked) |
| Changelog | 1.1 — pentagon-stat-reshape unblock: verified spike code survived the reshape merge (`_ERN_EXPLAIN_OPENER`, `_ern_explain_appendix`, `_HELPER_LEAK_RE` still present in `ask_gemma.py`). No changes to §1-§4 required from the reshape; the schema's `stat_code: Literal["ERN", "ROI", "RES", "GRW", "AURA"]` already reflected the post-reshape stat set. <br>1.0 — initial draft. |
| Related Specs | `docs/specs/feature-ask-gemma.md` (the existing scope-aware chat surface this extends); `docs/specs/pentagon-stat-reshape.md` (in-flight HMN→AURA reshape); `docs/specs/feature-gemma-trace.md` (the trace-rail UX that streams tool-call events — unchanged by this spec but its event model is what makes the "show the receipts" moment legible) |
| Related References | `.claude/skills/pentagon-stat-explanation/SKILL.md` (voice rules + worked-example template that the JSON prose fields must follow); `docs/reference/stat-display-surfaces.md` (surface index — `<ExplainStatReceipt>` is a new entry under §1g of that doc once shipped) |

---

## §1 Feature Description

### Overview

Replace the free-form Gemma narration produced by the in-app ERN-explain spike with a **structured JSON receipt** that the backend validates, post-processes for arithmetic correctness, and renders via a dedicated `<ExplainStatReceipt>` React component. Gemma writes the prose fields (one-liner, per-component explainers, why-mix paragraph) and pulls the data via `get_career_paths` + `get_occupation_data` tool calls; the server stamps the score from the build, computes the math line, and validates everything via Pydantic before the response leaves the API. ERN-only in this spec.

### Problem Statement

The ERN-explain spike (shipped 2026-05-02 in this same conversation, no prior spec) proved that the four-section markdown template works as a UX shape but **fails on math reliability**. A real run on Millikin University → Chemistry → Food Science Technicians produced:

- Score `4.3/10` when the actual ERN formula `_round_half_up(1.0 + 9.0 × raw)` over `raw = 0.146` yields **2/10**.
- A null `cip_family_earnings_rank` was substituted with `0`, producing a fake but valid-looking math line `0.6 × 0 + 0.4 × 0.365 = 0.146`.
- A null `earnings_1yr_median` rendered as `$0`.
- The "Why we mix both pieces" paragraph truncated mid-sentence ("Imagine a student in a high-paying field like software engineering,").
- Gemma's `[helper: ...]` scratchpad block leaked into the response (caught and patched by `_HELPER_LEAK_RE` in `ask_gemma.py`, but the leak proves the model is not reliably following the "never reproduce helper annotations" rule).

The root cause is structural, not a prompt-tuning issue: at temperature 0 with explicit instructions, Gemma 4 still computes `1 + 9 × 0.146 = 4.3` (treating raw as if it were the score) and improvises around null inputs. Every prompt-engineering tightening so far has produced a different plausibly-wrong number on the next run. No amount of prompt iteration will reliably compute `1 + 9 × raw` and round half-up across the full universe of school × major × career combinations the product exposes (~140k+ rows in `consumable.program_career_paths`).

The fix is to take the math out of Gemma's hands. Gemma stays in charge of **voice** (one-liner, per-component explainer, why-mix paragraph); the **server** owns score, percentiles, math line, missing-data handling, and rendering structure.

### Success Criteria

- [ ] When a student clicks "✦ Explain this to me" on the ERN row in `BuildResultsScreen`, the slide-in chat opens, fires the sentinel opener, streams two tool-call events (`get_career_paths` + `get_occupation_data`) on the trace rail, and renders an `<ExplainStatReceipt>` component as the assistant's reply.
- [ ] The `score` field in the rendered receipt always equals the build's `stats.ern` value, regardless of what Gemma emitted in the JSON. Server-side override is unconditional.
- [ ] The `math_line` field is computed server-side from the tool-result percentile values. Null inputs render as `n/a` (e.g., `0.6 × n/a + 0.4 × 0.37 → score 2/10`), never as `0`.
- [ ] When a tool returns null for `cip_family_earnings_rank`, the receipt's school-rank component renders `value_pct = null` and surfaces a `missing_reason` line ("no median earnings reported for this program yet"); no `0`, no `$0`.
- [ ] When the tool loop fails entirely (transport error, both tools raise) or Gemma's output fails Pydantic validation, the response falls back to the existing markdown-spike path (the system appendix added in 2026-05-02 in `ask_gemma.py`). The student gets the spike's output, not a 5xx.
- [ ] Pydantic validation rejects payloads with hallucinated fields. The `ExplainStatReceipt` model is `extra="forbid"` so Gemma adding fields is a parse failure that triggers fallback, not silent acceptance.
- [ ] The trace-rail UX is byte-identical to the spike — same `TraceTurnStart` and `TraceTurnComplete` events, same ordering, same timing. The structural change is the `final_text` payload shape, not the streaming protocol.
- [ ] `logs/gemma.jsonl` continues to capture every Gemma call with the new `response_format` flag and the JSON output recorded verbatim.
- [ ] Both `INFERENCE_BACKEND=ollama` (local) and `INFERENCE_BACKEND=openrouter` (cloud demo) successfully produce valid JSON receipts under temperature 0. Manual smoke verification on each backend before VERIFICATION marks green.
- [ ] The `ExplainStatReceipt` schema is generic enough that ROI, RES, GRW, and AURA can populate it in future specs without breaking-change additions to the Pydantic model. The component count, the optional `value_pct`, and the per-component `missing_reason` already accommodate the AURA missing-data case (institution-level, may be null) and the GRW case (single-component, no blend).
- [ ] `docs/reference/stat-display-surfaces.md` gains a new §1i entry for `<ExplainStatReceipt>` listing it as ✅ wired (the second after §1a) so the next surface-by-surface explainer rollout doesn't have to rediscover the contract.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | The math is **server-computed**, not Gemma-generated. The `score` field on the receipt is unconditionally stamped from `build.career.stats.ern`; the `math_line` field is built in Python from the values the tools returned. | The spike proved Gemma's arithmetic is unreliable across the full input space. Receipts that show wrong math are worse than no receipts — they damage trust in every other number on the screen. | (a) Tighten prompts further. Rejected — already at temperature 0 with explicit instructions, repeated failures across runs. (b) Have Gemma emit the raw values and have a JS-side calculator on the frontend. Rejected — splits the formula authority across two languages and breaks the single-source-of-truth rule (the formula lives in `src/gold/futureproof_engine.py`). (c) Skip the math line entirely and only show percentiles. Rejected — the math line IS the receipt; without it the explainer is just a definition. |
| 2 | JSON output via `response_format: {"type": "json_object"}` on the OpenAI-compatible chat endpoint, **not** a custom delimited format or markdown-with-tags. | Both Ollama and OpenRouter (Gemma 4) support `response_format` natively on the chat-completions API. Pydantic validation gives us a typed parser at the API boundary for free. Markdown-with-tags would require a custom parser and lose the type safety. | (a) Markdown with HTML-like tags Gemma fills in. Rejected — fragile parser, no type checking, no schema enforcement. (b) Function calling with a "render_receipt" function whose args ARE the receipt. Rejected — abuses the function-calling channel for output formatting; muddles the trace rail (which currently shows real tool calls). (c) Two-pass: free-form prose, then a follow-up call extracting structured fields. Rejected — doubles the latency budget for one explanation. |
| 3 | The structured path triggers **only** on the sentinel `[explain-this:ERN]` opener. A student typing their own question into the same stat-scope chat still routes to the existing markdown-prose handler. | The structured receipt is opinionated and prescriptive — it answers exactly one question ("explain how this score is built"). For every other question ("how does this compare to my friend's school?", "what jobs pay more?"), free-form prose is correct. The trigger condition keeps the two surfaces cleanly separated and avoids needing a "should this question be JSON or prose?" heuristic. | (a) Make all stat-scope chat structured. Rejected — too prescriptive; the same panel handles "ask anything about this stat" follow-ups. (b) Use a separate API endpoint for explain-receipts. Rejected — duplicates the trace-rail SSE plumbing for no benefit; the existing scope contract carries the intent. |
| 4 | ERN-only in this spec. ROI, RES, GRW, AURA each get their own spec after this one ships and the spike is validated. | The five stats have different formulas, different missing-data semantics, and (post-reshape) different scoping (AURA is institution-level, the others are per-career). Forcing one spec to cover all five would either bloat the schema with conditional fields or paper over real differences. The schema we ship in v1.0 is generic enough to fit all five (see §4 Data Model), but the prose, the system-appendix instructions, and the missing-data treatment differ enough that each stat deserves its own implementation pass. | (a) All five at once. Rejected — bloats the spec, blocks shipping ERN. (b) ERN + ROI together (most-similar formulas). Rejected — even ROI's piecewise-linear DTE map is structurally different from ERN's blend; the schema fits both but the explainer prompts diverge. |
| 5 | The Pydantic model is `extra="forbid"`. Gemma adding fields outside the schema is a **parse failure**, not silent acceptance. | The schema is the contract. If Gemma adds a `confidence_score` or `caveat` field, that means our prompt failed and we should fall back to the spike's known-good markdown path, not silently render an incomplete receipt. Strict mode catches this at the boundary. | (a) `extra="ignore"`. Rejected — masks prompt failures. (b) `extra="allow"` with a logged warning. Rejected — same outcome, more noise. |
| 6 | When JSON parsing fails for any reason (transport error, schema violation, unparseable text), the backend falls back to the **existing markdown spike path** that ships today in `ask_gemma.py`. The student gets the spike's output, never a 5xx, never an empty bubble. | The spike is the known-good baseline. Falling back to it preserves the user-facing experience while we tune the JSON path. The spike's output has known math problems, but it's a degraded experience, not a broken one. | (a) Fall back to a hardcoded canned explanation. Rejected — loses Gemma's voice and the build-specific values. (b) Fall back to the standard stat-scope free-form prose. Rejected — the user clicked "Explain this to me," they expect a structural answer; arbitrary prose is a different surface. (c) Show an error state. Rejected — fails the "graceful 200 over 5xx" rule the existing chat already follows. |
| 7 | The `score` field in the JSON gets discarded server-side and replaced with `build.career.stats.ern`. We do not even read what Gemma sent. | This is the load-bearing reliability decision: the score the student sees on the pentagon legend is the score the receipt shows. Period. Gemma cannot drift. | (a) Compare Gemma's score to the build score, log on mismatch. Rejected — adds telemetry noise without changing user behavior. (b) Compute the score server-side from the tool results and compare to the build. Rejected — the build's score is authoritative (it accounts for effort-slider adjustments, etc., that the tool result doesn't reflect). |
| 8 | The `math_line` is **rendered as a string** by the server, not as structured math fields the frontend assembles. | The math line has formatting subtleties (n/a placeholders, parens, unicode arrow `→`, the rounded score) that are tightly coupled to the explanation voice. Letting the server own the string keeps Pydantic responsible for the entire receipt shape. | (a) Send `{components: [...], operator: "+", result: 0.146, score: 2}` and let the frontend stringify. Rejected — pushes presentation logic to two places; localization (when it lands) becomes harder. |
| 9 | Trace-rail UX is **untouched**. The streaming protocol still emits `TraceTurnStart` / `TraceTurnComplete` / `TraceFinalText` / `TraceDone` events in the same order; only the `TraceFinalText.response` payload changes shape from `str` to `str \| ExplainStatReceipt`. | The trace rail is the user-facing "show the receipts" moment — it's where the student watches Gemma fetch real data live. Keeping it byte-identical to the spike means the trace-rail React component (`GemmaTrace.tsx`) does not need to change at all. | (a) Add a new event type for the structured receipt. Rejected — invents complexity; the existing `final_text` event already carries the response payload, just typed wider. (b) Replace the trace-rail component with a structured-receipt-aware version. Rejected — separates the two surfaces; we want them visually unified. |
| 10 | The `ExplainStatReceipt` schema is intentionally **generic across all five stats**. `components` is a list (length 1–N), `value_pct` is optional (so AURA's institution-level lookup can populate without a percentile), `missing_reason` is per-component (so any input can degrade gracefully), and the `score_max` field is fixed to 10 in v1.0 but parameterized for future-proofing. | The reshape spec adds AURA, which is institution-level and has different missing-data semantics than the percentile-rank-based stats. Designing the schema to accommodate AURA from day one means the future AURA-explainer spec is a prompt change + an `<ExplainStatReceipt>` props pass, not a Pydantic migration. | (a) ERN-shaped schema (two components, both required). Rejected — would force a v2.0 model the moment ROI lands (single-component DTE map). (b) Stat-typed discriminated union (`type: "ern"` vs `type: "aura"`, etc.). Rejected — premature; we don't know the actual differences yet. v1.0 ships flat and generalizes if needed. |
| 11 | The frontend renders the receipt via a **new dedicated component** `<ExplainStatReceipt>`, not by extending the existing chat-message renderer. | The receipt is structurally different from a prose bubble — it has section headings, source pills, percentile-callout typography, and missing-data treatment that don't apply to free-form replies. A dedicated component lets each surface evolve independently and keeps the markdown renderer simple. | (a) Render the receipt as serialized markdown and let the existing renderer handle it. Rejected — loses the per-section styling control that motivates this spec. (b) Render inline inside the existing message bubble container. Rejected — the receipt should feel like a "card" inside the chat, not a long message. |
| 12 | The chat-history-item TypeScript type is widened to a discriminated union: `{ kind: "text"; content: string } \| { kind: "receipt"; payload: ExplainStatReceipt }`. The renderer dispatches on `kind`. | This is the cleanest way to keep both surfaces in the same history list and ordering without sentinel strings or magic prefixes. The dispatch is exhaustive in TypeScript so future kinds (if any — see decision 4) are forced through the type system. | (a) Always store as text and parse JSON at render time. Rejected — wastes a parse and loses type safety. (b) Two parallel lists. Rejected — ordering becomes fragile. |

### Constraints

- **No data pipeline changes.** Same constraint as the pentagon-stat-reshape spec. The needed columns are already in `consumable.program_career_paths` and `consumable.occupation_profiles`.
- **No new MCP tools.** `get_career_paths` returns `cip_family_earnings_rank` and `earnings_1yr_median`; `get_occupation_data` returns `wage_percentile_overall` and `median_annual_wage`. Both are already in the `_TOOLS` allowlist for chat-time calls.
- **Backend and frontend cut over together.** The chat-history-item type widens in lockstep with the API response shape change. Half-migrated state is a runtime crash.
- **Both inference backends must work.** The smoke test in §9 verifies both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter` produce parseable JSON. If OpenRouter rejects `response_format`, the spike fallback covers it but the spec doesn't ship until both are green.
- **The existing ERN-explain spike code path stays in the codebase as the JSON-mode fallback.** It is not deleted by this spec. A future spec (after the JSON path proves stable in production usage) removes it.
- **Voice authority remains the SKILL.** The system appendix's prose-field instructions cite `.claude/skills/pentagon-stat-explanation/SKILL.md` as the source of truth for the four-section voice. Schema and voice are decoupled — the schema dictates structure, the SKILL dictates the words.

### Out of Scope

| Item | Park as |
|------|---------|
| ROI explain-receipt | Future spec `feature-explain-stat-receipt-roi.md` |
| RES explain-receipt (post-reshape blend) | Future spec `feature-explain-stat-receipt-res.md` |
| GRW explain-receipt | Future spec `feature-explain-stat-receipt-grw.md` |
| AURA explain-receipt (institution-level, missing-data heavy) | Future spec `feature-explain-stat-receipt-aura.md` |
| Structured receipts for boss / skill / build / branch / compare scopes | Different problem domain — those are conversational. Future specs only if the design pattern proves out for stats. |
| New MCP tool for stat breakdowns | Existing tools cover the data. |
| Removal of the markdown spike code path | Future cleanup spec after this one is stable in production for ≥2 weeks. |
| Localization of the math-line string format | Out of scope for v1.0. The English string is server-rendered; a `Locale` parameter to `_render_math_line` is the obvious extension point. |

---

## §3 UI/UX Design

> **Backend-only?** No — this spec ships a new React component. @fp-design-visionary fills this section BEFORE implementation begins. Pixel-perfect target.

### What's in scope for the visionary

The new `<ExplainStatReceipt>` component renders inside `GemmaChat` as the assistant's reply when the receipt path fires. Specifically the visionary owns:

1. **The receipt "card" within the chat bubble.** Background tier, padding, border treatment, max-width, how it visually distinguishes from a plain-prose Gemma reply directly above or below it in the chat history.
2. **Section typography.** The four sections (one-liner / how it works / sources / why-we-mix) each need distinct typographic weight without becoming busy. Current spike uses `### H3` + `**bold**` paragraph headers in markdown; the visionary decides whether to keep that hierarchy or compress.
3. **Component bullet rendering.** Each `StatComponent` is a row with `weight_pct` (e.g., "60%") + `label` ("your school's program rank") + the explainer text + the percentile callout + missing-data line. Visionary specifies the layout — left-rail percentage chip? Inline weight prefix? Stacked vs. inline?
4. **Percentile callout typography.** "87th percentile (out of 100 programs, this one ranks higher than about 86)" is a real on-screen text element. The number `87` and the gloss are visually distinct elements; visionary decides the treatment (data-font for the number? muted parenthetical?).
5. **The math line.** `0.6 × 0.87 + 0.4 × 0.92 → score 9/10`. This is the "show the receipts" moment. Visionary decides whether it's a code-block-styled box, a centered single-line callout, or inline with the bullets.
6. **Source pills.** "College Scorecard" and "BLS Occupational Outlook Handbook" — visionary specifies the chip / pill / badge treatment, including whether they're tappable (e.g., to surface a tooltip with the exact dataset version, which we have in tool results).
7. **Missing-data treatment.** When `value_pct === null`, `anchor_dollars === null`, or `missing_reason` is set, the row's visual weight should drop to `text-muted` and the missing-reason line should be subtle. The visionary decides exactly how subtle (italics? small caps? inline em-dash?).
8. **Score callout at top.** `### Earning Power — 9/10` is the receipt's title. The score is the headline number; treat it like one. The stat color (`var(--color-stat-ern)`) should drive the accent.
9. **Responsive behavior.** Chat panel ranges from ~480px (slide-in narrow) to ~720px (wide). The receipt has to read at all widths. Bullets may need to stack on narrow.
10. **Loading state.** While the tool loop is running, the chat shows the existing typing-dots indicator. When the structured receipt arrives, it transitions in. Visionary specifies whether there's a fade, a skeleton, or just an instant swap.

### Brightpath references

- Background tier: receipt sits inside the existing `bg-bp-mid` chat bubble; the receipt's own surface is likely `bg-bp-raised` to read as a card-within-a-card.
- Stat color: `var(--color-stat-ern)` (gold, `#F2D477`). Use for the score number, the section accent, and the trigger button on `BuildResultsScreen` (already shipped from the spike).
- Typography: `font-display` for section headings, `font-body` for prose, `font-data` for percentages/scores/math. No new fonts.
- Border / divider: existing `border-border-subtle` for inter-section separators if any; no new tokens.
- Source pills should reuse an existing chip pattern if one exists (check `frontend/src/components/ui` and `BossBand.tsx` for chip conventions).

### Accessibility

| Element | Identifier | Type | aria-label |
|---------|------------|------|------------|
| Receipt container | `data-testid="explain-stat-receipt"` | `<article role="region">` | `Earning Power explanation receipt` |
| Score callout | (visionary specifies) | (visionary specifies) | `Earning Power score: {N} out of {N_max}` |
| Component row | `data-testid="receipt-component-{ern\|roi\|res\|grw\|aura}-{0..N}"` | `<li>` | (visionary specifies) |
| Source pill | `data-testid="receipt-source-{slug}"` | `<a>` or `<button>` if tappable, `<span>` if not | `Source: {name}` |
| Missing-data line | `data-testid="receipt-missing-{component-key}"` | `<p role="note">` | (visionary specifies) |

### States to mock

- **Default** — both percentiles populated (Indiana University → CS → Software Developer).
- **Missing school rank** — `cip_family_earnings_rank === null` (Millikin → Chemistry → Food Science Technicians, the spike's failure case).
- **Missing occupation wage** — `wage_percentile_overall === null` (rare but possible for SOC codes BLS doesn't price).
- **Both missing** — degenerate but possible; receipt should still render with `score` from the build and a graceful explanation.
- **Loading** — tool calls in flight, receipt not yet rendered.
- **Fallback** — JSON parse failed; markdown-spike output renders in its place. (Visionary doesn't need to design this — it's the existing spike output. But specify how it's visually identified, if at all, so the engineer knows.)

---

## §4 Technical Specification

### Architecture Overview

The Ask Gemma chat surface (`backend/app/services/ask_gemma.py`) already routes the sentinel `[explain-this:ERN]` opener to a dedicated branch in `chat_ask` and `chat_ask_stream` (added 2026-05-02 in this same conversation, no prior spec). This spec replaces what that branch produces:

- **Today (spike):** the branch swaps in a markdown-template appendix that mandates a four-section response. Gemma writes free-form markdown; the response is rendered as plain-text in the chat.
- **After this spec:** the branch swaps in a JSON-schema appendix that mandates an `ExplainStatReceipt`-shaped JSON object. Gemma writes JSON; the backend post-processes (stamps the score, validates, builds `math_line`); the response is delivered as a structured payload; the frontend renders it via `<ExplainStatReceipt>`.

Five integration points:

1. **`gemma_client.generate_with_tools_loop`** — gains a `response_format: dict[str, Any] | None = None` kwarg that, when set, propagates to the underlying chat-completions API call. Both Ollama and OpenRouter accept `{"type": "json_object"}` here.
2. **`ask_gemma._ern_explain_appendix`** — rewritten to instruct Gemma to emit a JSON object matching the `ExplainStatReceipt` schema (the schema is included verbatim in the appendix as a structural template). The four-section voice rules from the SKILL stay; they now apply to the prose-field values inside the JSON, not to the markdown rendering.
3. **`ask_gemma._postprocess_ern_explain_receipt`** — new helper. Parses the JSON, validates via Pydantic, stamps the `score` from the build, computes `math_line` from the tool-call log, returns an `ExplainStatReceipt` object. On any failure, returns `None` and the caller falls back to the markdown-spike path.
4. **`AskResponse` and `TraceFinalText` Pydantic models** — extended so `response: str` becomes `response: str | ExplainStatReceipt`. The streaming `TraceFinalText` event carries the same union. Frontend types mirror.
5. **`<ExplainStatReceipt>` React component + `ChatHistoryItem` type widening** — new component renders the structured payload; the chat history item type becomes a discriminated union; the existing `GemmaChat` renderer dispatches on `kind`.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/models/api.py` | Modify | Add `ExplainStatReceipt`, `StatComponent`, `ReceiptSource` Pydantic models with `model_config = ConfigDict(extra="forbid")`. Widen `AskResponse.response` and `TraceFinalText.response` from `str` to `str \| ExplainStatReceipt`. |
| `backend/app/services/ask_gemma.py` | Modify | (a) Add `_RECEIPT_JSON_SCHEMA` constant — the JSON-schema-as-prose included in the system appendix. (b) Replace `_ern_explain_appendix` body with the new JSON-mode instructions (keeps function signature). (c) Add `_postprocess_ern_explain_receipt(json_str: str, build: Build, tool_call_log: list) -> ExplainStatReceipt \| None`. (d) In both `chat_ask` and `chat_ask_stream`, when `explain_ern` is true: pass `response_format={"type": "json_object"}` to the tool loop, then after the loop attempt `_postprocess_ern_explain_receipt`; on success return / yield the receipt as the response payload; on failure log a warning and fall back to the spike's existing markdown path (run the loop AGAIN without `response_format`, with the markdown appendix — the spike code stays in the file as the fallback). (e) Helper-leak stripper (`_HELPER_LEAK_RE`) continues to apply to the fallback markdown path; it does not run on JSON output (which is parsed, not rendered as text). |
| `backend/app/services/gemma_client.py` | Modify | Add `response_format: dict[str, Any] \| None = None` kwarg to `generate_with_tools_loop` and `generate_async`. Propagate to the OpenAI-compat chat-completions request body when set. Verify `logs/gemma.jsonl` records the flag. No-op when `None` (current behavior). |
| `backend/app/services/__init__.py` | Modify | Re-export the new Pydantic models if the package's public surface includes them. |
| `backend/tests/services/test_ask_gemma_explain_receipt.py` | Create | New file. Tests for `_postprocess_ern_explain_receipt`: happy path, score-from-build override, math-line construction (both percentiles present, school-rank null, occupation-wage null, both null), Pydantic-validation failures (missing field, extra field, wrong type), tool-call-log extraction edge cases (no calls, only one call, calls in either order). |
| `backend/tests/services/test_ask_gemma.py` | Modify | Add fallback test: when `_postprocess_ern_explain_receipt` returns `None`, the response falls through to the markdown spike path and the response is a string, not an `ExplainStatReceipt`. Existing ERN-explain integration test (if added during the spike) updates to the new payload shape. |
| `backend/tests/services/test_gemma_client.py` | Modify | Add: `response_format` kwarg propagates to the chat-completions request body; `None` is a no-op; logging captures the flag. |
| `backend/app/routers/chat.py` (or wherever `/chat/ask` and `/chat/ask/stream` live) | Modify | The router serializes `AskResponse` and `TraceFinalText`; verify the union type roundtrips correctly through FastAPI's response-model serializer (Pydantic v2 should JSON-encode the `ExplainStatReceipt` branch as a nested object). |
| `frontend/src/types/chat.ts` (or wherever `ChatHistoryItem` lives — likely `frontend/src/components/menu/GemmaChat.tsx` inline) | Modify | Add TypeScript discriminated union: `type ChatHistoryItem = { role: "user" \| "assistant"; kind: "text"; content: string } \| { role: "assistant"; kind: "receipt"; payload: ExplainStatReceipt }`. Add `ExplainStatReceipt`, `StatComponent`, `ReceiptSource` types mirroring the backend models. |
| `frontend/src/api/menu.ts` (or wherever the chat-stream client lives) | Modify | When the SSE `final_text` event arrives, branch on the response shape: string → existing path; object matching the receipt shape → push a `{ kind: "receipt", payload }` history item. The runtime check uses a Zod schema (preferred) or a manual type guard on the presence of the `score` + `components` fields. |
| `frontend/src/components/menu/GemmaChat.tsx` | Modify | Renderer dispatches on `kind`. The existing prose-message renderer stays untouched. The "receipt" branch renders `<ExplainStatReceipt payload={item.payload} />`. |
| `frontend/src/components/menu/ExplainStatReceipt.tsx` | Create | New React component. Props: `{ payload: ExplainStatReceipt }`. Pixel-perfect implementation of @fp-design-visionary's §3 spec. Handles all states: default, missing-data, both-missing. Uses Brightpath tokens; no inline color values. |
| `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | Create | Vitest tests covering all states from §3 plus accessibility (data-testid presence, aria-label on container, role attributes). Snapshot test for the default state. |
| `frontend/src/lib/zodSchemas.ts` (or new file `frontend/src/types/explainReceipt.ts`) | Create or Modify | Zod schema for `ExplainStatReceipt` runtime validation at the SSE boundary. Exports both the Zod schema and the inferred TypeScript type (single source of truth for the frontend type). |
| `docs/reference/stat-display-surfaces.md` | Modify | Add a new §1i entry for `<ExplainStatReceipt>` listing it as ✅ wired (the second entry tagged ✅ — first is §1a popover trigger). Cross-reference the new component file path and the "explain-this:ERN" sentinel. |
| `.claude/skills/pentagon-stat-explanation/SKILL.md` | Modify | Add a new line under "Companion reference" pointing to `frontend/src/components/menu/ExplainStatReceipt.tsx` as the rendering authority. The voice rules stay where they are; the SKILL just gains a pointer to where its prose-field outputs render. |

### Data Model Changes

New Pydantic models in `backend/app/models/api.py`:

```python
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ReceiptSource(BaseModel):
    """A data source citation rendered as a pill in the receipt UI."""
    model_config = ConfigDict(extra="forbid")

    label: str = Field(
        description="Human-readable category, e.g. 'Graduate earnings'."
    )
    name: str = Field(
        description=(
            "Full source name, e.g. 'College Scorecard "
            "(U.S. Department of Education)'."
        )
    )


class StatComponent(BaseModel):
    """One mixed-in piece of a stat's score (e.g. the 60% school rank
    piece of ERN, or the 40% occupation wage piece). Generic across all
    five stats: a stat with one component (e.g. GRW) emits a length-1
    list; an institution-level stat with no per-career percentile (AURA)
    sets value_pct=None and surfaces the same missing_reason field."""
    model_config = ConfigDict(extra="forbid")

    weight_pct: int = Field(
        ge=0,
        le=100,
        description=(
            "Percentage weight in the formula (e.g. 60 for the 60% school "
            "rank piece). Sum across components <= 100."
        ),
    )
    label: str = Field(
        description=(
            "Plain-English component name, e.g. 'your school's program rank'."
        )
    )
    explainer: str = Field(
        description=(
            "Gemma-written 1-2 sentence explanation of what this component "
            "measures and where the percentile comes from. Voice rules from "
            "pentagon-stat-explanation/SKILL.md apply."
        )
    )
    value_pct: int | None = Field(
        default=None,
        ge=0,
        le=100,
        description=(
            "Percentile rank (0-100). Null when the underlying input is "
            "missing — the renderer must read this as 'we don't have this "
            "yet,' not as zero."
        ),
    )
    anchor_text: str = Field(
        description=(
            "The named entity this percentile attaches to, e.g. "
            "'Indiana University Computer Science grads' or "
            "'Software Developer'. Used in the bullet's lead phrase."
        )
    )
    anchor_dollars: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Dollar amount associated with the anchor (median earnings, "
            "median wage). Null when missing. Server-stamped from the "
            "tool result, never from Gemma."
        ),
    )
    missing_reason: str | None = Field(
        default=None,
        description=(
            "When value_pct or anchor_dollars is null, this string explains "
            "why in plain English (e.g. 'no median earnings reported for "
            "this program yet'). Server-stamped, not from Gemma."
        ),
    )


class ExplainStatReceipt(BaseModel):
    """Structured explainer-receipt payload for one of the five pentagon
    stats. Generic across ERN, ROI, RES, GRW, AURA — only ERN populates
    in this spec."""
    model_config = ConfigDict(extra="forbid")

    stat_code: Literal["ERN", "ROI", "RES", "GRW", "AURA"] = Field(
        description="Pentagon stat code; mirrors the AskScope target_id."
    )
    stat_name: str = Field(
        description=(
            "Plain-English stat name, e.g. 'Earning Power'. Mirrors "
            "ask_gemma._STAT_ALIAS but Pydantic-typed."
        )
    )
    score: int = Field(
        ge=1,
        le=10,
        description=(
            "The student's score on this stat. Server-stamped from "
            "build.career.stats.<stat>; whatever Gemma emits in this "
            "field is overwritten unconditionally (see §2 Decision 7)."
        ),
    )
    score_max: int = Field(
        default=10,
        description=(
            "Maximum possible score. Fixed at 10 in v1.0; parameterized "
            "for future stat-system changes."
        ),
    )
    one_liner: str = Field(
        description=(
            "Gemma-written one-sentence definition of the score. Voice "
            "rules from pentagon-stat-explanation/SKILL.md apply."
        )
    )
    components: list[StatComponent] = Field(
        min_length=1,
        max_length=5,
        description=(
            "The mixed-in pieces of the score. ERN uses 2; ROI uses 1; "
            "AURA uses 1 with no value_pct (institution-level)."
        ),
    )
    math_line: str = Field(
        description=(
            "Server-rendered math expression showing how the components "
            "combine to the score, e.g. '0.6 × 0.87 + 0.4 × 0.92 → "
            "score 9/10'. Null inputs render as 'n/a'. Server-stamped, "
            "never from Gemma."
        )
    )
    sources: list[ReceiptSource] = Field(
        min_length=1,
        description="Data sources rendered as pills in the receipt UI.",
    )
    why_mix_paragraph: str = Field(
        description=(
            "Gemma-written ~3-sentence 'two students contrast' paragraph "
            "explaining why the score is structured the way it is. Voice "
            "rules from pentagon-stat-explanation/SKILL.md apply."
        )
    )
```

`AskResponse` and `TraceFinalText` (existing models in same file) widen the `response` field:

```python
class AskResponse(BaseModel):
    response: str | ExplainStatReceipt
    tool_calls: list[ToolCall]


class TraceFinalText(BaseModel):
    type: Literal["final_text"] = "final_text"
    response: str | ExplainStatReceipt
```

No Iceberg or DuckDB schema changes. No new MCP tool surfaces.

### Service Changes

New helper in `backend/app/services/ask_gemma.py`:

```python
async def _postprocess_ern_explain_receipt(
    json_str: str,
    build: Build,
    tool_call_log: list[gemma_client.ToolCallTurn],
) -> ExplainStatReceipt | None:
    """Parse Gemma's JSON, validate, and stamp server-controlled fields.

    Returns None on any failure — caller falls back to the markdown spike
    path. Failures logged at WARNING level with enough context to debug
    a bad prompt run (build_id, json prefix, exception type).

    Server-controlled fields (overwritten regardless of Gemma's output):
      - score: from build.career.stats.ern (Decision 7)
      - math_line: rendered from tool_call_log values (Decision 8)
      - components[*].value_pct: from get_career_paths +
        get_occupation_data results (Gemma can suggest, server validates
        against actual tool output)
      - components[*].anchor_dollars: same — from tool result
      - components[*].missing_reason: server-set when value_pct or
        anchor_dollars is null

    Gemma-controlled fields (preserved as-is from the parsed JSON,
    after Pydantic validation):
      - one_liner
      - components[*].explainer
      - components[*].label (validated against an allowlist per stat
        to prevent drift, e.g. ERN must use "your school's program
        rank" / "this career's pay rank")
      - why_mix_paragraph
    """
```

Existing helper `_ern_explain_appendix(career: CareerOutcome) -> str` keeps its signature; the body is rewritten to instruct Gemma to emit JSON matching the schema. The four-section voice rules from `pentagon-stat-explanation/SKILL.md` stay; they now apply to the prose-field values inside the JSON.

`gemma_client.generate_with_tools_loop` signature change:

```python
async def generate_with_tools_loop(
    *,
    system: str,
    user: str,
    tools: list[dict[str, Any]],
    dispatch: ToolDispatch,
    max_turns: int = 5,
    max_wall_time_s: float = 30.0,
    temperature: float = 0.5,
    max_tokens: int = 1200,
    extra: dict[str, Any] | None = None,
    on_turn_start: ToolStartCallback | None = None,
    on_turn_event: ToolTurnCallback | None = None,
    response_format: dict[str, Any] | None = None,  # NEW
) -> tuple[str, list[ToolCallTurn]]: ...
```

Frontend `<ExplainStatReceipt>` props:

```typescript
interface ExplainStatReceiptProps {
  payload: ExplainStatReceipt;
}
```

### Gemma-touching extra discipline

This spec modifies `gemma_client.generate_with_tools_loop` (a public Gemma call site), adds a new `_postprocess_ern_explain_receipt` consumer, and changes the `ask_gemma._ern_explain_appendix` system-prompt content. The call-site discipline:

| Concern | Behavior |
|---------|----------|
| Fallback when transport fails | Existing: empty string from the loop → `fallback_text("chat_unavailable", locale)` 200 response. Unchanged. |
| Fallback when JSON parsing fails | NEW: `_postprocess_ern_explain_receipt` returns None → log warning → re-run the loop without `response_format` and with the markdown-spike appendix → return string response. The spike's known-good output covers the failure case. |
| Fallback when both attempts fail | The second attempt is the existing spike path with its existing fallbacks (transport failure, turn-cap exhaustion, wall-time). Same `chat_unavailable` 200 response. |
| `logs/gemma.jsonl` capture | Both calls captured. The first call records `response_format: {"type": "json_object"}` and the JSON string output. The fallback call records the markdown output. The fallback path is identifiable via the existing `extra` field plus a new `extra["fallback_after_json_parse_failure"] = True`. |
| `INFERENCE_BACKEND=ollama` | Ollama supports `response_format` on the OpenAI-compat chat endpoint as of v0.5+. Verify shipped Ollama version meets this; if older, the spec REQUIRES upgrading the dev-stack Ollama version (note this in §6 implementation log). |
| `INFERENCE_BACKEND=openrouter` | OpenRouter supports `response_format` via the OpenAI-compat passthrough; some models don't enforce it strictly. For Gemma 4 specifically (`google/gemma-4-26b-a4b-it`), verify behavior in the smoke test in §9. If OpenRouter's Gemma 4 doesn't honor `response_format` strictly, the JSON path falls back to markdown for OpenRouter calls — the user-facing experience degrades but does not break. |
| Concurrency for cloud demo | One JSON-mode call per "Explain this to me" click. Same Gemma semaphore limits as existing chat. No new contention. |
| Token-budget impact | The JSON output is roughly the same byte count as the markdown output (~600-900 tokens). `max_tokens=_ERN_EXPLAIN_MAX_TOKENS=1500` (already set by the spike) covers both. No change. |

### Testing Impact Analysis

> **Search performed:** `rg "explain_ern\|_ERN_EXPLAIN\|_ern_explain_appendix" backend/ frontend/` — current spike has no test coverage. The blast radius is the entire ERN-explain code path, which means new tests in this spec are creating coverage rather than modifying it.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_stat_scope_*` (existing stat-scope tests) | Low | The free-form stat-scope path is unchanged by this spec. Risk is non-zero only if the test fixtures depend on `_TEMPERATURE` or `_ERN_EXPLAIN_*` constants, which they should not. |
| `backend/tests/services/test_gemma_client.py` | `test_generate_with_tools_loop_*` | Low | Adding a kwarg with a `None` default does not change existing call signatures. Tests should continue to pass without modification. |
| `frontend/src/components/menu/GemmaChat.test.tsx` | All assistant-message rendering tests | Medium | Widening `ChatHistoryItem` to a discriminated union may break tests that construct history items as bare objects without a `kind` field. Authorized to update fixtures to include `kind: "text"` on existing test data. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `frontend/src/components/menu/GemmaChat.test.tsx` (multiple tests) | Add `kind: "text"` to existing chat-history fixtures | The history-item type widens; existing fixtures need the discriminator field. Pure additive change to test data. |
| `backend/tests/services/test_ask_gemma.py::test_chat_ask_ern_explain_*` (if any exist from the spike) | Update assertions on response payload shape from `str` to `ExplainStatReceipt` | The spike was unspec'd; if it shipped with tests, this spec changes the response shape. |

#### Confirmed Safe

These tests must NOT break. If they fail, escalate per §10:

- `backend/tests/services/test_ask_gemma.py::test_chat_ask_boss_scope_*` — boss scope is unchanged.
- `backend/tests/services/test_ask_gemma.py::test_chat_ask_skill_scope_*` — skill scope is unchanged.
- `backend/tests/services/test_ask_gemma.py::test_chat_ask_build_scope_*` — build scope is unchanged.
- `backend/tests/services/test_ask_gemma.py::test_chat_ask_branch_*` — branch scope is unchanged.
- `backend/tests/services/test_ask_gemma.py::test_strip_thinking_prefix*` — `_strip_thinking_prefix` is reused for the markdown fallback path; no signature change.
- `backend/tests/services/test_ask_gemma.py::test_helper_leak_*` (if any exist for `_HELPER_LEAK_RE`) — same.
- `backend/tests/services/test_voice_contract.py` — the system-base voice rules are unchanged; the explain-receipt appendix rules are LOCAL to that turn and do not register against the global voice contract.
- `frontend/src/components/menu/GemmaChat.test.tsx::test_message_rendering_text` — plain-text message rendering must continue to work identically.
- All `BuildResultsScreen.test.tsx` tests — the "✦ Explain this to me" link from the spike is unchanged; only the response shape changes downstream.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_happy_path` | Valid Gemma JSON → parsed `ExplainStatReceipt` with all fields populated. Both percentiles present. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_overrides_score_from_build` | Gemma emits `score: 99` (wrong); receipt's score equals `build.career.stats.ern` (e.g., 7). |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_school_rank_null` | `cip_family_earnings_rank` is null in tool results → component's `value_pct` is null, `missing_reason` is set, `math_line` renders `0.6 × n/a + 0.4 × X.YZ → score N/10`. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_occupation_pct_null` | `wage_percentile_overall` is null → component's `value_pct` is null, `missing_reason` set, `math_line` shows `n/a` for the 40% piece. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_both_null` | Both percentiles null → receipt still parses, math_line is `0.6 × n/a + 0.4 × n/a → score N/10`. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_invalid_json_returns_none` | Unparseable string → returns None. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_extra_field_rejected` | Gemma adds `confidence: 0.8` to the JSON → Pydantic `extra="forbid"` rejects → returns None. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_missing_required_field` | Gemma omits `why_mix_paragraph` → returns None. |
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_ern_explain_falls_back_on_parse_failure` | When `_postprocess_ern_explain_receipt` returns None, response is the markdown-spike string output. Stream variant covered by sister test. |
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_stream_ern_explain_emits_receipt_in_final_text` | `TraceFinalText.response` carries an `ExplainStatReceipt` object, not a string, when the JSON path succeeds. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_response_format_propagates_to_chat_request` | When `response_format={"type": "json_object"}` is passed to `generate_with_tools_loop`, the underlying chat-completions request body includes the field. None default is a no-op. |
| P0 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_renders_default_state` | All sections render with the expected text content. Snapshot. |
| P0 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_renders_missing_school_rank` | Missing-reason row renders, percentile shows "—", row visual weight reduces (verify className). |
| P0 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_renders_score_color_token` | Score callout uses `var(--color-stat-{stat_code})` — verify via inline-style or className inspection. |
| P0 | `frontend/src/components/menu/GemmaChat.test.tsx` | `test_dispatches_receipt_to_explain_stat_component` | Pushing a `{ kind: "receipt", payload }` history item renders `<ExplainStatReceipt>`, not the prose renderer. |
| P1 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_label_allowlist` | Gemma writes `label: "the school number"` (off-script) → server normalizes to the allowlisted "your school's program rank" or returns None (decision: normalize). |
| P1 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_math_line_format_unicode_arrow` | The math line uses `→` (U+2192), not `->`, for consistency with the rest of the product copy. |
| P1 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_renders_responsive_narrow` | Component renders without overflow at the 480px breakpoint (use `vitest-environment-jsdom` viewport simulation). |
| P1 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_accessibility_attributes` | `data-testid`, `role="region"`, `aria-label` per §3 accessibility table. |
| P2 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_logs_warning_with_context` | Failed parse logs WARNING with build_id + JSON prefix. Visible in `logs/gemma.jsonl` for debugging bad prompt runs. |
| P2 | `frontend/src/lib/zodSchemas.test.ts` (new) | `test_explain_stat_receipt_zod_matches_pydantic` | Round-trip a known-good payload through both Pydantic (backend serialize) and Zod (frontend parse); must match. Catches schema drift between the two. |

#### Test Data Requirements

- **Fixtures.** Three canonical builds covering the missing-data matrix:
  1. *Both percentiles present* — Indiana University-Bloomington → Computer Science → Software Developer (the "happy path" build).
  2. *School rank null* — Millikin University → Chemistry → Food Science Technicians (the spike's failure case — production data).
  3. *Both null* — synthesized for unit tests; not needed in integration tests.
- **Mocks.** Mock Gemma client responses for: valid JSON, malformed JSON, Pydantic-rejected JSON (extra field), Pydantic-rejected JSON (missing field), Pydantic-rejected JSON (wrong type), JSON with hallucinated `score: 99`.
- **Tool result mocks.** Mock `get_career_paths` and `get_occupation_data` MCP responses with the four percentile-null permutations.
- **State.** No new env vars. `INFERENCE_BACKEND` is already set per dev environment; both backends covered by smoke verification (§9), not unit tests.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING
#### Findings
[Filled in by @fp-architect — Pydantic schema correctness, JSON-mode plumbing through `gemma_client`, fallback logic robustness, frontend-backend type contract, generic-across-stats schema design.]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @genai-architect Review
**Status:** PENDING
#### Findings
[Filled in by @genai-architect — JSON-mode prompt design, schema compatibility with Gemma 4 on both Ollama and OpenRouter, system-appendix instruction quality, voice-contract impact (does the JSON path drift from the SKILL's voice rules in measurable ways?).]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review
**Status:** SKIPPED — no pipeline, schema, or data-formula changes. Existing `cip_family_earnings_rank` and `wage_percentile_overall` columns are read; no transformation, no re-promotion.

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
[Brightpath token compliance for `<ExplainStatReceipt>`, dark-first, missing-data state visual treatment, focus state, responsive behavior at 480px and 720px breakpoints.]

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Filled in by reviewer — security (JSON injection?), performance (parser overhead), error handling (fallback paths), architectural consistency with existing Ask Gemma patterns.]
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

### Smoke Verification (manual)
| Backend | "Explain this to me" click → JSON receipt rendered? | Both tools called in trace? | Score matches build pentagon? | Math line correct? |
|---------|------|------|------|------|
| `INFERENCE_BACKEND=ollama` | | | | |
| `INFERENCE_BACKEND=openrouter` | | | | |

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

[Final thoughts, lessons learned, follow-up items. Specifically: did the JSON path produce reliable receipts across both inference backends? Was the parse-failure fallback rate acceptable in dogfood usage? Should the schema's `extra="forbid"` strictness be loosened for production-tolerance? When can the markdown spike fallback be removed?]
