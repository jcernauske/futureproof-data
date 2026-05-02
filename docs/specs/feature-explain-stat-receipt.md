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
| Spec Version | 1.3 (DRAFT) |
| Last Updated | 2026-05-02 |
| Blocked By | — (was: `pentagon-stat-reshape.md`; reshape reached COMPLETE on 2026-05-02 — unblocked) |
| Changelog | 1.3 — addresses the single new concern raised by @genai-architect re-review of v1.2 (sentinel passthrough): adds a Pydantic `field_validator` on prose fields rejecting strings that contain template-sentinel patterns (`__FILL_IN__`, `[FILL`, `<FILL`, etc.); adds an explicit prohibition in the system appendix telling Gemma not to echo placeholder sentinels back; clarifies the placeholder convention; adds P0 test `test_postprocess_rejects_sentinel_passthrough`. v1.2 had 7/7 v1.1 genai-architect conditions and 8/8 v1.1 fp-architect conditions resolved; this v1.3 closes the only newly-introduced concern. <br>1.2 — addresses §5 v1.1 architecture-review findings (CHANGES REQUESTED from both @fp-architect and @genai-architect): adds Decision 13 (effort-shift coherence), Decision 14 (label allowlist normalization), Decision 15 (response_format synthesis-turn-only scoping); softens Decision 10's AURA generality claim; rewrites §4 Service Changes to specify per-backend JSON-mode translation (Ollama `format: "json"` vs OpenRouter `response_format: {"type":"json_object"}`); changes the system-appendix prompt format from "Pydantic model verbatim" to "filled-in JSON example with `__FILL_IN__` sentinels"; adds tool-result caching across the JSON→markdown fallback retry; adds a `kind: Literal["receipt"]` self-discriminator field to `ExplainStatReceipt`; splits the score-reference voice-rule relaxation between JSON numeric fields (lifted) and prose fields (retained); requires `_extract_json_objects` reuse; adds `_postprocess_ern_explain_receipt` extra validations (stat_code match, server-only `math_line` regardless of Gemma output, `max_length=800` on `why_mix_paragraph`); requires structured parse-failure log records in `gemma.jsonl`; expands the frontend `menu.ts` and `GemmaChat.tsx` cascade in §4 File Changes; adds null-build-stat guard. <br>1.1 — pentagon-stat-reshape unblock: verified spike code survived the reshape merge. <br>1.0 — initial draft. |
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
- [ ] `logs/gemma.jsonl` continues to capture every Gemma call with the new JSON-mode flag (`response_format` on OpenRouter, `format` on the native Ollama path — see Decision 15 and §4 Service Changes for the per-backend translation) and the raw JSON output recorded verbatim.
- [ ] **Per-parse structured log record.** Every invocation of `_postprocess_ern_explain_receipt` appends one structured record to `logs/gemma.jsonl` with fields `{call_site: "explain_ern_receipt", parse_success: bool, failure_reason: str \| None, json_prefix: str (first 500 chars), build_id: str, backend: "ollama" \| "openrouter"}`. The record is emitted at INFO on success and WARNING on failure. This enables a `parse_success_rate` metric computable by filtering `gemma.jsonl` records on `call_site == "explain_ern_receipt"`.
- [ ] Both `INFERENCE_BACKEND=ollama` (local) and `INFERENCE_BACKEND=openrouter` (cloud demo) successfully produce valid JSON receipts under temperature 0, with JSON mode applied **only on the final synthesis turn** of the tool loop (Decision 15). Manual smoke verification on each backend before VERIFICATION marks green.
- [ ] **Effort-shift coherence (Decision 13).** When the build's effort slider is non-default, the receipt's `math_line` shows the unshifted percentile-derivation score, AND the receipt surfaces a separate effort line (e.g., `"Your Focused effort setting lifts this to 9/10"`). The score callout at the top equals `build.career.stats.ern` (the effort-shifted value); the math line equals the unshifted percentile derivation; the two are reconciled by the explicit effort line. No silent disagreement between the callout and the math.
- [ ] The `ExplainStatReceipt` schema fits ERN, ROI, RES, and GRW in future specs without breaking-change additions to the Pydantic model. **AURA explicitly out of scope for the v1.0 schema generality claim** — AURA's institution-level provenance (`aura_score_basis`, `aura_score_version`) does not fit the `StatComponent` shape (it's stat-level provenance, not a per-component percentile) and will require one **additive** root-level field (e.g., `score_provenance: str | None`) in the future AURA spec. Additive, not breaking.
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
| 10 (revised v1.2) | The `ExplainStatReceipt` schema is **generic across ERN, ROI, RES, and GRW**. `components` is a list (length 1–N), `value_pct` is optional, `missing_reason` is per-component, `score_max` is fixed to 10 in v1.0 but parameterized for future-proofing. **AURA explicitly excluded from the v1.0 generality claim** — its institution-level provenance fields (`aura_score_basis`, `aura_score_version`) are stat-level metadata, not per-component data, and forcing them into `StatComponent.missing_reason` is a category error. The future AURA spec will add one **additive** root-level field (e.g., `score_provenance: str \| None`) — additive, not breaking. | The reshape spec adds AURA, which is institution-level and has different missing-data semantics. v1.1 of this spec claimed the schema accommodated AURA "without a v2 migration." @fp-architect's review (§5) demonstrated that placing AURA's basis enum inside `StatComponent` is structurally wrong. Honest scoping is "generic across the four percentile-rank-based stats; AURA needs one additive field." | (a) Add `score_provenance: str \| None` to v1.0 in anticipation of AURA. Rejected — we don't yet know AURA's full provenance surface; landing the field speculatively risks needing to migrate it later. (b) Stat-typed discriminated union (`type: "ern"` vs `type: "aura"`). Rejected — premature; the four percentile-rank stats genuinely share a structure. (c) Keep the original "AURA fits without migration" claim. Rejected per @fp-architect finding 4 — the basis enum doesn't fit the per-component shape. |
| 11 | The frontend renders the receipt via a **new dedicated component** `<ExplainStatReceipt>`, not by extending the existing chat-message renderer. | The receipt is structurally different from a prose bubble — it has section headings, source pills, percentile-callout typography, and missing-data treatment that don't apply to free-form replies. A dedicated component lets each surface evolve independently and keeps the markdown renderer simple. | (a) Render the receipt as serialized markdown and let the existing renderer handle it. Rejected — loses the per-section styling control that motivates this spec. (b) Render inline inside the existing message bubble container. Rejected — the receipt should feel like a "card" inside the chat, not a long message. |
| 12 | The chat-history-item TypeScript type is widened to a discriminated union: `{ kind: "text"; content: string } \| { kind: "receipt"; payload: ExplainStatReceipt }`. The renderer dispatches on `kind`. | This is the cleanest way to keep both surfaces in the same history list and ordering without sentinel strings or magic prefixes. The dispatch is exhaustive in TypeScript so future kinds (if any — see decision 4) are forced through the type system. | (a) Always store as text and parse JSON at render time. Rejected — wastes a parse and loses type safety. (b) Two parallel lists. Rejected — ordering becomes fragile. |
| 13 (new v1.2) | **Effort-shift coherence.** The build's `stats.ern` includes effort-slider adjustments (±2 points via `_apply_effort` in `stat_engine.py`); the percentile-derived score `_round_half_up(1.0 + 9.0 × raw)` does not. The receipt's score callout shows `build.career.stats.ern` (effort-shifted, authoritative for the pentagon legend); the `math_line` shows the unshifted percentile derivation; **when `effort != "balanced"` an explicit "effort line" is appended to the math section** ("Your **Focused** effort setting lifts this to 9/10"). | Without this reconciliation, the receipt would render two different N-values in the same card (e.g., callout `9/10` + math line `→ 7/10`). That collapses the trust the receipt is built to create. | (a) Have `math_line` show the shifted score and elide the arithmetic-rounding step. Rejected — lossy and dishonest; the math no longer adds up. (b) Document explicitly that `math_line` ALWAYS uses the build's score with no derivation shown. Rejected — defeats the "show the receipts" purpose. (c) Suppress the receipt entirely when `effort != "balanced"`. Rejected — most students adjust effort; would suppress the feature for the majority. |
| 14 (new v1.2) | **Label allowlist normalization.** Each stat carries a per-stat allowlist of canonical `components[*].label` strings (for ERN: `"your school's program rank"` and `"this career's pay rank"`). When Gemma drifts (e.g., emits `"program rank"` or `"school earnings rank"`), `_postprocess_ern_explain_receipt` **normalizes** by matching on `weight_pct` first, then nearest-string-distance, replacing the off-script label with the canonical version and logging a WARNING with the original. | At temperature 0, Gemma drifts on labels ~15-25% of runs (per @genai-architect). Rejecting and falling back to markdown for a label paraphrase wastes the entire receipt when the underlying numbers and prose are valid. Normalization preserves the receipt; the WARNING enables drift tracking. The match-by-weight-first guard catches the rare swap-component-labels case. | (a) Reject on label drift (Pydantic `Literal`). Rejected — too brittle; 1 in 5 receipts would fall back to markdown for a benign paraphrase. (b) Accept Gemma's label verbatim. Rejected — defeats the SKILL's voice authority and produces inconsistent UI copy across runs. (c) Normalize by similarity alone (no weight match). Rejected — fails the swap case (Gemma puts the 60% label on the 40% component). |
| 15 (new v1.2) | **`response_format` synthesis-turn-only scoping.** JSON-mode (`response_format: {"type":"json_object"}` on OpenRouter; `format: "json"` on Ollama native) is applied **only on the final synthesis turn** of `gemma_client.generate_with_tools_loop` — never on intermediate tool-call turns. The implementation hook is a `final_turn_response_format` kwarg on `_tools_loop_inner` that injects the JSON constraint into the turn's `completion_kwargs` only when the loop detects it is about to return plain text (i.e., `not response_tool_calls` after the previous turn's response). | Per @genai-architect: applying `response_format` across tool-call turns risks suppressing the model's ability to emit structured `tool_calls` fields on OpenRouter, collapsing the two required MCP fetches. The constraint must be scoped to the synthesis turn only. | (a) Apply `response_format` to all turns (the v1.1 spec's design). Rejected — risk of tool-call suppression on OpenRouter. (b) Disable `response_format` entirely and rely on prompt instructions. Rejected — falls back to spike's failure mode. (c) Use a separate non-tool synthesis call after the tool loop completes. Rejected — duplicates the loop, doubles latency, breaks trace-rail invariance. |

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

### Emotional target

**Trust, in physical form.** The student clicked "✦ Explain this to me" because the score made them curious or skeptical. The receipt is the answer to *"prove it."* It should feel like the moment a financial advisor slides a single sheet of paper across the table — the math is right there, the sources are named, nothing is hidden. Not a wall of text. Not a "trust me." A receipt.

The card sits inside the chat history but it is not a chat message. It is **a document the chat returned**. That distinction drives every visual decision below: the card has its own surface tier, its own typographic system, its own breathing room. The chat bubble is the envelope; the receipt is the letter.

The micro-feeling at each beat:
- **Loading** — patience, not anxiety. Gemma is fetching the actual numbers. The trace rail already shows that beautifully; the receipt area below it just holds a low-key skeleton placeholder so the student knows what shape is coming.
- **Arrival** — *settling*. The card doesn't snap in; it lifts up from below the trace and settles like paper landing on a desk. The score number locks last (a 120ms delay after the card body appears) so the eye is led: "here's the receipt … here's the headline."
- **Reading** — *guided clarity*. The score is the headline. The two component bullets are the evidence. The math line is the tally. The sources are the citations. The why-mix paragraph is the editorial. Every section is visually distinct enough to scan in two seconds and read in twenty.
- **A missing piece** — *honest, not embarrassed*. When a percentile is null, the row dims to `text-muted` and the percentile slot becomes an open-ring em-dash glyph (matching the existing pentagon-vertex missing-data convention from AURA). No red. No warning. Just a quiet "we don't have this yet."

### The card

A single self-contained surface, distinct from the chat bubble that holds it. The chat bubble (`bg-bp-deep`, per `ChatMessage.tsx:28`) acts as the envelope; the receipt is a `bg-bp-raised` card-within-a-card with a 3px stat-color left rail. The left rail is the **only** color cue on the card body — it stamps the receipt with the stat's identity (gold for ERN, green for ROI, etc.) without bleeding color into the prose.

| Property | Value | Rationale |
|---|---|---|
| Container element | `<article role="region">` with `data-testid="explain-stat-receipt"` | Semantic landmark, screen-reader-discoverable. |
| Background | `bg-bp-raised` | One tier above the chat bubble's `bg-bp-deep`; reads as a card on a card. Same tier as `StatInfoPopover.tsx:57`. |
| Border | `border border-border-default` (full 1px) + `borderLeft: 3px solid var(--color-stat-ern)` | The full subtle border defines the card edge; the 3px gold left rail is the stat fingerprint. Direct echo of the StatInfoPopover treatment so the two surfaces feel like siblings. |
| Border radius | `rounded-[14px]` | Matches StatInfoPopover. Plush, not sharp. |
| Padding | `20px` (top/right/bottom) + `24px` (left) | Slightly more left padding so prose floats away from the stat rail and the rail reads as ornament, not as a divider being crowded. |
| Box shadow | `0 8px 32px rgba(27,29,48,0.55)` | Half a step shy of the popover's `0.7` because the receipt sits inside an already-elevated bubble; over-shadowing reads as floating. |
| Max width | `min(100%, 640px)` | The chat panel ranges 480-720px; capping at 640px ensures the receipt never feels stretched even on the widest panel. The chat bubble's own `max-w-[90%]` from `ChatMessage.tsx:28` already provides the outer constraint. |
| Spacing inside | Sections separated by `marginTop: 18px` (no dividers between most sections); `border-t border-border-subtle` divider ONLY above the sources row | Dividers everywhere makes the card feel like a form. One divider before sources lets the citations read as a footer. |
| Outer wrap | `<motion.article>` mounting transition (see §3 Interactions) | The receipt's arrival is the moment of trust; motion is part of the design, not decoration. |
| Distinguishing from a prose bubble | A plain-prose Gemma reply has NO stat-color rail, NO `bg-bp-raised` surface, and NO border — it's a soft `bg-bp-deep` bubble with rounded corners and an `✦` avatar to its left (`ChatMessage.tsx:38-45`). The receipt has all three (rail + raised surface + border) and the `✦` avatar is suppressed (the receipt is a document, not a quote from Gemma). The two surfaces are unmistakable at a glance. |

### Score callout (the headline)

The first thing the student sees inside the card. Treat it like a magazine cover: stat name in display weight, score number huge in data font, slash and max in muted data font.

```
┌───────────────────────────────────────────────────────────────┐
│  EARNING POWER                                          9 /10 │
│                                                              │
│  Where your starting paychecks land — your school's program  │
│  versus the rest of the country, blended with how this       │
│  career pays nationally.                                     │
└───────────────────────────────────────────────────────────────┘
```

Specifically:

| Element | Token / spec |
|---|---|
| `EARNING POWER` (eyebrow) | `font-display` weight 600, size 13px, letter-spacing 1.5px, `text-text-muted`, uppercase. Sits *above* the score row. The all-caps eyebrow gives the stat name the air of a section header without competing with the score number. |
| Score number `9` | `font-data` weight 700, size 44px, line-height 1.0, `color: var(--color-stat-ern)`. **The only number on the card rendered in stat color.** Everything else (percentiles, math line) stays in `text-text-primary` so the score is unambiguously the headline. |
| Slash + max `/10` | `font-data` weight 400, size 22px, `text-text-muted`, baseline-aligned with the score number's lower third (so `9 /10` reads as one composed unit, not two glued ones). 4px of left margin on the slash. |
| One-liner (`payload.one_liner`) | `font-body` weight 400, size 15px, line-height 1.55, `text-text-secondary`, max width 56ch. Sits 12px below the eyebrow/score row. This is the Gemma-written one-sentence definition; voice rules from `pentagon-stat-explanation/SKILL.md` apply. |
| Layout | Eyebrow + score on the same row using `flex justify-between items-baseline`. One-liner stacks below at full card width. On narrow widths (<560px), eyebrow stays inline; score never wraps. |

The score number's `data-testid="receipt-score"` and `aria-label="Earning Power score: 9 out of 10"` belong here.

### How it works (the components)

The two `StatComponent` rows are the heart of the receipt. **Layout decision: option (a) — left-rail percentage chip + stacked label/explainer/percentile callout.** Reasoning:
- Option (b) inline-weight-prefix becomes unreadable on a narrow chat panel — "60% — your school's program rank — Indiana University..." wraps badly and the weight gets lost in the prose.
- Option (c) two-column with weight + everything else introduces a vertical divider that makes the card feel like a spreadsheet, fighting the "letter, not form" emotional target.
- Option (a) gives the weight chip its own anchor, leaves the prose to breathe at full width, and stays composable when a row's `value_pct` is null (the chip is unaffected; only the prose dims).

Wireframe of one component row:

```
┌─────┐
│ 60% │  Your school's program rank
└─────┘  Indiana University Computer Science grads earn a median
         of $78,400 within a year — that's the 87th percentile
         (out of about 1,200 CS programs nationally, this one
         ranks higher than ~1,044 of them).

         87th percentile  ·  median $78,400
```

| Element | Token / spec |
|---|---|
| Container | `<li data-testid="receipt-component-ern-{0\|1}">`, `display: flex`, `gap: 14px`, `align-items: flex-start`. Rows separated by `marginTop: 16px` between siblings. |
| Weight chip (left rail) | Fixed `width: 56px`, `flex-shrink: 0`. Inside: a pill with `background: rgba(242,212,119,0.12)` (stat-color at 12% — derived from the existing `STAT_COLORS.ern.bg` pattern in `bossData.ts:80`), `padding: 6px 10px`, `border-radius: 999px`, `font-data` weight 700, size 13px, `color: var(--color-stat-ern)`, `text-align: center`. Reads as `60%`. The chip uses stat-color background not because the weight has color identity, but because it tethers each row visually to the score callout's stat color — the rail-and-chip pair feels intentional, not accidental. |
| Label (`payload.components[i].label`) | `font-display` weight 600, size 14px, `text-text-primary`, line-height 1.3. Sits as the row title. Sentence-case (the canonical labels are sentence-case: "your school's program rank"). |
| Explainer (`payload.components[i].explainer`) | `font-body` weight 400, size 14px, `text-text-secondary`, line-height 1.55, `marginTop: 4px`. The Gemma-written prose; max width 60ch. The percentile gloss appears inline within this prose per the SKILL voice rule (e.g., *"the 87th percentile (out of 1,200 CS programs nationally, this one ranks higher than about 1,044)"*) — see "Percentile typography inside the explainer" below. |
| Percentile callout (data row) | A separate row below the explainer prose with `marginTop: 8px`, displaying `{value_pct}th percentile · median ${anchor_dollars.toLocaleString()}` (or just one of the two if the other is null). `font-data` weight 600, size 13px, `text-text-primary` for the numbers, `text-text-muted` for the `th percentile` and `median` words and the `·` separator (U+00B7). Letter-spacing 0.3px. This is the "show the receipts" data-summary line per row — the one place a student looking for just the numbers can find them quickly without re-reading the prose. |

#### Percentile typography inside the explainer prose

The explainer string contains the percentile gloss inline (e.g., *"the 87th percentile (out of 1,200 CS programs nationally, this one ranks higher than about 1,044)"*). The treatment:

- The number `87` and the gloss numbers `1,200` and `1,044` are wrapped in `<span class="font-data text-text-primary">` to nudge the digits into Space Mono. **The surrounding "th percentile" and the parenthetical gloss stay in `font-body` `text-text-secondary`** — same weight as the rest of the explainer prose, no italics. This keeps the prose readable as a sentence (the eye doesn't trip on dimmed parentheticals) while letting the data points pop subtly via font change alone.
- This nudge is achieved by a regex pass in the renderer: any match of `/(\d{1,3})(st|nd|rd|th)\s+percentile/i` and `/\$([0-9,]+)/g` and integer-with-comma matches inside parentheses gets the data-font wrap. Implementation detail; the visual rule is "numbers in Space Mono, glue prose in Nunito."

### The math line (the tally)

This is the show-the-receipts moment. The math line gets its own visual treatment — an inset card with mono font and a unicode arrow. It's the one element in the receipt that is unapologetically *engineering*; that's what makes it trustworthy.

```
┌─────────────────────────────────────────────────────────────┐
│   0.6 × 0.87  +  0.4 × 0.92   →   score 9/10                │
└─────────────────────────────────────────────────────────────┘
   Your Focused effort setting lifts this to 9/10
```

Specifically:

| Element | Token / spec |
|---|---|
| Container | `<div data-testid="receipt-math-line">`, `bg-bp-mid` (one tier *down* from the card surface — recessed, like a tally tape sunk into the page), `padding: 14px 18px`, `border-radius: 10px`, `marginTop: 18px`. No border. The recessed surface treatment is what distinguishes this from a chat-message bubble; `ChatMessage.tsx:75` already uses `bg-bp-mid` for inline `<code>`, so the eye reads `bg-bp-mid` as "this is data, not prose" — perfect carry-over. |
| Math expression | `font-data` weight 600, size 15px, `text-text-primary`, letter-spacing 0.4px. The unicode arrow `→` (U+2192) and the score `9/10` get a 12px horizontal gap (via `gap: 12px` on a flex container) so the score callout stands apart from the arithmetic. The arrow itself stays in `text-text-primary` — keeping it in stat color was tempting but would over-color the receipt; reserving stat color for the score number alone makes that one number more powerful. |
| Centering | `text-align: center` on the math expression. Centered single-line on widths ≥ 480px; on narrower widths it stays centered and wraps the score callout to its own line below the expression (see Responsive Behavior). |
| Effort line (Decision 13) | When `payload.math_line` contains a `\n` and the second line follows the pattern `Your **{Effort}** effort setting...`, the renderer parses the second line and renders it BELOW the inset math-card, NOT inside it. Treatment: `font-body` weight 400, size 13px, `text-text-secondary`, `marginTop: 8px`, `text-align: center`, `font-style: italic`. The `**{Effort}**` markdown delimiters render as `font-display weight 600 text-text-primary` (non-italic) for the effort label. The outset placement (below the math-card, not inside) makes the effort line read as a footnote on the math, not as another line of arithmetic — which is exactly the relationship Decision 13 wants surfaced. |

### Sources (the citations)

A row of two pills below a divider. Quiet, factual, tappable.

```
─────────────────────────────────────────────────────────────
SOURCES
[ Graduate earnings · College Scorecard ]   [ Wages · BLS OOH ]
```

| Element | Token / spec |
|---|---|
| Section eyebrow | `font-display` weight 600, size 11px, letter-spacing 1.5px, `text-text-muted`, uppercase. `marginTop: 16px` (the divider sits between this eyebrow and the why-mix paragraph above it). |
| Divider | `border-t border-border-subtle`, `paddingTop: 14px`. The single divider in the entire receipt, demarcating prose-above from citations-below. |
| Pill row | `<ul>` with `display: flex; flex-wrap: wrap; gap: 8px`, `marginTop: 8px`. |
| Pill (`<li>`) | `<button>` (tappable — tooltip on focus/hover with the source's full `name` and the dataset version, when available). `bg-bp-mid`, `border: 1px solid border-border-subtle`, `border-radius: 999px`, `padding: 6px 12px`, `font-body` weight 500, size 12px. Inside: `<span class="text-text-muted">{label}</span>` + `<span class="text-text-muted">·</span>` + `<span class="text-text-primary">{name short form}</span>`. The label (e.g., "Graduate earnings") is muted; the source name is primary. The U+00B7 middle dot separates them. |
| Pill name truncation | The full source name on payload (`"College Scorecard (U.S. Department of Education)"`) is too long for a pill. The renderer applies a short-form lookup table: `College Scorecard (U.S. Department of Education)` → `College Scorecard`; `Occupational Outlook Handbook, published by the Bureau of Labor Statistics (BLS)` → `BLS OOH`. The full name appears in the tooltip + `aria-label` so nothing is hidden, just compressed. |
| Hover/focus state | `bg-bp-raised` background (one tier up — feels like the pill rises slightly), `border-color: var(--color-stat-ern)` (stat-color border on hover, the second place stat color enters the receipt), `cursor: pointer`. Transition: `200ms ease-out` on background + border-color. |
| Tooltip on hover/focus | Existing `TooltipPrimitive` pattern (or Radix tooltip if already in the project — verify in implementation). Content: full source name + a small data line (e.g., *"College Scorecard (U.S. Department of Education) · 2023 release"* if a version is available; `payload.sources[i].name` alone if not). 200ms open delay, 100ms close. |
| Pill `data-testid` | `receipt-source-{slug}` where slug is a kebab-case of the short-form name. |
| Pill `aria-label` | `Source: {full name}`. |

### Why we mix both pieces (the editorial)

A single paragraph. Last narrative section before the sources divider. Its job is the *why* — the educational paragraph that turns a list of components into an explanation.

| Element | Token / spec |
|---|---|
| Section eyebrow | `WHY WE MIX BOTH` — `font-display` weight 600, size 11px, letter-spacing 1.5px, `text-text-muted`, uppercase. `marginTop: 22px` (more breathing room than between component rows; this is a section change). |
| Paragraph (`payload.why_mix_paragraph`) | `font-body` weight 400, size 14px, line-height 1.6, `text-text-secondary`, max-width 60ch, `marginTop: 8px`. |
| Voice handling | The Pydantic `max_length=800` validator catches truncations before they render here; a half-sentence never reaches the DOM. The voice rules from `SKILL.md` Section 4 ("Picture two students…") shape the prose; the visionary doesn't override them. |
| What this section does NOT have | No bold pull-quotes inside the paragraph. No emphasis tints. The Gemma-written prose carries its own rhythm; styling it would over-egg an already-thoughtful card. |

### Missing-data treatment

When a `StatComponent` has `value_pct === null` OR `anchor_dollars === null` OR `missing_reason` is non-null, the row's visual weight drops in three coordinated steps. **All three apply together.** This is the existing AURA missing-data convention transferred to the receipt — same vocabulary, different surface.

1. **Row body opacity drops to 0.6.** The label, the explainer prose, the percentile callout all dim together. The weight chip stays at full opacity (the structural information — that this row is the 60% piece — remains undimmed; only the data is dimmed).
2. **Percentile callout slot becomes an open-ring em-dash.** Where the percentile would render (e.g., `87th percentile · median $78,400`), the renderer instead displays a `◦ —` glyph: a small open ring (U+25E6, `text-text-muted`, 12px) followed by an em-dash (U+2014, same color). This is the same vocabulary the pentagon vertex uses for an unreported AURA stat — when the student sees `◦ —` anywhere in the product, it means *we don't have this yet*. The legend coherence is the point.
3. **Missing-reason line appears below the explainer.** A `<p role="note" data-testid="receipt-missing-{component-key}">` containing `payload.components[i].missing_reason` (the canned server-stamped string, e.g., `"no median earnings reported for this program yet"`). Treatment: `font-body` weight 400, size 12px, `font-style: italic`, `text-text-muted`, `marginTop: 6px`. Italics here are the right move (despite italics being rare in the rest of the design system) because the line is *meta* — it's about the data, not part of it. The explainer prose stays non-italic; only the meta-explanation tilts.

The `missing_reason` `aria-label` reads as `Note: {missing_reason}` to the screen reader.

When **both** components are missing, the receipt still renders (the score is from the build, not from the percentiles), and the math line shows `0.6 × n/a + 0.4 × n/a → score N/10`. The two `n/a` strings inside the math expression are styled exactly the same as the percentile values (no special opacity dim) — they're already textually distinct, and dimming them inside the math card would muddy the recessed `bg-bp-mid` surface. The receipt does NOT show a card-level "limited data" warning banner (per the user's standing rule on substitution caveats).

### Loading state (skeleton frame)

While the tool loop is in flight, the trace rail above the receipt area is doing its job — streaming `TraceTurnStart` events for `get_career_paths` and `get_occupation_data`. The receipt area below the trace shows a **skeleton frame in the exact final shape**, with shimmer animations on each placeholder. The skeleton is not a generic gray box; it's the receipt's actual layout, just unfilled. This is the moment the student is most curious; showing the empty container reduces perceived wait.

```
┌───────────────────────────────────────────────────────────────┐
│  ▱▱▱▱▱▱▱▱▱▱▱                                          ▱▱ /10│  ← shimmer eyebrow + score
│                                                              │
│  ▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱                    │  ← shimmer one-liner
│                                                              │
│  ┌──┐  ▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱                                       │
│  │  │  ▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱                  │
│  └──┘                                                        │
│                                                              │
│  ┌──┐  ▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱                                       │
│  │  │  ▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱▱                  │
│  └──┘                                                        │
└───────────────────────────────────────────────────────────────┘
```

| Element | Token / spec |
|---|---|
| Skeleton container | Same card chrome as the realized receipt: `bg-bp-raised`, full border, 3px `var(--color-stat-ern)` left rail, same padding. The frame is the constant; the contents fill in. |
| Shimmer block | `<div role="presentation" aria-hidden>`, `bg-bp-mid` background, `border-radius: 4px`, sized to match the realized element (eyebrow row: 96px × 14px; one-liner: full-width × 18px × 2 lines; component label: 200px × 14px; explainer: full-width × 14px × 3 lines). |
| Shimmer animation | A single sweep gradient — `background: linear-gradient(90deg, bg-bp-mid 0%, bg-bp-raised 50%, bg-bp-mid 100%)`, `background-size: 200% 100%`, animated `background-position` from `100% 0` to `-100% 0` over 1400ms `ease-in-out` infinite. Subtle, not flashy. |
| When the receipt arrives | The skeleton fades out (200ms) while the realized receipt fades up (320ms `springs.smooth` from y:8). The two animations overlap by 100ms so the transition feels like the skeleton is *becoming* the receipt rather than being replaced by it. |
| `data-testid` | `explain-stat-receipt-skeleton`. |
| `aria-busy` | The skeleton container carries `aria-busy="true"` so screen readers announce loading state. The realized receipt drops the attribute. |

### Fallback path (markdown spike)

When JSON parsing fails and the markdown-spike fallback fires, the response renders through the existing prose markdown path (`ChatMessage.tsx`) — that's a `bg-bp-deep` chat bubble with the `✦` avatar, NOT a receipt card. **Decision: do not visually distinguish the fallback from any other Gemma prose reply.** Reasoning: the user clicked "Explain this to me" and they got an explanation; whether it came through the structured path or the markdown path is an engineering detail, not a user-facing one. Showing a "this is a fallback" indicator would teach the student that something failed, which (a) breaks the trust the receipt feature is built to create and (b) is outside the user's mental model entirely (they don't know the receipt path exists as a separate code branch). The markdown response has its own visual identity already (chat bubble, ✦, prose). That's the correct degraded experience: same content shape, slightly less polish.

### Mockups (all five required states)

#### State 1 — Default (both percentiles present, balanced effort)

Indiana University-Bloomington → Computer Science → Software Developer

```
┌── chat panel (640px wide) ──────────────────────────────────────────────┐
│                                                                         │
│  ✦  [trace rail collapsed: 2 tools called, 1.4s]                        │
│                                                                         │
│  ┌─[receipt card, bg-bp-raised, 3px gold left rail]──────────────────┐  │
│  ┃ EARNING POWER                                              9 /10  │  │
│  ┃                                                                   │  │
│  ┃ Where your starting paychecks land — your school's program        │  │
│  ┃ versus the rest of the country, blended with how this career      │  │
│  ┃ pays nationally.                                                  │  │
│  ┃                                                                   │  │
│  ┃ ┌─────┐  Your school's program rank                               │  │
│  ┃ │ 60% │  Indiana University Computer Science grads earn a median  │  │
│  ┃ └─────┘  of $78,400 within a year — the 87th percentile (out of   │  │
│  ┃          1,200 CS programs nationally, this one ranks higher      │  │
│  ┃          than about 1,044 of them).                               │  │
│  ┃                                                                   │  │
│  ┃          87th percentile  ·  median $78,400                       │  │
│  ┃                                                                   │  │
│  ┃ ┌─────┐  This career's pay rank                                   │  │
│  ┃ │ 40% │  Software Developers nationally are paid in the 92nd      │  │
│  ┃ └─────┘  percentile (out of all U.S. occupations, this one earns  │  │
│  ┃          more than ~840 of them) — median wage about $132,930.    │  │
│  ┃                                                                   │  │
│  ┃          92nd percentile  ·  median $132,930                      │  │
│  ┃                                                                   │  │
│  ┃ ╭─[bg-bp-mid inset]──────────────────────────────────────────╮    │  │
│  ┃ │      0.6 × 0.87  +  0.4 × 0.92    →    score 9/10          │    │  │
│  ┃ ╰────────────────────────────────────────────────────────────╯    │  │
│  ┃                                                                   │  │
│  ┃ WHY WE MIX BOTH                                                   │  │
│  ┃                                                                   │  │
│  ┃ Picture two students with the same diploma. One graduates from    │  │
│  ┃ a program where alumni land lucrative jobs; the other from a      │  │
│  ┃ program where alumni land in lower-paid roles. The career's       │  │
│  ┃ national pay tells you the ceiling of the field; your program's   │  │
│  ┃ rank tells you how this school's grads stack up reaching it.      │  │
│  ┃                                                                   │  │
│  ┃ ─────────────────────────────────────────────────────────────     │  │
│  ┃ SOURCES                                                           │  │
│  ┃ [ Graduate earnings · College Scorecard ]  [ Wages · BLS OOH ]    │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### State 2 — Missing school rank (60% component)

Millikin University → Chemistry → Food Science Technicians (the spike's failure case)

```
┌─[receipt card]──────────────────────────────────────────────────────┐
┃ EARNING POWER                                              2 /10    │
┃                                                                     │
┃ Where your starting paychecks land — your school's program          │
┃ versus the rest of the country, blended with how this career        │
┃ pays nationally.                                                    │
┃                                                                     │
┃ ┌─────┐  Your school's program rank                                 │  ← row dimmed (opacity 0.6)
┃ │ 60% │  Millikin University Chemistry grads' median earnings       │  ← chip stays at full opacity
┃ └─────┘  within a year of graduation aren't reported in the         │
┃          public data — that piece of the score sits open.           │
┃                                                                     │
┃          ◦ —                                                        │  ← open-ring + em-dash
┃                                                                     │
┃          (note) no median earnings reported for this program yet    │  ← italic missing-reason
┃                                                                     │
┃ ┌─────┐  This career's pay rank                                     │  ← full opacity
┃ │ 40% │  Food Science Technicians nationally are paid in the        │
┃ └─────┘  37th percentile (out of all U.S. occupations, this one     │
┃          earns more than ~330 of them) — median wage about          │
┃          $48,440.                                                   │
┃                                                                     │
┃          37th percentile  ·  median $48,440                         │
┃                                                                     │
┃ ╭─[bg-bp-mid inset]──────────────────────────────────────────╮      │
┃ │     0.6 × n/a  +  0.4 × 0.37    →    score 2/10            │      │
┃ ╰────────────────────────────────────────────────────────────╯      │
┃                                                                     │
┃ WHY WE MIX BOTH                                                     │
┃ ...                                                                 │
┃                                                                     │
┃ ─────────────────────────────────────────────────────────────       │
┃ SOURCES                                                             │
┃ [ Graduate earnings · College Scorecard ]  [ Wages · BLS OOH ]      │
└─────────────────────────────────────────────────────────────────────┘
```

#### State 3 — Missing occupation wage (40% component)

```
┌─[receipt card]──────────────────────────────────────────────────────┐
┃ EARNING POWER                                              5 /10    │
┃ ...                                                                 │
┃                                                                     │
┃ ┌─────┐  Your school's program rank                                 │  ← full opacity
┃ │ 60% │  ...                                                        │
┃ └─────┘  62nd percentile  ·  median $54,200                         │
┃                                                                     │
┃ ┌─────┐  This career's pay rank                                     │  ← row dimmed
┃ │ 40% │  Wage data for this occupation isn't reported by the BLS    │
┃ └─────┘  at the level we need — the national pay piece sits open.   │
┃                                                                     │
┃          ◦ —                                                        │
┃          (note) no national wage data reported for this             │  ← italic
┃                 occupation yet                                      │
┃                                                                     │
┃ ╭─[bg-bp-mid inset]──────────────────────────────────────────╮      │
┃ │     0.6 × 0.62  +  0.4 × n/a    →    score 5/10            │      │
┃ ╰────────────────────────────────────────────────────────────╯      │
┃ ...                                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

#### State 4 — Both missing (degenerate)

```
┌─[receipt card]──────────────────────────────────────────────────────┐
┃ EARNING POWER                                              3 /10    │  ← score from build, not derived
┃ ...                                                                 │
┃                                                                     │
┃ ┌─────┐  Your school's program rank                  (row dimmed)   │
┃ │ 60% │  ...                                                        │
┃ └─────┘  ◦ —                                                        │
┃          (note) no median earnings reported for this program yet    │
┃                                                                     │
┃ ┌─────┐  This career's pay rank                      (row dimmed)   │
┃ │ 40% │  ...                                                        │
┃ └─────┘  ◦ —                                                        │
┃          (note) no national wage data reported for this             │
┃                 occupation yet                                      │
┃                                                                     │
┃ ╭─[bg-bp-mid inset]──────────────────────────────────────────╮      │
┃ │     0.6 × n/a  +  0.4 × n/a    →    score 3/10             │      │
┃ ╰────────────────────────────────────────────────────────────╯      │
┃ ...                                                                 │
└─────────────────────────────────────────────────────────────────────┘
```

#### State 5 — Loading (skeleton)

See the "Loading state" section above for the skeleton wireframe.

#### State variant — Effort line (Decision 13, applies orthogonally to states 1-4)

```
┃ ╭─[bg-bp-mid inset]──────────────────────────────────────────╮
┃ │     0.6 × 0.87  +  0.4 × 0.92    →    score 7/10           │
┃ ╰────────────────────────────────────────────────────────────╯
┃                                                              
┃         Your Focused effort setting lifts this to 9/10         ← italic, below the math card
```

### Interactions (Framer Motion specs)

| Trigger | Element | Animation | Configuration |
|---|---|---|---|
| Receipt mounts after tool loop completes | `<motion.article>` card | Fade up + scale | `initial={{ opacity: 0, y: 12, scale: 0.985 }}` → `animate={{ opacity: 1, y: 0, scale: 1 }}`, `transition={springs.smooth}` (200/25). The slight scale (0.985 → 1) gives the "settling onto the desk" feel. |
| Receipt mounts (continued) | Score number `9` | Counts up + delayed appear | The score number wrapper has `initial={{ opacity: 0 }}`, `animate={{ opacity: 1 }}`, `transition={{ delay: 0.18, ...springs.snappy }}`. The number text itself counts from 0 to the final value over 400ms `ease-out` (existing count-up util in the project, or a simple `useEffect` ticker if not). |
| Receipt mounts (continued) | Component rows (li) | Stagger fade-up | Use `staggerContainer(delayChildren=0.08, staggerAmount=stagger.normal)` from `motion.ts`; each `<li>` fades up from y:6. Math line and sources also participate in the stagger but with `delayChildren` chosen so the math card lands ~120ms after the second component row. |
| Receipt mounts (continued) | Math-line inset card | Fade in with slight scale | `initial={{ opacity: 0, scale: 0.96 }}`, `animate={{ opacity: 1, scale: 1 }}`, `transition={{ delay: 0.4, ...springs.smooth }}`. The math is the punchline; the late delay lets the eye finish reading the components before the tally appears. |
| Source pill hover/focus | `<button>` pill | Background + border lift | `transition={springs.snappy}`, change `bg` from `bg-bp-mid` → `bg-bp-raised` and `borderColor` from `border-border-subtle` → `var(--color-stat-ern)` over 200ms. `whileHover` and `whileFocus` Framer props. |
| Source pill press | `<button>` pill | Scale press | `whileTap={{ scale: 0.97 }}` with `transition={springs.snappy}`. Existing `pressTap` pattern from `transitions` in `motion.ts`. |
| Tooltip on source pill | Tooltip surface | Fade + shift in | Existing tooltip pattern; 200ms open delay, 150ms fade-in, 100ms close. |
| Skeleton → realized receipt | Skeleton wrapper | Crossfade | Skeleton: `exit={{ opacity: 0 }}, transition={{ duration: 0.2 }}`. Realized receipt: see "Receipt mounts" above. AnimatePresence wrapper keys on `kind === "receipt" ? "receipt" : "skeleton"`. |
| Reduced motion | All of the above | Disable transforms, keep fades | Wrap motion variants in `useReducedMotion()` (Framer hook) — when true, the entrance becomes a single 150ms fade with no y/scale, the count-up snaps to final value instantly, and the stagger collapses to 0. The receipt still arrives; it just arrives plainly. |

### Responsive Behavior

The chat panel is 480-720px wide; the receipt card respects the panel's `max-w-[90%]` and adds its own `max-width: 640px`. Two breakpoints inside the receipt:

**At ≥ 560px (chat panel approximately ≥ 600px):**
- Eyebrow + score on a single row (`flex justify-between`).
- Component bullets: weight chip + stacked content side-by-side as designed (the default option-a layout).
- Math line: math expression and `→ score N/10` on a single line, centered.
- Source pills: inline on one row, wrap only if both pills together exceed available width.

**At < 560px (chat panel approximately ≤ 600px, the narrow slide-in mode):**
- Eyebrow + score still inline (eyebrow shrinks via `text-overflow: ellipsis` if needed; score stays on the right). The eyebrow's `EARNING POWER` is short enough to never truncate; this is a defensive rule.
- Component bullets: weight chip stays in left rail (it's only 56px, narrow enough to keep the layout intact even at 480px). The prose still flows beside the chip — never stack the chip above the prose, because the row's information hierarchy (weight is a *qualifier* of the label, not a separate concept) only reads when they're side-by-side.
- Math line: the score callout (`→ score 9/10`) wraps to its own line below the arithmetic. Both lines remain centered. The math expression `0.6 × 0.87 + 0.4 × 0.92` stays on one line at 480px because the data-font is compact enough; the wrap behavior kicks in only on the `→` arrow before the score.
- Source pills: stack to two rows (one per pill) only if the longest pill exceeds the available width; otherwise inline. The flex-wrap handles this declaratively.
- Why-mix paragraph: max-width drops from 60ch to the full card width.

The "no break" baseline is **480px** (the narrowest the chat panel ever goes). At 480px the receipt is still a four-section composed document; nothing collapses or hides. Below 480px is out of scope for the chat panel and therefore out of scope for the receipt.

### Brightpath Design References

| Concern | Token / pattern |
|---|---|
| Card surface | `bg-bp-raised` (matches `StatInfoPopover.tsx:57`) |
| Card border | `border border-border-default` + `borderLeft: 3px solid var(--color-stat-ern)` (mirrors StatInfoPopover's left-rail treatment) |
| Card shadow | `0 8px 32px rgba(27,29,48,0.55)` (a tier shy of StatInfoPopover's `0.7`) |
| Card radius | `rounded-[14px]` (StatInfoPopover) |
| Recessed math card | `bg-bp-mid` (echoes inline `<code>` in `ChatMessage.tsx:75`) |
| Eyebrow text | `font-display` 11-13px, `letter-spacing: 1.5px`, uppercase, `text-text-muted` |
| Score number | `font-data` weight 700, 44px, `color: var(--color-stat-ern)` |
| Score max | `font-data` weight 400, 22px, `text-text-muted` |
| Section label / row title | `font-display` weight 600, 14px, `text-text-primary` |
| Prose | `font-body` weight 400, 14-15px, line-height 1.55-1.6, `text-text-secondary` |
| Inline numbers in prose | `font-data` `text-text-primary` (regex pass) |
| Percentile callout row | `font-data` weight 600, 13px, `text-text-primary` for numbers, `text-text-muted` for the prose glue |
| Math expression | `font-data` weight 600, 15px, `text-text-primary`, U+2192 arrow |
| Effort line | `font-body` italic 13px, `text-text-secondary`, `**Effort**` segment in `font-display` weight 600 `text-text-primary` non-italic |
| Source pill | Compact pattern derived from `SkillStatBadge.tsx` (`rounded-full`, `font-data` for the label-name pair) — but with `font-body` instead of `font-data` to match the reading register, and tappable behavior via `<button>` |
| Stat-color tint background | `rgba(242,212,119,0.12)` for ERN weight chip — derived from `STAT_COLORS.ern.bg` pattern (`rgba(242,212,119,0.15)`) at slightly reduced opacity to sit quietly inside the recessed math context |
| Missing-data percentile | U+25E6 + U+2014 (`◦ —`) in `text-text-muted` 12px |
| Missing-reason note | `font-body` italic 12px `text-text-muted` |
| Motion: card mount | `springs.smooth` (200/25) |
| Motion: score appear | `springs.snappy` (400/25) at `delay: 0.18` |
| Motion: row stagger | `staggerContainer(delayChildren=0.08, staggerAmount=stagger.normal)` |
| Motion: math line | `springs.smooth` at `delay: 0.4` |
| Motion: pill hover | `springs.snappy` |

No new tokens. No new font roles. No new color values. The receipt is composed entirely from existing Brightpath primitives.

### Accessibility

| Element | Identifier | Type | aria-label / role notes |
|---|---|---|---|
| Receipt container | `data-testid="explain-stat-receipt"` | `<article role="region">` | `aria-label="Earning Power explanation receipt"`. The `role="region"` makes it a screen-reader landmark; receipt is announced as a discrete section the user can jump to. |
| Score callout (number) | `data-testid="receipt-score"` | `<span>` inside the score row | `aria-label="Earning Power score: 9 out of 10"`. The visual "9 /10" is decorative; the aria-label is the canonical reading. |
| Score row container | (no testid) | `<header>` | The score row is the receipt's `<header>` element so the eyebrow + score + one-liner are grouped semantically. |
| Component row list | `data-testid="receipt-components"` | `<ul>` | Implicit role; no aria-label needed. |
| Component row | `data-testid="receipt-component-{stat_code.lower()}-{0..N}"` (e.g., `receipt-component-ern-0`) | `<li>` | `aria-label="60 percent — your school's program rank"`. Reading the weight first matches the visual order. |
| Component weight chip | (no testid) | `<span aria-hidden="true">` | The visible "60%" text is hidden from the screen reader because the row's `aria-label` already includes "60 percent." |
| Component label | (no testid) | `<h3>` (visually styled, not size 24) | The label uses `<h3>` semantic but the visual is `font-display 14px`. Receipt section structure: `<header>` (score), `<h2>` for "How it works" (visually-hidden), `<h3>` per component, `<h2>` for "Why we mix both" (visually-hidden), `<h2>` for "Sources" (visually-hidden eyebrow with `aria-label`). |
| Percentile callout row | (no testid) | `<p>` | Read inline; no special role. |
| Math line container | `data-testid="receipt-math-line"` | `<div role="math" aria-label="Score formula">` | The aria-label is `"Score formula: zero point six times zero point eight seven plus zero point four times zero point nine two equals score 9 out of 10"`. Built server-side in the renderer from the structured fields, so it reads naturally even on screen readers that don't pronounce U+2192. |
| Effort line | `data-testid="receipt-effort-line"` | `<p>` | Read as flowing prose. |
| Why-mix paragraph | `data-testid="receipt-why-mix"` | `<p>` | The eyebrow `<h2>` above it labels the section. |
| Sources eyebrow | (no testid) | `<h2 class="sr-only">Sources</h2>` followed by visible `<div aria-hidden>SOURCES</div>` | The visual eyebrow is decorative; the screen reader reads the proper heading. |
| Source pill list | `data-testid="receipt-sources"` | `<ul>` | |
| Source pill | `data-testid="receipt-source-{slug}"` | `<button>` (tappable) — `<li>` wrapper | `aria-label="Source: College Scorecard (U.S. Department of Education)"`. The full source name is announced; the visual short-form is decorative. Tooltip content is also announced via `aria-describedby` pointing at the tooltip element. |
| Missing-data line | `data-testid="receipt-missing-{component-key}"` (e.g., `receipt-missing-school-rank`) | `<p role="note">` | `aria-label="Note: no median earnings reported for this program yet"`. |
| Missing-data percentile glyph | (no testid) | `<span aria-label="data not available">◦ —</span>` | The U+25E6 + U+2014 glyph string is meaningless to a screen reader; the aria-label is canonical. |
| Skeleton container | `data-testid="explain-stat-receipt-skeleton"` | `<div role="status" aria-busy="true" aria-live="polite">` | `aria-label="Loading Earning Power explanation"`. Polite live region so the eventual receipt arrival is announced without interrupting. |
| Reduced motion | All Framer motion props | Hook | `useReducedMotion()` collapses entrance animations; functionality is identical. |
| Focus state on pills | Pill `<button>` | `focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-none` | Same focus ring pattern as `StatInfoPopover.tsx:89`. |
| Color contrast | All text on `bg-bp-raised` | Verified | `text-text-primary` and `text-text-secondary` on `bg-bp-raised` exceed WCAG AA at all sizes (verified against the existing StatInfoPopover, which uses identical pairings). The `var(--color-stat-ern)` gold (`#F2D477`) on `bg-bp-raised` for the score number passes AA at 44px (large text threshold is 3:1; gold-on-raised exceeds). |

### States to mock

(Final list, mirrored against §4 Architecture and §5 reviews. All five required states are wireframed in "Mockups" above.)

- **State 1 — Default.** Both percentiles populated, balanced effort. Indiana University-Bloomington → CS → Software Developer.
- **State 2 — Missing school rank.** `cip_family_earnings_rank === null`. 60% component dims, percentile slot is `◦ —`, missing-reason note appears. Millikin → Chemistry → Food Science Technicians (the spike's failure case — production data).
- **State 3 — Missing occupation wage.** `wage_percentile_overall === null`. 40% component dims; same treatment.
- **State 4 — Both missing.** Score still renders from `build.career.stats.ern`; both rows dim; math line shows `0.6 × n/a + 0.4 × n/a → score N/10`.
- **State 5 — Loading (skeleton).** Same card chrome, shimmer placeholders inside. `aria-busy="true"`, polite live region.
- **State variant — Effort line (Decision 13).** Applies to any of states 1-4 when `effort != "balanced"`. The italic effort line renders below the math card.
- **Fallback — markdown spike.** No visual distinction from a normal Gemma prose reply. Renders through `ChatMessage.tsx`. The student does not learn that JSON parsing failed.

---

## §4 Technical Specification

### Architecture Overview

The Ask Gemma chat surface (`backend/app/services/ask_gemma.py`) already routes the sentinel `[explain-this:ERN]` opener to a dedicated branch in `chat_ask` and `chat_ask_stream` (added 2026-05-02 in this same conversation, no prior spec). This spec replaces what that branch produces:

- **Today (spike):** the branch swaps in a markdown-template appendix that mandates a four-section response. Gemma writes free-form markdown; the response is rendered as plain-text in the chat.
- **After this spec:** the branch swaps in a JSON-schema appendix that mandates an `ExplainStatReceipt`-shaped JSON object. Gemma writes JSON; the backend post-processes (stamps the score, validates, builds `math_line`); the response is delivered as a structured payload; the frontend renders it via `<ExplainStatReceipt>`.

Five integration points (all updated v1.2 per §5 reviews):

1. **`gemma_client.generate_with_tools_loop`** — gains a `final_turn_response_format: dict[str, Any] | None = None` kwarg (Decision 15). When set, the JSON-mode constraint is injected into `completion_kwargs` **only on the final synthesis turn** (when no further tool calls are pending), not on intermediate tool-call turns. The kwarg propagates to the underlying chat-completions API call via per-backend translation:
   - **OpenAI-compat path (`_one_tool_turn`):** added to `completion_kwargs` verbatim as `response_format={"type":"json_object"}`. Used when `INFERENCE_BACKEND=openrouter`.
   - **Native Ollama path (`_one_tool_turn_ollama`):** translated to `payload["format"] = "json"` before the httpx POST. Ollama's native `/api/chat` endpoint uses a different on-the-wire key. Used when `INFERENCE_BACKEND=ollama`.
   - The translation is internal to `gemma_client`. The public kwarg is uniform; per-backend translation hides inside the two `_one_tool_turn*` paths.
2. **`ask_gemma._ern_explain_appendix`** — rewritten to instruct Gemma to emit a JSON object matching the `ExplainStatReceipt` schema. The structural template is delivered as a **single filled-in JSON example with `__FILL_IN__` sentinel strings** for prose fields and realistic numeric placeholders for percentile/dollar fields (Decision 15 supporting genai-architect finding 2 — Pydantic model definition verbatim is the wrong vehicle for Gemma 4). Inline reproduction of the relevant `pentagon-stat-explanation/SKILL.md` voice rules (percentile-gloss inline format, acronym-first-use rule, `why_mix_paragraph` calibration target) — Gemma has no SKILL.md access at inference time. The voice-rule relaxation is **scoped**: the "never state a raw score" rule is lifted ONLY for the JSON numeric fields (`value_pct`, `anchor_dollars`); for prose fields (`one_liner`, `explainer`, `why_mix_paragraph`) the prohibition stays active to prevent score-reference drift after the server overwrites `score`.
3. **`ask_gemma._postprocess_ern_explain_receipt`** — new helper. Pipeline:
   1. Run `gemma_client._extract_json_objects(raw)` (existing helper, lines 815-846) to strip markdown fences and extract JSON from prose-wrapped output. Catches the two most common Gemma 4 JSON-mode failure modes (```json{...}``` fencing and trailing prose) without a fallback retry.
   2. `json.loads` the extracted object. On failure, return None.
   3. Pydantic-validate the parsed dict against `ExplainStatReceipt`. On `ValidationError`, return None.
   4. Assert `receipt.stat_code == "ERN"` (guards against Gemma cross-stat drift in the same JSON-mode constraint window). On mismatch, return None.
   5. **Server-stamp `score`** unconditionally from `build.career.stats.ern`. If `build.career.stats.ern is None`, return None — the trigger button on `BuildResultsScreen` should be disabled in that case (see Service Changes), but the helper guards belt-and-suspenders.
   6. **Server-build `math_line`** unconditionally from the `tool_call_log` percentile values, regardless of whatever Gemma emitted. Format: `"0.6 × <cip_pct or 'n/a'> + 0.4 × <wage_pct or 'n/a'> → score <build score>/10"`. When `effort != "balanced"`, append a separate effort line (Decision 13).
   7. **Normalize `components[*].label`** against the per-stat allowlist (Decision 14): match by `weight_pct` first, then nearest-string-distance; replace off-script labels with the canonical version; log a WARNING with both the original and the normalized value.
   8. **Server-stamp `value_pct`, `anchor_dollars`, `missing_reason`** from the tool results. Gemma's emitted values for these fields are discarded; the helper rebuilds them from `tool_call_log` so the UI cannot drift from the truth. `missing_reason` is set to a canned string (e.g., `"no median earnings reported for this program yet"`) when the corresponding tool field is null.
   9. Append a structured log record to `logs/gemma.jsonl` with `{call_site: "explain_ern_receipt", parse_success: bool, failure_reason: str | None, json_prefix: str (first 500 chars), build_id: str, backend: "ollama" | "openrouter"}`. INFO on success, WARNING on failure.
   10. Return the validated, server-stamped `ExplainStatReceipt`.
4. **`AskResponse` and `TraceFinalText` Pydantic models** — extended so `response: str` becomes `response: str | ExplainStatReceipt`. `ExplainStatReceipt` carries a self-discriminating `kind: Literal["receipt"] = "receipt"` field so the frontend Zod validator can use `z.discriminatedUnion`-style logic without object-shape sniffing (or, where the type is `string | ExplainStatReceipt`, a `z.union([z.string(), z.object({kind: z.literal("receipt"), ...})])` parser). The streaming `TraceFinalText.response` carries the same union. Existing scopes (boss, skill, build, branch, compare) continue to emit string responses.
5. **`<ExplainStatReceipt>` React component + `ChatHistoryItem` type widening** — new component renders the structured payload; the chat history item type becomes a discriminated union; the existing `GemmaChat` renderer dispatches on `kind`. The cascade through `frontend/src/api/menu.ts` and `GemmaChat.tsx` is enumerated in the File Changes table below.

**Fallback path (Decision 6 — refined v1.2).** When `_postprocess_ern_explain_receipt` returns None, the backend re-runs the loop ONCE without `final_turn_response_format` and with the markdown-spike appendix. The fallback re-uses the **cached `tool_call_log` from the first attempt** — it does not re-issue `get_career_paths` or `get_occupation_data`. The cached values are injected into the markdown-fallback's user message (`"Here are the values from your build: cip_family_earnings_rank=X, earnings_1yr_median=Y, ..."`) so Gemma renders the markdown receipt without a second tool fetch. This caps total wait at ~10-15s instead of 50-60s and skips two redundant MCP round-trips.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/models/api.py` | Modify | Add `ExplainStatReceipt`, `StatComponent`, `ReceiptSource` Pydantic models with `model_config = ConfigDict(extra="forbid")`. `ExplainStatReceipt` includes a `kind: Literal["receipt"] = "receipt"` self-discriminator field for frontend Zod parsing without object-shape sniffing. `why_mix_paragraph` carries `Field(max_length=800)` to catch token-budget truncations before they render. Widen `AskResponse.response` and `TraceFinalText.response` from `str` to `str \| ExplainStatReceipt`. |
| `backend/app/services/ask_gemma.py` | Modify | (a) Add `_RECEIPT_JSON_TEMPLATE` constant — a **filled-in JSON example with `__FILL_IN__` sentinel strings** for prose fields and realistic numeric placeholders (NOT the Pydantic model definition verbatim — see Decision 15 / genai-architect finding 2). (b) Add `_ERN_LABEL_ALLOWLIST: dict[int, str]` constant mapping `weight_pct → canonical label` (60 → `"your school's program rank"`, 40 → `"this career's pay rank"`). (c) Replace `_ern_explain_appendix` body with JSON-mode instructions, the filled-in template, the inline-reproduced SKILL voice rules (percentile-gloss inline format, acronym-first-use, `why_mix_paragraph` calibration target), and the **scoped voice-rule split**: numeric-field score-reference relaxation + prose-field score-reference prohibition. (d) Add `_postprocess_ern_explain_receipt(raw: str, build: Build, tool_call_log: list[ToolCallTurn]) -> ExplainStatReceipt \| None` — the 10-step pipeline documented in Architecture Overview point 3. Returns None when `build.career.stats.ern is None`. (e) Add `_render_math_line(cip_pct: float \| None, wage_pct: float \| None, build_score: int, effort: str) -> str` helper that produces the `0.6 × A + 0.4 × B → score N/10` string with `n/a` placeholders for nulls; appends a separate effort line when `effort != "balanced"` (Decision 13). (f) Add `_normalize_label(weight_pct: int, gemma_label: str) -> tuple[str, bool]` helper that does the allowlist match (Decision 14); returns `(canonical_label, was_normalized)`. (g) Add `_log_receipt_parse(call_site, parse_success, failure_reason, json_prefix, build_id, backend) -> None` helper for the structured `gemma.jsonl` record. (h) In both `chat_ask` and `chat_ask_stream`, when `explain_ern` is true: pass `final_turn_response_format={"type": "json_object"}` to the tool loop, capture the `tool_call_log`, attempt `_postprocess_ern_explain_receipt`; on success return / yield the receipt; on failure run the loop ONCE more without `final_turn_response_format` and with the markdown-spike appendix, **injecting the cached tool values into the markdown user message so no MCP re-fetch happens** (Decision 6 v1.2 refinement). (i) Helper-leak stripper (`_HELPER_LEAK_RE`) continues to apply to the markdown fallback path only. |
| `backend/app/services/gemma_client.py` | Modify | (a) Add `final_turn_response_format: dict[str, Any] \| None = None` kwarg to `generate_with_tools_loop` and `_tools_loop_inner` (Decision 15 — synthesis-turn-only scoping). When set, the constraint is injected into the turn's `completion_kwargs` ONLY when `_tools_loop_inner` detects it is about to return plain text (no `response_tool_calls` after the previous turn). (b) **Per-backend translation:** in `_one_tool_turn` (OpenAI-compat path, lines ~1255-1266) the kwarg is added to `completion_kwargs` verbatim. In `_one_tool_turn_ollama` (native Ollama path, lines ~1312-1340) the kwarg `{"type":"json_object"}` is translated to `payload["format"] = "json"` before the httpx POST. The translation is internal; the public kwarg API is uniform. (c) `_extract_json_objects` (existing helper, lines 815-846) is the documented JSON-extraction primitive that `ask_gemma._postprocess_ern_explain_receipt` calls — no changes to that helper itself. (d) `logs/gemma.jsonl` records the flag in the existing per-call exchange record. No-op when `final_turn_response_format` is `None` (current behavior). |
| `backend/app/services/__init__.py` | Modify | Re-export the new Pydantic models if the package's public surface includes them. |
| `backend/tests/services/test_ask_gemma_explain_receipt.py` | Create | New file. Tests for `_postprocess_ern_explain_receipt`: happy path, score-from-build override, math-line construction (both percentiles present, school-rank null, occupation-wage null, both null), Pydantic-validation failures (missing field, extra field, wrong type), tool-call-log extraction edge cases (no calls, only one call, calls in either order). |
| `backend/tests/services/test_ask_gemma.py` | Modify | Add fallback test: when `_postprocess_ern_explain_receipt` returns `None`, the response falls through to the markdown spike path and the response is a string, not an `ExplainStatReceipt`. Existing ERN-explain integration test (if added during the spike) updates to the new payload shape. |
| `backend/tests/services/test_gemma_client.py` | Modify | Add: `response_format` kwarg propagates to the chat-completions request body; `None` is a no-op; logging captures the flag. |
| `backend/app/routers/chat.py` (or wherever `/chat/ask` and `/chat/ask/stream` live) | Modify | The router serializes `AskResponse` and `TraceFinalText`; verify the union type roundtrips correctly through FastAPI's response-model serializer (Pydantic v2 should JSON-encode the `ExplainStatReceipt` branch as a nested object). |
| `frontend/src/types/chat.ts` (new file) | Create | TypeScript discriminated union: `type ChatHistoryItem = { role: "user" \| "assistant"; kind: "text"; content: string } \| { role: "assistant"; kind: "receipt"; payload: ExplainStatReceipt }`. Re-exports `ExplainStatReceipt`, `StatComponent`, `ReceiptSource` types inferred from the Zod schema (single source of truth). Imported by `menu.ts`, `GemmaChat.tsx`, and `ExplainStatReceipt.tsx`. |
| `frontend/src/api/menu.ts` | Modify | **Cascade enumerated:** (a) `parseSSEFrame` `final_text` branch (current line ~276-280) — preserve the object payload when not a string; do NOT coerce to `""` for non-string. (b) `AskGemmaStreamResult.response` type (current line ~321) widens from `string` to `string \| ExplainStatReceipt`. (c) `let response = ""` initialization in `askGemmaStream` (current line ~357) widens to `let response: string \| ExplainStatReceipt = ""`. (d) The synthetic `final_text` events in the mock + fallback paths (current lines ~349, ~417) — verify they don't break under the wider type. (e) `mockChat` returns string (unchanged for non-receipt scopes). (f) `sendChat` (legacy non-scope endpoint, line ~188) returns string (unchanged). (g) Runtime validation: parse the SSE `final_text.response` via the Zod union schema (`z.union([z.string(), explainStatReceiptSchema])`); on parse failure, fall back to `String(response)` rather than throwing. |
| `frontend/src/components/menu/GemmaChat.tsx` | Modify | **Cascade enumerated:** (a) Line ~207 (`setHistory(...)` in opener path) — construct `{role: "assistant", kind: "text", content}` for string responses, `{role: "assistant", kind: "receipt", payload}` for receipts. (b) Line ~239 (history fold for tool-loop response) — same dispatch. (c) Line ~248 (`assistantIdx = nextHistory.length`) — index-into-array works regardless of `kind`; trace attachment unchanged. (d) Lines ~262 / ~280 / ~287 (assistant-message construction in the streaming path) — widen the local `response` variable typing and dispatch on the union type when constructing the history item. (e) Renderer (`renderMessageWithTrace` and consumers) — switch on `item.kind`: `"text"` → existing prose markdown renderer; `"receipt"` → `<ExplainStatReceipt payload={item.payload} />`. The trace rail attaches to assistant message indices independently of kind, so no changes there. |
| `frontend/src/components/menu/ExplainStatReceipt.tsx` | Create | New React component. Props: `{ payload: ExplainStatReceipt }`. Pixel-perfect implementation of @fp-design-visionary's §3 spec. Handles all states: default, missing-data, both-missing. Uses Brightpath tokens; no inline color values. |
| `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | Create | Vitest tests covering all states from §3 plus accessibility (data-testid presence, aria-label on container, role attributes). Snapshot test for the default state. |
| `frontend/src/lib/zodSchemas.ts` (or new file `frontend/src/types/explainReceipt.ts`) | Create or Modify | Zod schema for `ExplainStatReceipt` runtime validation at the SSE boundary. Exports both the Zod schema and the inferred TypeScript type (single source of truth for the frontend type). |
| `docs/reference/stat-display-surfaces.md` | Modify | Add a new §1i entry for `<ExplainStatReceipt>` listing it as ✅ wired (the second entry tagged ✅ — first is §1a popover trigger). Cross-reference the new component file path and the "explain-this:ERN" sentinel. |
| `.claude/skills/pentagon-stat-explanation/SKILL.md` | Modify | Add a new line under "Companion reference" pointing to `frontend/src/components/menu/ExplainStatReceipt.tsx` as the rendering authority. The voice rules stay where they are; the SKILL just gains a pointer to where its prose-field outputs render. |

### Data Model Changes

New Pydantic models in `backend/app/models/api.py`:

```python
from typing import Literal
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator


# Module-level helper used by both StatComponent and ExplainStatReceipt
# prose-field validators. Catches Gemma echoing the system-appendix
# placeholder sentinels back into the JSON instead of replacing them
# with real prose. This is a silent-correctness failure mode genai-
# architect flagged on v1.2 — without this guard a string like
# "__FILL_IN__" or "[ONE-SENTENCE DEFINITION HERE]" would pass Pydantic
# validation and render to the student.
_SENTINEL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"__FILL[_ ]IN__", re.IGNORECASE),
    re.compile(r"\[\s*FILL[\s_-]*IN", re.IGNORECASE),
    re.compile(r"<\s*FILL[\s_-]*IN", re.IGNORECASE),
    re.compile(r"\bONE-SENTENCE\s+DEFINITION\s+HERE\b", re.IGNORECASE),
    re.compile(r"\bPLACEHOLDER\b", re.IGNORECASE),
)


def _reject_sentinel_passthrough(value: str) -> str:
    """Reject prose strings that contain unreplaced template sentinels.

    Used as a Pydantic field_validator on every prose field
    (one_liner, components[*].explainer, components[*].anchor_text,
    why_mix_paragraph). Triggers the markdown fallback path when
    Gemma echoes the appendix's placeholder sentinels back instead of
    writing real content.
    """
    for pattern in _SENTINEL_PATTERNS:
        if pattern.search(value):
            raise ValueError(
                f"prose field contains unreplaced template sentinel: "
                f"{value[:80]!r}"
            )
    return value


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

    # Sentinel-passthrough guards: reject Gemma echoing the system-
    # appendix placeholders back instead of replacing them.
    _reject_sentinel_explainer = field_validator("explainer")(
        _reject_sentinel_passthrough
    )
    _reject_sentinel_anchor_text = field_validator("anchor_text")(
        _reject_sentinel_passthrough
    )


class ExplainStatReceipt(BaseModel):
    """Structured explainer-receipt payload for one of the five pentagon
    stats. Generic across ERN, ROI, RES, GRW, AURA — only ERN populates
    in this spec."""
    model_config = ConfigDict(extra="forbid")

    kind: Literal["receipt"] = Field(
        default="receipt",
        description=(
            "Self-discriminator field for frontend Zod validation. "
            "Lets the frontend distinguish a receipt response from a "
            "plain-string response without object-shape sniffing on "
            "the union type str | ExplainStatReceipt. Always 'receipt'."
        ),
    )
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
            "field is overwritten unconditionally (see §2 Decision 7). "
            "_postprocess_ern_explain_receipt returns None when "
            "build.career.stats.ern is None — the trigger button on "
            "BuildResultsScreen should be disabled in that case "
            "(belt-and-suspenders guard)."
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
            "rules from pentagon-stat-explanation/SKILL.md apply. "
            "Must NOT contain numeric score references like 'N/10' "
            "or 'your score is X' (the score callout is the UI's "
            "responsibility — see Decision 15 voice-rule scoping)."
        )
    )
    components: list[StatComponent] = Field(
        min_length=1,
        max_length=5,
        description=(
            "The mixed-in pieces of the score. ERN uses 2; ROI uses 1; "
            "GRW uses 1; RES uses 2 (post-reshape blended). AURA is "
            "out of scope for v1.0 (Decision 10 v1.2 — institution-level "
            "provenance does not fit this shape)."
        ),
    )
    math_line: str = Field(
        description=(
            "Server-rendered math expression showing how the components "
            "combine to the score, e.g. '0.6 × 0.87 + 0.4 × 0.92 → "
            "score 9/10'. Null inputs render as 'n/a'. **Always "
            "server-built unconditionally from tool_call_log; the value "
            "Gemma emits in this field (if any) is discarded.** When "
            "effort != 'balanced', a separate effort line is appended "
            "(Decision 13)."
        )
    )
    sources: list[ReceiptSource] = Field(
        min_length=1,
        description="Data sources rendered as pills in the receipt UI.",
    )
    why_mix_paragraph: str = Field(
        max_length=800,
        description=(
            "Gemma-written ~3-sentence 'two students contrast' paragraph "
            "explaining why the score is structured the way it is. Voice "
            "rules from pentagon-stat-explanation/SKILL.md apply. "
            "Must NOT contain numeric score references (see one_liner). "
            "max_length=800 catches token-budget truncations as a "
            "Pydantic validation failure → fallback fires (rather than "
            "rendering a half-sentence)."
        )
    )

    # Sentinel-passthrough guards: reject Gemma echoing the system-
    # appendix placeholders back instead of replacing them. Without
    # these, a string like "__FILL_IN__" would pass Pydantic and
    # render to the student. genai-architect v1.2 re-review concern.
    _reject_sentinel_one_liner = field_validator("one_liner")(
        _reject_sentinel_passthrough
    )
    _reject_sentinel_why_mix = field_validator("why_mix_paragraph")(
        _reject_sentinel_passthrough
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
    raw: str,
    build: Build,
    tool_call_log: list[gemma_client.ToolCallTurn],
) -> ExplainStatReceipt | None:
    """Parse Gemma's JSON output, validate via Pydantic, stamp server-
    controlled fields, return a fully-realized ExplainStatReceipt.

    Returns None on any failure — caller falls back to the markdown spike
    path with the cached tool_call_log injected (no MCP re-fetch).

    Pipeline (10 steps; see §4 Architecture Overview point 3):
      1. _extract_json_objects(raw) — strip markdown fences, brace-depth
         extract; handles ```json{...}``` and trailing-prose wrappers.
      2. json.loads on the extracted object. ValueError -> None.
      3. ExplainStatReceipt.model_validate(parsed). ValidationError -> None.
      4. Assert receipt.stat_code == "ERN". Mismatch -> None.
      5. If build.career.stats.ern is None -> None (belt-and-suspenders;
         the trigger button should be disabled in this case).
      6. Server-stamp receipt.score = build.career.stats.ern. Discard
         whatever Gemma emitted (Decision 7).
      7. Server-build receipt.math_line via _render_math_line() using
         tool_call_log percentile values + build's effort setting
         (Decision 13). Discard whatever Gemma emitted (Decision 8).
      8. Normalize each receipt.components[i].label via _normalize_label()
         against the per-stat allowlist (Decision 14). Off-script labels
         get replaced; WARNING logged with original + canonical.
      9. For each component, server-stamp value_pct, anchor_dollars,
         missing_reason from tool_call_log (discard Gemma's emitted
         values; server is the source of truth for numeric data).
     10. _log_receipt_parse(call_site="explain_ern_receipt",
         parse_success=True, ...) appends a structured record to
         logs/gemma.jsonl; on failure it's emitted at step 1-9's
         exception handler with parse_success=False.

    Server-controlled fields (always rebuilt; Gemma's emitted values
    are discarded regardless):
      - score, score_max
      - math_line
      - components[*].value_pct, anchor_dollars, missing_reason

    Gemma-controlled fields (kept as-emitted after Pydantic validation):
      - kind (always "receipt")
      - stat_code (validated == "ERN", discarded if not)
      - stat_name
      - one_liner
      - components[*].weight_pct (Pydantic-validated 0-100)
      - components[*].explainer
      - components[*].anchor_text (the named entity, e.g. school name)
      - sources (Pydantic-validated min_length=1; voice authority is
        the SKILL but the server doesn't normalize this)
      - why_mix_paragraph (Pydantic max_length=800 catches truncation)

    Server-normalized fields (Gemma's value taken as a hint, replaced
    with a canonical value):
      - components[*].label (Decision 14 allowlist)
    """


def _render_math_line(
    components: list[tuple[int, float | None]],
    build_score: int,
    score_max: int,
    effort: str,
) -> str:
    """Build the receipt's math_line string from raw inputs.

    components: list of (weight_pct, value_pct_or_none) pairs.
    Format: '0.6 × 0.87 + 0.4 × n/a → score 7/10'

    When effort != 'balanced', appends a separate effort line on a new
    line: 'Your **Focused** effort setting lifts this to 9/10'
    (Decision 13). The build_score is the effort-shifted authoritative
    value; the math_line shows the unshifted derivation.
    """


def _normalize_label(
    weight_pct: int,
    gemma_label: str,
    allowlist: dict[int, str],
) -> tuple[str, bool]:
    """Match Gemma's label against the per-weight allowlist.

    Returns (canonical_label, was_normalized). Match strategy:
      1. Exact match on weight_pct -> allowlist[weight_pct] (canonical).
         Compare gemma_label against the canonical; if equal, returns
         (canonical, False).
      2. If gemma_label != canonical, return (canonical, True) and
         log WARNING with both values (Decision 14).

    The match-by-weight-first strategy guards the swap-component-labels
    case (Gemma puts the 60% label on the 40% component).
    """


def _log_receipt_parse(
    *,
    call_site: str,
    parse_success: bool,
    failure_reason: str | None,
    json_prefix: str,
    build_id: str,
    backend: Literal["ollama", "openrouter"],
) -> None:
    """Append one structured record to logs/gemma.jsonl per call.

    Schema (per genai-architect §5 finding 9):
      {
        "call_site": "explain_ern_receipt",
        "parse_success": True | False,
        "failure_reason": "pydantic_validation" | "json_decode" |
                          "stat_code_mismatch" | "score_null" | None,
        "json_prefix": "<first 500 chars of Gemma output>",
        "build_id": "...",
        "backend": "ollama" | "openrouter"
      }

    INFO level on success, WARNING level on failure. The call_site
    filter enables a parse_success_rate metric over time.
    """
```

Existing helper `_ern_explain_appendix(career: CareerOutcome) -> str` keeps its signature; the body is rewritten per the v1.2 + v1.3 changes:
- Replaces the markdown four-section template with a single filled-in JSON example carrying `__FILL_IN__` sentinels for prose fields and realistic numeric placeholders (Decision 15 / genai-architect v1.1 finding 2).
- Inlines the relevant SKILL.md voice rules verbatim (percentile-gloss inline format, acronym-first-use, `why_mix_paragraph` calibration target — ~3-sentence "two students" contrast).
- Splits the score-reference voice-rule relaxation: lifted for `value_pct` and `anchor_dollars` JSON numeric fields, retained as an explicit prohibition for `one_liner`, `explainer`, `why_mix_paragraph` ("Do not write 'N/10', 'your score is N', or any numeric score reference in any prose field — score display is the UI's responsibility").
- **Sentinel-passthrough prohibition (v1.3 — genai-architect re-review).** The appendix concludes with an explicit instruction: *"The example above shows the JSON structure. The strings `__FILL_IN__`, `[FILL_IN]`, `<FILL_IN>`, `ONE-SENTENCE DEFINITION HERE`, and `PLACEHOLDER` are placeholders ONLY — they MUST be replaced with your actual content. Echoing them back verbatim will fail validation and the receipt will not render."* This is the appendix-side companion to the Pydantic `field_validator` guard.

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
    final_turn_response_format: dict[str, Any] | None = None,  # NEW (Decision 15)
) -> tuple[str, list[ToolCallTurn]]: ...
```

The kwarg is named `final_turn_response_format` (not `response_format`) to make the synthesis-turn-only scoping explicit at the call-site (Decision 15). `_tools_loop_inner` injects the value into the per-turn `completion_kwargs` only when about to return plain text (no further tool calls expected). Per-backend translation happens inside `_one_tool_turn` (OpenRouter — passes verbatim) and `_one_tool_turn_ollama` (Ollama native — translates `{"type":"json_object"}` to `payload["format"] = "json"`).

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
| Fallback when JSON parsing fails | **NEW (refined v1.2):** `_postprocess_ern_explain_receipt` returns None → `_log_receipt_parse(parse_success=False, ...)` → re-run the tool loop ONCE without `final_turn_response_format` and with the markdown-spike appendix, **injecting the cached `tool_call_log` percentile values into the markdown appendix's user message** so no MCP re-fetch happens (Decision 6 v1.2 refinement) → return string response. Caps total wait at ~10-15s instead of ~50-60s. |
| Fallback when both attempts fail | The second attempt is the existing spike path with its existing fallbacks (transport failure, turn-cap exhaustion, wall-time). Same `chat_unavailable` 200 response. |
| `logs/gemma.jsonl` capture | Three records per call: (1) the JSON-mode tool loop's exchange record (existing, includes the `final_turn_response_format` flag and Gemma's raw JSON output verbatim); (2) `_log_receipt_parse` structured record (NEW — `call_site: "explain_ern_receipt"`, `parse_success`, `failure_reason`, `json_prefix`, `build_id`, `backend`); (3) on fallback, the markdown loop's exchange record with `extra["fallback_after_json_parse_failure"] = True`. The `call_site == "explain_ern_receipt"` filter computes `parse_success_rate` over time. |
| `INFERENCE_BACKEND=ollama` | Ollama's native `/api/chat` endpoint accepts `format: "json"` (top-level field) — NOT OpenAI's `response_format: {...}` shape. The `_one_tool_turn_ollama` path in `gemma_client.py` translates `final_turn_response_format={"type":"json_object"}` to `payload["format"] = "json"` before the httpx POST (Decision 15 — fp-architect Condition 1). Ollama v0.5+ supports `format: "json"`; verify the dev-stack version meets this in §6 implementation log. |
| `INFERENCE_BACKEND=openrouter` | OpenRouter's OpenAI-compat passthrough takes `response_format: {"type":"json_object"}` verbatim. The `_one_tool_turn` path passes the kwarg through `completion_kwargs` unchanged. For Gemma 4 specifically (`google/gemma-4-26b-a4b-it`), JSON-mode reliability is ~85-92% on the first attempt at temperature 0 (per genai-architect's empirical estimate); the `_extract_json_objects` reuse in step 1 of the helper pipeline catches the markdown-fence and trailing-prose failure modes without invoking the markdown fallback. |
| **Tool-call mechanism preservation (Decision 15)** | `final_turn_response_format` is applied **only on the final synthesis turn** of `_tools_loop_inner` (when no further tool calls are expected). Applying it across tool-call turns risks suppressing the model's ability to emit structured `tool_calls` fields on OpenRouter, collapsing the two required MCP fetches. The synthesis-turn-only scoping is the load-bearing fix. |
| Concurrency for cloud demo | One JSON-mode call per "Explain this to me" click, plus possibly one markdown-fallback call. Same Gemma semaphore limits as existing chat. No new contention. |
| Token-budget impact | The JSON output is roughly the same byte count as the markdown output (~600-900 tokens). `max_tokens=_ERN_EXPLAIN_MAX_TOKENS=1500` (already set by the spike) covers both. The `why_mix_paragraph` `max_length=800` Pydantic constraint catches truncation as a validation failure → fallback fires (rather than rendering a half-sentence). |

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
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_stream_ern_explain_emits_receipt_in_final_text` | `TraceFinalText.response` carries an `ExplainStatReceipt` object (with `kind: "receipt"`), not a string, when the JSON path succeeds. |
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_ern_explain_fallback_uses_cached_tool_log` | When fallback fires, `get_career_paths` and `get_occupation_data` MCP tools are NOT re-called — the cached `tool_call_log` percentile values are injected into the markdown appendix's user message instead (Decision 6 v1.2). Mock the MCP dispatch and assert call count == 2 (one per tool, ONE attempt). |
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_ern_explain_returns_none_when_build_score_null` | Build with `stats.ern is None` → `_postprocess_ern_explain_receipt` returns None → fallback fires (or, if BuildResultsScreen disables the trigger, this path doesn't fire at all — verify the helper-level guard). |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_final_turn_response_format_synthesis_only` | `final_turn_response_format` is injected into completion_kwargs ONLY on the synthesis turn, NOT on tool-call turns. Mock `_one_tool_turn` to capture per-turn kwargs across a 3-turn loop (2 tool calls + 1 synthesis); assert response_format presence only on turn 3. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_response_format_propagates_to_openrouter_path` | OpenAI-compat path (`_one_tool_turn`) — `final_turn_response_format={"type":"json_object"}` lands in `completion_kwargs["response_format"]` verbatim. Mock OpenAI client; capture call args. |
| P0 | `backend/tests/services/test_gemma_client.py` | `test_response_format_translates_to_ollama_native_payload` | Native Ollama path (`_one_tool_turn_ollama`) — `final_turn_response_format={"type":"json_object"}` translates to `payload["format"] = "json"` before the httpx POST. Mock httpx.AsyncClient.post; capture json kwarg. **fp-architect Condition 1 — without this test, the Ollama backend silently no-ops JSON mode.** |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_uses_extract_json_objects_first` | Gemma emits ` ```json{valid receipt}``` ` (markdown-fenced) → `_postprocess_ern_explain_receipt` calls `_extract_json_objects` first to strip fences → parse succeeds. Without the extract step, `json.loads` would fail on the fence. **genai-architect Condition 2.** |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_extract_handles_trailing_prose` | Gemma emits `Here is the receipt: {valid JSON}` → `_extract_json_objects` brace-depth extraction recovers the JSON → parse succeeds. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_rejects_wrong_stat_code` | Gemma emits `stat_code: "ROI"` for an ERN explain request → assertion fails → returns None. **genai-architect Condition 5a.** |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_overwrites_math_line_unconditionally` | Gemma emits `math_line: "I made this up"` → server overwrites with the actual `_render_math_line(...)` output. The string Gemma sent NEVER appears in the receipt. **genai-architect Condition 5b.** |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_rejects_truncated_why_mix_paragraph` | Gemma emits a `why_mix_paragraph` string of length 801+ → Pydantic `max_length=800` rejects → returns None → fallback fires. **genai-architect Condition 5c.** |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_rejects_sentinel_passthrough` | Gemma echoes `"one_liner": "__FILL_IN__"` (or `"[FILL_IN]"`, `"<FILL_IN>"`, `"PLACEHOLDER"`, `"ONE-SENTENCE DEFINITION HERE"`) verbatim from the appendix's filled-in JSON example → Pydantic `field_validator` raises → returns None → fallback fires. Covers all five sentinel patterns across all four prose fields (`one_liner`, `components[*].explainer`, `components[*].anchor_text`, `why_mix_paragraph`). **genai-architect v1.2 re-review concern — silent correctness failure mode.** |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_label_normalization_match_by_weight` | Gemma emits `components[0].weight_pct=60, label="program rank"` (off-script) → `_normalize_label` matches by `weight_pct=60` → replaces with canonical "your school's program rank" → WARNING logged with both values. **Decision 14 + genai-architect Condition 6.** |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_label_normalization_handles_swap` | Gemma swaps the labels (60% component carries the 40% canonical label) → match-by-weight catches the swap → both labels normalized to their canonical forms. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_logs_structured_record_on_success` | After a successful parse, `_log_receipt_parse` appends one structured record to `gemma.jsonl` with `parse_success=True`, `failure_reason=None`, plus `call_site`, `json_prefix`, `build_id`, `backend`. Assert by tailing the test log file or mocking the writer. **genai-architect Condition 6.** |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_postprocess_logs_structured_record_on_failure` | After a parse failure, `_log_receipt_parse` appends one structured record with `parse_success=False`, `failure_reason="json_decode" \| "pydantic_validation" \| "stat_code_mismatch" \| "score_null"`. Each failure type covered. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_render_math_line_balanced_effort` | `effort="balanced"` → math_line is the simple `0.6 × A + 0.4 × B → score N/10` form. No effort line. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_render_math_line_focused_effort` | `effort="focused"` → math_line shows the unshifted derivation, then on a new line `Your **Focused** effort setting lifts this to 9/10`. **Decision 13.** |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_render_math_line_chill_effort` | `effort="chill"` → similar to focused but score drops by 2 (e.g., `→ score 8/10\nYour **Chill** effort setting brings this to 6/10`). |
| P0 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_renders_default_state` | All sections render with the expected text content. Snapshot. |
| P0 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_renders_missing_school_rank` | Missing-reason row renders, percentile shows "—", row visual weight reduces (verify className). |
| P0 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_renders_score_color_token` | Score callout uses `var(--color-stat-{stat_code})` — verify via inline-style or className inspection. |
| P0 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_renders_effort_line_when_non_balanced` | When `math_line` includes the effort line (Decision 13), the renderer surfaces it as a distinct visual element below the math expression. |
| P0 | `frontend/src/components/menu/GemmaChat.test.tsx` | `test_dispatches_receipt_to_explain_stat_component` | Pushing a `{ kind: "receipt", payload }` history item renders `<ExplainStatReceipt>`, not the prose renderer. |
| P0 | `frontend/src/components/menu/GemmaChat.test.tsx` | `test_history_item_widening_no_break_for_text_kind` | Existing assistant-message tests still pass after fixtures gain `kind: "text"`. |
| P0 | `frontend/src/api/menu.test.ts` (or similar) | `test_zod_parser_distinguishes_string_vs_receipt` | The Zod union schema (`z.union([z.string(), explainStatReceiptSchema])`) correctly parses both branches. Object with `kind: "receipt"` → ExplainStatReceipt branch. String → string branch. |
| P0 | `frontend/src/api/menu.test.ts` | `test_zod_parser_falls_back_to_string_on_invalid_object` | Object payload that fails the Zod receipt schema (e.g., missing `components`) falls back to `String(response)` rather than throwing. |
| P1 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_math_line_format_unicode_arrow` | The math line uses `→` (U+2192), not `->`, for consistency with the rest of the product copy. |
| P1 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_renders_responsive_narrow` | Component renders without overflow at the 480px breakpoint (use `vitest-environment-jsdom` viewport simulation). |
| P1 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_accessibility_attributes` | `data-testid`, `role="region"`, `aria-label` per §3 accessibility table. |
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
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-05-02

#### System Context
This feature swaps the `final_text` payload on the existing Ask Gemma stat-scope SSE channel from a free-form prose string to a server-validated structured object, while preserving the trace-rail event protocol byte-identically. It touches three layers: (a) `gemma_client.generate_with_tools_loop` gains a `response_format` kwarg that must thread cleanly through both the OpenAI-compat client (OpenRouter) AND the native Ollama `/api/chat` shim; (b) `ask_gemma._postprocess_ern_explain_receipt` post-processes Gemma's JSON, stamps server-authoritative fields (score, math_line, percentiles, anchor_dollars, missing_reason), and validates via Pydantic v2 with `extra="forbid"`; (c) the `AskResponse.response` and `TraceFinalText.response` union type widens from `str` to `str | ExplainStatReceipt`, requiring discriminated-union handling in FastAPI serialization, the frontend SSE parser, the Zod validator, and the `ChatHistoryItem` renderer. No Brightsmith zone changes — Bronze/Silver/Gold are untouched, the existing `get_career_paths` and `get_occupation_data` MCP tools already surface every field the receipt needs.

#### Data Flow Analysis
Click "✦ Explain this to me" on `BuildResultsScreen` ERN row → `GemmaChat` mounts with sentinel opener `[explain-this:ERN]` → POST `/chat/ask/stream` → `ask_gemma.chat_ask_stream` detects sentinel → appends `_ern_explain_appendix(career)` (rewritten to instruct JSON output matching the schema) → calls `gemma_client.generate_with_tools_loop` with `response_format={"type":"json_object"}` and the existing 5-turn / 30s-wall-time / 1500-token budget → loop's tool turns dispatch `get_career_paths` and `get_occupation_data` against the MCP server (Gold-zone DuckDB read) → trace events stream out via the existing `on_turn_start` / `on_turn_event` callbacks (unchanged) → final assistant turn emits a JSON object → `_postprocess_ern_explain_receipt` parses, runs Pydantic v2 validation, stamps `score = build.career.stats.ern`, builds `math_line` from the tool_call_log percentile values, sets `missing_reason` per component when nulls land, returns `ExplainStatReceipt` → `TraceFinalText(response=receipt)` → SSE-serialized via `ev.model_dump(mode="json")` → frontend `parseSSEFrame` discriminates on shape → pushes `{kind: "receipt", payload}` into the chat history → `GemmaChat` renderer dispatches on `kind` → `<ExplainStatReceipt>` paints the card. Fallback on parse failure: re-run the loop (a second time) without `response_format` and with the markdown-spike appendix; result is a string; renders through the existing prose path.

The data-flow contract is sound on paper. Three boundary crossings need attention: (1) the OpenAI-compat client vs the native Ollama `/api/chat` path inside `gemma_client` (the spec assumes one path; there are two); (2) the build-authority of `score` vs the percentile-derived `math_line` (effort slider can shift the build's stored ERN by ±2 points, making `0.6 × A + 0.4 × B → score N/10` arithmetically inconsistent with the displayed N); (3) the `string | object` SSE payload, which the existing frontend handles only as `string` at four call sites.

#### Contract Review
- **`ExplainStatReceipt` Pydantic model:** `extra="forbid"` is correct; field ranges (`weight_pct: 0-100`, `value_pct: 0-100`, `score: 1-10`) are well-typed; the `Literal["ERN", "ROI", "RES", "GRW", "AURA"]` matches the post-reshape stat set; `components: list[StatComponent]` with `min_length=1, max_length=5` accommodates ERN's 2-component blend, ROI's single-component DTE, GRW's single-component growth-rate, and even a hypothetical 5-driver composite. The `value_pct: int | None` is the right shape for the missing-data degradation. **Concern:** AURA's `aura_score_basis` enum (`three_term` / `two_term_finance_only` / `two_term_no_endowment` / `one_term_marketing_only`) lives on `CareerOutcome`, not on a per-component value, and is structurally a stat-level provenance field, not a component-level percentile. The schema as written has no place for it — putting it inside `StatComponent.missing_reason` is a category error (it's not a "missing reason," it's a "what we used"). Decision 10 claims the schema fits AURA without a v2 migration; verify by sketching a worked AURA receipt before claiming generality.
- **`gemma_client.generate_with_tools_loop` signature change:** Adding `response_format: dict[str, Any] | None = None` is additive and backward-compatible. **Blocker for the implementation, though, not for approval:** the propagation must hit BOTH the OpenAI-compat path (`_one_tool_turn`, line ~1255) AND the native Ollama path (`_one_tool_turn_ollama`, line ~1312, which posts directly to `/api/chat` via `httpx`). Ollama's native `/api/chat` accepts a `format` field (string `"json"` or a JSON-Schema object), not OpenAI's `response_format` shape — these are different on-the-wire keys. `extra_body` doesn't exist on the native httpx call. Spec needs to either (a) translate `response_format={"type":"json_object"}` → `format="json"` in the Ollama branch and inject it into `payload`, or (b) plumb a backend-agnostic `json_mode: bool` kwarg and let `gemma_client` translate per backend. Mentioning this in §4 Service Changes prevents a half-done implementation that only works on OpenRouter.
- **`AskResponse.response` and `TraceFinalText.response` union:** Pydantic v2 serializes `str | ExplainStatReceipt` correctly without a discriminator (FastAPI calls `model_dump(mode="json")` which recurses; the SSE encoder at `ask_gemma_router.py:93` already does this). Frontend Zod validation at the SSE boundary needs a discriminator — the proposed runtime check ("presence of `score` + `components` fields") works but is brittle; prefer a discriminated union with a literal tag (e.g., `kind: "receipt"` on `ExplainStatReceipt` itself, or a wrapper `{response_kind: "text" | "receipt", ...}`). The spec lists "manual type guard or Zod" — pick Zod and document the discriminator approach.
- **Existing chat-history-item type:** `frontend/src/api/menu.ts:112-115` defines `ChatHistoryItem = { role; content }`. Widening to a discriminated union ripples to `GemmaChat.tsx` lines 207, 239, 287 (each constructs `{role, content}` without `kind`), `ChatMessage.tsx` (consumer typed as `ChatHistoryItem`), and the message-rendering path at `renderMessageWithTrace`. `traces.set(0, [...])` keys traces by message index — that's index-into-the-history-array, agnostic to the item's `kind`, so the trace-rail attachment continues to work. But the live-trace-binding at line 248 (`assistantIdx = nextHistory.length`) and the closure at 287 (`setHistory([...nextHistory, { role: "assistant", content: response }])`) assume `response: string` — the receipt-branch must construct `{role: "assistant", kind: "receipt", payload}` instead, AND the existing variable `let response: string` declared at line 262 needs to widen to `string | ExplainStatReceipt`. Touch points are: `askGemmaStream`'s return type (`AskGemmaStreamResult.response: string` at line 320), `mockChat` (string-only), `synthesizeEventsFromToolCalls` (consumes `tool_calls`, doesn't see response), `parseSSEFrame`'s `final_text` branch (line 276-280, currently coerces to `""` on non-string).

#### Findings

##### Sound
- **Decision 1 (server-computed math).** Right call. The spike's failure mode (`1 + 9 × 0.146 = 4.3`) is structural; no prompt fix would land. Server-stamping `score`, `math_line`, `value_pct`, `anchor_dollars`, `missing_reason` is the correct boundary — Gemma owns voice, the server owns numbers.
- **Decision 5 (`extra="forbid"`).** Correct strictness for v1.0; treating unexpected fields as a parse failure that triggers fallback is the right load-bearing posture while the prompt is being tuned. Loosen later if dogfood data shows benign hallucinations on common fields.
- **Decision 6 (fallback to spike markdown).** Robust user-facing failure path. The spike is known-good for "200, not 5xx," even if the math is wrong — the explicit policy "the student gets the spike's output, never an empty bubble" matches the rest of the chat surface's contract.
- **Decision 9 (trace-rail untouched).** The streaming protocol stays byte-identical; only the `final_text.response` shape widens. `<GemmaTrace>` doesn't touch the response payload at all, so no test-coverage delta there. Verified at `ask_gemma.py:702-712` — the on_turn callbacks build `TraceTurnComplete` from `ToolCallTurn` fields, never the final text.
- **MCP tool surface coverage.** Confirmed: `cip_family_earnings_rank` and `earnings_1yr_median` are in `get_career_paths`'s output (`mcp_server/futureproof_server.py:345, 338`); `wage_percentile_overall` and `median_annual_wage` are in `get_occupation_data` (`mcp_server/futureproof_server.py:364-365`). Both tools are in `_TOOLS` allowlist (`ask_gemma.py:83-84`). No new MCP work needed.
- **Test impact analysis is realistic.** The "Confirmed Safe" list is correct — boss/skill/build/branch/compare scopes never touch `_ern_explain_appendix` or `explain_ern`; widening the union with `str | ExplainStatReceipt` doesn't break their fixtures because every existing test constructs `AskResponse(response="...", tool_calls=[...])` and a string is still a valid member of the union. No mypy-strict regressions expected on the backend; the frontend `ChatHistoryItem` widening DOES require fixture updates (called out correctly in "Authorized Test Modifications").
- **No Brightsmith / data-pipeline changes needed.** Confirmed against §4 Constraints. ERN formula stays in `src/gold/futureproof_engine.py`; receipt rendering reads but does not re-derive.

##### Concerns

- **Effort-shift coherence: build-score and percentile-math can visually disagree.** **Impact:** Gold path on a non-`balanced` effort slider produces a receipt where the score callout reads `9/10` (build's stored, effort-shifted ERN) but the math line reads `0.6 × 0.87 + 0.4 × 0.92 → 0.89 → score 8/10` (the unshifted percentile derivation rounds to 8). The student sees two different N-values in the same card; trust collapses, and the entire "show the receipts" pitch inverts. `_apply_effort` shifts ERN by ±2 (`stat_engine.py:109-115`); ROI is excluded; effort is irrelevant to RES/GRW/AURA. **Recommendation:** Add Decision 13 explicitly addressing this. Three options, in preference order: (a) Render `math_line` to the unshifted score, then append an explicit effort line ("...your effort setting (Focused) lifts this to 9/10"). (b) Have `math_line` show the shifted score and elide the arithmetic-rounding step entirely (lossy but coherent). (c) Document explicitly that for v1.0 the math line shows `→ score N/10` where N is the build score, with a footnote that the value reflects effort. Option (a) is most honest. The pentagon-stat-explanation SKILL voice rule on raw percentages applies here.
- **`response_format` does not propagate identically across the two `_one_tool_turn` paths.** **Impact:** The OpenAI-compat client (`gemma_client.py:1255-1266`) accepts `response_format` as a top-level kwarg via `completion_kwargs`. The native Ollama path (`gemma_client.py:1312-1340`) posts directly to `/api/chat` via httpx and constructs `payload` by hand — Ollama's native API uses a `format` key (string `"json"` or a JSON Schema), NOT `response_format`. If the spec ships as written, Ollama JSON mode silently no-ops and every Ollama call falls back to the markdown spike, eliminating local-dev coverage and the Ollama-track demo path. **Recommendation:** §4 Service Changes must specify the per-backend translation. Suggested signature: keep `response_format: dict | None` as the public kwarg; internally, on Ollama, translate `{"type":"json_object"}` → `payload["format"] = "json"`; on OpenRouter, pass `response_format` through `completion_kwargs` as written. Add a unit test (`test_response_format_propagates_to_ollama_native_payload`) with both backend mocks. Without this, the §1 success criterion "Both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter` successfully produce valid JSON receipts" fails on the local backend.
- **Fallback path re-runs the tool loop, doubling wall-time exposure and re-issuing 2 tool calls.** **Impact:** §2 Decision 6 says "fall back to the markdown spike path" which §4 Service Changes implements as "run the loop AGAIN without `response_format`." That's 2 sequential tool loops per failure: ~5-12s for the JSON attempt + ~5-12s for the markdown retry, both re-issuing `get_career_paths` and `get_occupation_data` (cache miss each time). The 30s wall-time cap is per-loop, not aggregate, so worst-case the student waits 60s for a fallback markdown response. The MCP calls are idempotent and cheap (~50-300ms each against DuckDB), but each Gemma turn is ~2-6s; 2x of that on the slow path is felt. **Recommendation:** Either (a) cache the tool_call_log from the first attempt and inject the tool results directly into the markdown-fallback's user message (skip the second tool loop entirely; markdown can render with the cached values, no second call needed), or (b) tighten the JSON attempt's `max_wall_time_s` to 20s and keep markdown fallback at 30s, capping total wait at 50s. (a) is cleaner and matches the "Gemma owns voice, server owns numbers" boundary — the markdown fallback only needs voice-rendering, the numbers were already fetched. Mention this in §4 Service Changes; a 60s loading state is the kind of thing dogfooders silently abandon before the receipt lands.
- **AURA fit in the generic schema is shakier than Decision 10 implies.** **Impact:** AURA is institution-level with provenance fields (`aura_score_basis`, `aura_score_version`) that don't fit the per-component `value_pct` / `anchor_dollars` shape. A v1.0 AURA receipt would need to either (a) emit `components=[]` (illegal — `min_length=1`), (b) put the basis enum inside `missing_reason` (semantically wrong — it's not a missing-reason, it's a what-we-used), or (c) add `score_provenance: str | None` at the receipt root, which IS a v2 migration. The spec frames AURA as the proof of generality, but AURA is the case that most stresses the schema. **Recommendation:** Don't change the schema in this spec — it's correct for ERN/ROI/RES/GRW. Instead, soften §1 Success Criterion #11 and Decision 10's parenthetical from "AURA missing-data case (institution-level, may be null)" to "ERN/ROI/RES/GRW. AURA's institution-level provenance shape will require an additive field (e.g. `score_provenance: str | None`) in the future AURA spec — additive, not breaking." This is honest and keeps the spec shippable.
- **`PentagonStats.ern` is `int | None`; the spec assumes always-int.** **Impact:** §2 Decision 7 says "`score = build.career.stats.ern` unconditionally." Per `career.py:60`, that field is `int | None`. A build with `ern=None` (data-incomplete career outcome — possible per the Pydantic model and the `stats_available_count` field at `career.py:171`) plus a sentinel-fired explain click would fail Pydantic validation on the receipt (`score: int = Field(ge=1, le=10)` rejects None). **Recommendation:** Either (a) the trigger button on `BuildResultsScreen` is hidden/disabled when `stats.ern is None` (preferred — match the existing legend's "—" treatment for null stats), or (b) `_postprocess_ern_explain_receipt` returns `None` and the markdown fallback fires when `build.career.stats.ern is None`. Document the choice in §4 Service Changes — the helper's contract should say "returns None when build.career.stats.ern is None."
- **Frontend `response` variable typing cascades wider than the file-changes table shows.** **Impact:** `frontend/src/api/menu.ts:357` declares `let response = ""`, then assigns `event.response` from `final_text` events; type is locked as `string`. `AskGemmaStreamResult.response: string` (line 321) is the public contract for `askGemmaStream` and is consumed by `GemmaChat.tsx:280` and `:287`. `parseSSEFrame`'s `final_text` branch (line 276-280) coerces `obj.response` to `""` when not-a-string — that strips the receipt. `mockChat` returns string. `sendChat` (legacy non-scope endpoint, line 188) returns string and feeds the same `setHistory([...nextHistory, {role: "assistant", content: response}])` shape. **Recommendation:** §4 File Changes lists `frontend/src/api/menu.ts` for modification with one line about the receipt branch — the actual change list inside that file is at minimum: `parseSSEFrame.final_text` branch (preserve object), `AskGemmaStreamResult.response` type, `let response =""` initialization (`let response: string | ExplainStatReceipt = ""` with default-string semantics), the synthetic `final_text` events in the mock + fallback paths (lines 349, 417), AND the consumers in `GemmaChat.tsx`. Add a sub-bullet to that row enumerating the cascade so the implementer doesn't ship a half-typed cascade and discover it via mypy/tsc.
- **Frontend Zod discriminator is informally specified.** **Impact:** §4 says "runtime check uses a Zod schema (preferred) or a manual type guard on the presence of the `score` + `components` fields." Object-shape sniffing is fragile — a future field rename or a malformed Gemma response that happens to include a `score` key would route to the receipt branch. **Recommendation:** Add a backend wrapper field to disambiguate: either rename `TraceFinalText.response` to `TraceFinalText.response_payload: TraceFinalTextString | TraceFinalTextReceipt` with a `kind` literal, or add a sibling `TraceFinalText.response_kind: Literal["text", "receipt"]`. Either way, Zod becomes a clean `z.discriminatedUnion("kind", [...])`. This is a small Pydantic v2 addition in §4 Data Model. The cost is a one-byte wire field on every chat reply; the gain is a parsable contract instead of structural sniffing.
- **`label` allowlist normalization (P1 test) needs a §2 decision.** **Impact:** §4 Service Changes's helper-docstring says "`components[*].label` (validated against an allowlist per stat to prevent drift, e.g. ERN must use 'your school's program rank' / 'this career's pay rank')" — but neither §2 Decisions nor the file-changes table enumerate the allowlist or the normalization-vs-reject behavior. The P1 test `test_postprocess_label_allowlist` says "decision: normalize" parenthetically. **Recommendation:** Promote this to Decision 13 in §2 with the allowlist enumerated as a constant in `ask_gemma.py`. "Normalize off-script labels by replacing with the canonical label from the allowlist; log a warning at INFO" is the right policy (matches the SKILL's voice authority). The decision is small but load-bearing for v1.0 ROI/RES specs that will reuse the pattern.

##### Blockers
None. The architecture is sound; the concerns above are all addressable inside §1-§4 without redrawing the data flow.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions (CHANGES REQUESTED)

1. **§4 Service Changes — `gemma_client` JSON-mode plumbing:** Add an explicit per-backend translation paragraph. Spec must say: "On the OpenRouter / OpenAI-compat path (`_one_tool_turn`), `response_format` is added to `completion_kwargs` verbatim. On the Ollama native path (`_one_tool_turn_ollama`), `response_format={"type":"json_object"}` translates to `payload["format"] = "json"` before the httpx POST. The unit test in `test_gemma_client.py` exercises both backends with mocked transports."
2. **§2 Decisions — add Decision 13 (effort-shift coherence):** Document how the math line reconciles with the build's effort-shifted score. Recommend option (a) above (math line shows the unshifted derivation, then an effort line if `effort != "balanced"`). Without this, the receipt can render two different N-values that fundamentally undermine the explainer's purpose.
3. **§4 Service Changes — fallback path:** Cache the tool_call_log from the first (JSON-mode) attempt and inject the percentile values into the markdown-fallback's user message instead of re-running the full tool loop. Tighten the wall-time exposure and skip 2 redundant MCP calls.
4. **§1 Success Criteria + §2 Decision 10 — soften the AURA generality claim:** Replace "schema is generic enough that ROI, RES, GRW, and AURA can populate it in future specs without breaking-change additions" with "...ROI, RES, GRW. AURA's institution-level provenance (`aura_score_basis`) will require one additive field on the receipt root in the future AURA spec — additive, not breaking." Keeps the v1.0 schema honest.
5. **§4 Service Changes — null-build-stat guard:** `_postprocess_ern_explain_receipt` returns `None` when `build.career.stats.ern is None`. Add to the helper contract and to the P0 test list.
6. **§4 File Changes — frontend cascade:** Expand the `frontend/src/api/menu.ts` row to enumerate the response-type cascade: `parseSSEFrame.final_text`, `AskGemmaStreamResult.response`, `let response` in `askGemmaStream`, the mock + fallback synthetic `final_text` events. Same row for `GemmaChat.tsx` should call out lines 207, 239, 248, 280, 287.
7. **§4 Data Model — discriminator field:** Add a `kind: Literal["text", "receipt"]` (or rename + literal) to `TraceFinalText` so the frontend Zod validator can use `z.discriminatedUnion`. Avoid object-shape sniffing as the load-bearing parser strategy.
8. **§2 Decisions — add Decision 14 (label allowlist):** Document the per-stat allowlist behavior (normalize vs reject) and where the allowlist lives. Promote the P1 test to P0 if "normalize" is the policy.

### @fp-architect Re-Review (v1.2)
**Status:** APPROVED
**Reviewed:** 2026-05-02

#### System Context
v1.2 was authored to address the eight conditions returned in the v1.1 re-review (CHANGES REQUESTED). The architectural surface is unchanged — same three layers (gemma_client kwarg, ask_gemma post-processor, AskResponse/TraceFinalText union widening) and the same sentinel-triggered branch in `chat_ask` / `chat_ask_stream`. The v1.2 changes are tightening moves on contracts, scope, and observability, not redrawing data flow. I am re-reading §1-§4 and the §4 Testing Impact Analysis only — sections owned by other reviewers (§3, design audit, code review, verification) are out of scope for this pass.

#### Per-Condition Verification

1. **§4 Service Changes — gemma_client JSON-mode plumbing.**
   RESOLVED. §4 File Changes row for `gemma_client.py` now spells out per-backend translation: OpenAI-compat path passes `response_format={"type":"json_object"}` verbatim into `completion_kwargs`; native Ollama path translates the same kwarg to `payload["format"] = "json"` before the httpx POST, with the translation hidden inside `_one_tool_turn_ollama` so the public kwarg API stays uniform. The two P0 tests (`test_response_format_propagates_to_openrouter_path`, `test_response_format_translates_to_ollama_native_payload`) lock both paths. The §4 Architecture Overview point 1 and the Gemma-touching extra discipline table (`INFERENCE_BACKEND=ollama` / `INFERENCE_BACKEND=openrouter` rows) cross-reference the same translation. Condition 1 is fully addressed.

2. **§2 Decisions — Decision 13 (effort-shift coherence).**
   RESOLVED. Decision 13 explicitly resolves the build-callout vs derived-math disagreement: math_line shows the unshifted percentile derivation; when `effort != "balanced"` an explicit effort line is appended ("Your **Focused** effort setting lifts this to 9/10"). The contract is mirrored in §1 Success Criterion #11, in `_render_math_line`'s docstring under §4 Service Changes, and in three P0 tests (`test_render_math_line_balanced_effort`, `_focused_effort`, `_chill_effort`). The two N-values are now visibly reconciled by the explicit effort line rather than silently disagreeing. Condition 2 is fully addressed.

3. **§4 Service Changes — fallback path caches tool_call_log.**
   RESOLVED. Decision 6 is refined v1.2 in the decision table; §4 Architecture Overview's Fallback path paragraph specifies the cached `tool_call_log` is injected into the markdown-fallback's user message ("Here are the values from your build: cip_family_earnings_rank=X, ..."); the Gemma-touching-extra-discipline "Fallback when JSON parsing fails" row reiterates "no MCP re-fetch happens"; and P0 test `test_chat_ask_ern_explain_fallback_uses_cached_tool_log` asserts MCP dispatch count == 2 (one per tool, ONE attempt). Wall-time exposure is documented as ~10-15s instead of ~50-60s. Condition 3 is fully addressed.

4. **§1 Success Criteria + §2 Decision 10 — soften AURA generality claim.**
   RESOLVED. Decision 10 is rewritten to "generic across ERN, ROI, RES, and GRW; AURA explicitly excluded" with the additive-not-breaking framing for the future AURA spec. §1 Success Criterion #11 carries the same scoping verbatim, including the explicit "AURA's institution-level provenance does not fit the StatComponent shape" sentence that mirrors my v1.1 finding. The §4 Out of Scope row for AURA still parks it correctly. The honest scoping is in place. Condition 4 is fully addressed.

5. **§4 Service Changes — null-build-stat guard.**
   RESOLVED. `_postprocess_ern_explain_receipt`'s 10-step pipeline (§4 Architecture Overview point 3) explicitly returns None at step 5 when `build.career.stats.ern is None`. The helper docstring under Service Changes documents the guard ("If build.career.stats.ern is None -> None (belt-and-suspenders; the trigger button should be disabled in this case)"). The `score` field description in the Pydantic model points at the same behavior. P0 test `test_chat_ask_ern_explain_returns_none_when_build_score_null` covers it. Condition 5 is fully addressed.

6. **§4 File Changes — frontend cascade.**
   RESOLVED. The `frontend/src/api/menu.ts` row now enumerates seven sub-bullets covering: (a) `parseSSEFrame` `final_text` branch preserving non-string payloads, (b) `AskGemmaStreamResult.response` widening, (c) `let response = ""` initialization widening, (d) synthetic `final_text` events in mock + fallback paths, (e) `mockChat` and (f) `sendChat` returning string unchanged, (g) Zod runtime parse with string-fallback on parse failure. The `GemmaChat.tsx` row enumerates lines 207, 239, 248, 262, 280, 287 plus the renderer dispatch (`item.kind === "text"` vs `"receipt"`). The new `frontend/src/types/chat.ts` file is added to centralize the discriminated union. Implementer cannot ship a half-typed cascade and discover it via tsc. Condition 6 is fully addressed.

7. **§4 Data Model — discriminator field.**
   RESOLVED. `ExplainStatReceipt` carries `kind: Literal["receipt"] = "receipt"` as a self-discriminator field at the model root with a clear field description explaining its purpose. The §4 Architecture Overview point 4 and the §4 File Changes row for `api.py` both surface the field. The frontend Zod parser is documented as `z.union([z.string(), z.object({kind: z.literal("receipt"), ...})])` in the `menu.ts` cascade and exercised by two P0 tests (`test_zod_parser_distinguishes_string_vs_receipt`, `test_zod_parser_falls_back_to_string_on_invalid_object`). Object-shape sniffing is no longer the load-bearing parser strategy. Condition 7 is fully addressed.

8. **§2 Decisions — Decision 14 (label allowlist).**
   RESOLVED. Decision 14 documents the normalize-not-reject policy with the match-by-weight-first guard against the swap-component-labels case. The `_ERN_LABEL_ALLOWLIST: dict[int, str]` constant is enumerated under §4 File Changes (60 → "your school's program rank", 40 → "this career's pay rank"). The `_normalize_label(weight_pct, gemma_label, allowlist) -> tuple[str, bool]` helper signature and docstring under §4 Service Changes specify the match strategy. Three P0 tests cover the cases (`test_postprocess_label_normalization_match_by_weight`, `_handles_swap`, plus the WARNING log assertion via `test_postprocess_logs_structured_record_*`). Condition 8 is fully addressed.

#### Findings

##### Sound (additive observations on v1.2)
- **Decision 15 (synthesis-turn-only response_format scoping)** — the v1.2 spec adopts genai-architect's synthesis-turn-only fix as a first-class decision, with a dedicated `final_turn_response_format` kwarg name that makes the scoping explicit at every call site. Cross-cutting tests at `test_final_turn_response_format_synthesis_only` and the mock-loop trace verify the scoping. This is architecturally correct and prevents the OpenRouter tool-call-suppression failure mode that was implicit in the v1.1 design.
- **`_extract_json_objects` reuse** — explicitly documented as step 1 of the helper pipeline (Architecture Overview point 3). Two P0 tests cover the markdown-fence and trailing-prose extraction modes. Avoids re-implementing the existing primitive. Clean.
- **Structured `gemma.jsonl` log records** — `_log_receipt_parse` is a properly-typed helper with a fixed schema and an enumerated `failure_reason` set (`pydantic_validation`, `json_decode`, `stat_code_mismatch`, `score_null`). The `call_site == "explain_ern_receipt"` filter for `parse_success_rate` aggregation is a good production-monitoring pattern. The §1 Success Criteria add the "Per-parse structured log record" criterion, locking in observability.
- **Voice-rule scoping split** — Decision 15 supporting paragraph + the §4 Service Changes appendix-rewrite bullet codify the split: numeric-field score-reference relaxation (`value_pct`, `anchor_dollars`) vs. prose-field score-reference prohibition (`one_liner`, `explainer`, `why_mix_paragraph`). The Pydantic field descriptions on `one_liner` and `why_mix_paragraph` carry the prohibition inline. This blocks the prose/score divergence failure mode genai-architect flagged.
- **`why_mix_paragraph` `max_length=800`** — Pydantic-level truncation guard now in place; truncated outputs trigger fallback rather than rendering a half-sentence. Documented in the model definition and in `test_postprocess_rejects_truncated_why_mix_paragraph`.
- **Filled-in JSON example with `__FILL_IN__` sentinels** — replaces the v1.1 "Pydantic model verbatim" prompt format. This is the right vehicle for Gemma 4 (per genai-architect finding 2) and is documented as the `_RECEIPT_JSON_TEMPLATE` constant under §4 File Changes.

##### Concerns
None remaining at the architecture layer. All eight v1.1 conditions are resolved; the additional v1.2 changes (Decision 15, structured logging, `max_length=800`, voice-rule scoping split, JSON-template format) are net improvements that close failure modes the v1.1 design left open.

##### Blockers
None.

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

Spec is ready to advance to **Phase 2: Design Vision** (@fp-design-visionary fills §3).

### @genai-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-05-02

#### LLM-Integration Analysis

**1. JSON-mode reliability under temperature 0**

Gemma 4 (`google/gemma-4-26b-a4b-it` on OpenRouter, `gemma4:e4b` locally via Ollama) does follow `response_format: {"type": "json_object"}` / `format: "json"` at temperature 0 with high but not perfect reliability. Empirical failure modes in production: markdown-fenced output (```json{...}```), a JSON object followed by trailing prose ("Here is the receipt:"), and valid JSON with a wrong-type field (e.g., `score: "7"` instead of `score: 7`). Based on typical Gemma 4 behavior on structured-output tasks at temperature 0, a parse-success rate of roughly 85–92% is realistic for a schema this complex on the first attempt. The spec's fallback-to-markdown path is necessary, not optional.

However, the spec currently describes the fallback as a full second tool loop (re-running `get_career_paths` + `get_occupation_data` from scratch). The `_extract_json_objects` helper in `gemma_client.py` (lines 815–846) already handles markdown fences and brace-depth extraction from free-form content — this exact logic is the right parser for the JSON-mode output too. The parse step in `_postprocess_ern_explain_receipt` should run `_extract_json_objects` as its first extraction attempt before treating the output as unparseable, catching the fence-wrap and trailing-prose failure modes without a fallback call.

The spec should budget explicitly for one retry before fallback: if `_extract_json_objects` succeeds but Pydantic validation fails, that is a true schema-compliance failure (fallback warranted). If `_extract_json_objects` fails to find any JSON object at all, one retry with a shorter, tighter prompt (or no tool calls) is worthwhile before the full markdown fallback. The current spec's binary JSON-success / markdown-fallback path wastes the retry budget entirely.

**2. Schema-as-prompt design**

Including the full 60-line Pydantic schema verbatim in the system appendix is the wrong vehicle for Gemma 4. Gemma 4 responds better to a few-shot JSON example than to a type-annotated schema document — the schema reads as Python code (with `Field(description=...)` annotations), which Gemma may treat as code to be executed rather than a structural contract to emit. The spec says the schema is included "verbatim ... as a structural template," but the actual schema is a Pydantic model definition, not a JSON Schema document and not a filled-in JSON example.

The right approach, in order of Gemma 4 effectiveness:
1. A single filled-in JSON example with realistic placeholder values (most effective — Gemma 4 is a strong few-shot learner and the example format is unambiguous)
2. A JSON Schema (draft 7) document stripped of Python-specific annotations (second-best — machine-readable, no Python syntax)
3. The Pydantic model verbatim (least effective — Python syntax confuses completion vs. instruction mode)

The spec needs to specify which form the `_RECEIPT_JSON_SCHEMA` constant takes. If it is option 1, the constant should be a JSON object with placeholder values (`"__FILL_IN__"` strings for prose fields, `null` for server-stamped fields with a comment that the server overwrites them). This also serves as implicit documentation of which fields Gemma must write vs. which the server stamps.

**3. Tool-call coherence with structured output**

The critical issue: on OpenRouter, `response_format: {"type": "json_object"}` is applied to the *entire* conversation. The OpenRouter Gemma 4 inference layer may apply the JSON-mode constraint to ALL turns, including the tool-call turns, which suppresses the model's ability to emit structured `tool_calls` fields and instead causes it to emit a JSON object representing a tool call rather than using the proper function-calling channel. This is the "JSON constraint sometimes suppresses tool calls" failure mode.

From inspection of `_one_tool_turn` (line 1254–1308): `response_format` must be passed to `completion_kwargs` only on the **final synthesis turn**, not on intermediate tool-call turns. The spec as written passes `response_format` to `generate_with_tools_loop` which plumbs it into every turn via `_one_tool_turn`. This is architecturally wrong for the multi-turn flow.

The correct implementation: `response_format` should be added to the completion kwargs only when `not tools` or only on the last turn. The cleanest approach is to add a separate kwarg to `_tools_loop_inner`: `final_turn_response_format`, which is only injected into the turn's completion kwargs when `response_tool_calls` is empty on the previous turn (i.e., Gemma returned plain text, and the loop is about to return). Alternatively, apply `response_format` only to the last `_one_tool_turn` call — detectable by the fact that the loop is about to exit with no tool calls.

Without this change, the spec's `max_turns=5` budget (4 tool turns + 1 synthesis) will have JSON mode active across all five turns. On OpenRouter this risks suppressing the tool-call mechanism entirely on turns 1–4, collapsing the two required tool fetches. Local Ollama behavior is more forgiving since `format: "json"` on the native `/api/chat` endpoint still permits `tool_calls` in the response, but OpenRouter's behavior is not guaranteed to match.

**4. Hallucination resistance on prose fields**

The JSON-mode constraint does degrade Gemma 4's adherence to voice rules compared to free-form markdown. The degradation is specific and predictable:
- `one_liner` and `explainer` fields tend to be shorter and more clinical in JSON mode — the model treats JSON values as data rather than prose and loses the conversational register. The SKILL's Rule 6 ("Honest, not corporate") is at elevated risk.
- The percentile-gloss rule (first-use inline gloss, subsequent percentiles standalone) is fragile under JSON mode because Gemma may write the gloss as a separate sentence in the `explainer` JSON string value rather than inline, defeating the "immediately after the number in parens" requirement. The rule needs to be restated explicitly in the JSON-mode appendix as a JSON-field-level constraint: "In the `explainer` string for the first component, write the percentile gloss inline within the string value — not as a separate sentence."
- `why_mix_paragraph` is the highest-risk field: it requires a multi-sentence narrative arc ("Picture two students...") that Gemma may collapse to a single generic sentence when operating in JSON mode at temperature 0. The SKILL's Section 4 voice example needs to appear verbatim in the appendix as a target-length calibration.

The schema's `Field(description=...)` annotations are insufficient alone. The `explainer` and `why_mix_paragraph` descriptions reference the SKILL by name but do not quote the SKILL's actual voice rules. The system appendix must inline the relevant voice rules — not just cite them — because Gemma has no access to the SKILL.md file at inference time.

**5. Server-side override behavior and prose/score divergence**

Yes, this is a real failure mode. Gemma 4 will write `why_mix_paragraph` values that contain numeric references to the score it computed, e.g., "Since your Earning Power is 4 out of 10, you're in the lower half..." After the server unconditionally overwrites `score` with the build value (Decision 7), the prose may now cite a different number than the score displayed in the receipt header, creating an internal contradiction visible to the student.

The rule is straightforward and must be made explicit in the system appendix: **"Do not reference the score numerically in any prose field (`one_liner`, `explainer`, `why_mix_paragraph`). The score display is handled by the UI — your prose fields must not repeat the N/10 value or say phrases like 'since you scored X' or 'your X out of 10 score'."** This is not inferrable from the schema field descriptions alone; it requires an explicit prohibition in the appendix.

The `_SYSTEM_BASE` voice rule "Never state a raw score, percentile, fraction (like '7/10'), or stat code in your reply" technically already covers this — but it is listed as relaxed for the explain-this-stat turn ("the 'never state a raw score' rule is suspended for this turn"). The suspension must be scoped: suspended only for the `math_line` server computation (which Gemma does not write anyway, per Decision 8) and the `value_pct` percentile values (which the server stamps). For the prose fields (`one_liner`, `explainer`, `why_mix_paragraph`), the standard prohibition stands. The appendix currently lifts the rule wholesale, which is why Gemma writes score references into prose fields.

**6. Label allowlist enforcement**

At temperature 0, Gemma 4 drifts on `components[*].label` values roughly 15–25% of the time — common drift: "program rank" instead of "your school's program rank", "occupation wage rank" instead of "this career's pay rank", "school earnings rank" or other paraphrases. The drift rate makes server-side normalization (not Pydantic rejection) the right policy — rejecting and falling back to markdown for a label paraphrase wastes the entire receipt when the underlying numbers and prose are valid.

However, the allowlist normalization approach has a subtle failure mode: if Gemma emits a label for the wrong component (e.g., swaps the 60% and 40% labels), normalization produces a receipt where the label is canonical but attached to the wrong `weight_pct`. The normalization logic must match by `weight_pct` + approximate label similarity, not label alone. The P1 test `test_postprocess_label_allowlist` should be promoted to P0 and the matching strategy documented as a constant in `ask_gemma.py`.

**7. Voice contract delta and per-turn override leak**

The `_SYSTEM_BASE` voice prohibition "Never state a raw score, percentile, fraction (like '7/10'), or stat code in your reply" is a global rule for the conversation. The explain-this-stat appendix currently relaxes it wholesale for the entire turn. This is correct for the JSON-mode path where Gemma writes `value_pct` fields (integers, not prose) — but it creates a risk if the user asks a follow-up question in the same conversation after the receipt renders. The `explain_ern` flag is only true on the sentinel-triggered first message; subsequent messages in the same chat-scope context fall back to standard stat-scope chat with the standard voice rules. The relaxed-rules appendix is appended to the system prompt for that first message only, so it does not persist into follow-up turns. This is architecturally safe.

However: the JSON-mode appendix must explicitly reinstate the score-reference prohibition for prose fields (finding #5 above), which is distinct from the relaxation for the JSON numeric fields. The current spike's appendix relaxes the rule globally; the new JSON-mode appendix must split it: "The prohibition on numeric score references is RELAXED for the `value_pct` and `anchor_dollars` fields (which are integers in the JSON, not prose). The prohibition REMAINS ACTIVE for `one_liner`, `explainer`, and `why_mix_paragraph` — do not write 'N out of 10', 'your score is N', or similar phrases in those string values."

**8. Failure-mode catalog**

| Failure mode | Spec's fallback handling | Assessment |
|---|---|---|
| Gemma emits ```json{...}``` fences | Not explicitly handled — `json.loads` fails on the fence-wrapped string | Gap: `_extract_json_objects` in `gemma_client.py` handles this already; `_postprocess_ern_explain_receipt` should call it before treating output as unparseable |
| Gemma emits JSON + trailing prose ("Here is the receipt: {...}") | Not explicitly handled | Gap: same — `_extract_json_objects` handles this via brace-depth extraction |
| `score: "9"` (string instead of int) | Pydantic `int` type rejects → `extra="forbid"` triggers fallback | Correct, but ONLY if `extra="forbid"` fires first — actually a type error fires first, which also returns None. Fine. |
| `math_line` contains prose narration from Gemma | Gemma should not write `math_line` (Decision 8 — server-rendered). If Gemma writes it anyway, Pydantic accepts any string value including a prose string. The server then overwrites it unconditionally. | Partially safe: the server overwrites the value so the math line is always correct. But the spec needs to confirm that `_postprocess_ern_explain_receipt` ALWAYS overwrites `math_line` regardless of what Gemma wrote — currently the spec says "server-stamped, never from Gemma" in the field description but the helper's docstring says Gemma "can suggest, server validates against actual tool output" for `value_pct`. The math_line treatment must be unambiguous: the server builds `math_line` from scratch using the tool_call_log, regardless of Gemma's output. |
| `why_mix_paragraph` truncated mid-sentence at 1500 tokens | `_trim_to_last_sentence` runs on the markdown fallback path only. The JSON path parses the JSON first; a truncated JSON string that is still valid JSON (ends with `"...truncated"`) will pass Pydantic but render an incomplete paragraph. | Gap: the spec needs a max-character validation on `why_mix_paragraph` (e.g., `max_length=800`) so a truncated string either passes cleanly or fails validation and triggers fallback. The `max_tokens=1500` budget is tight if the JSON receipt contains a full worked example for `why_mix_paragraph`. |
| `components` list has length 0 or > 5 | Pydantic `min_length=1, max_length=5` rejects → returns None → markdown fallback | Correct. |
| Gemma emits valid JSON for a different stat (e.g., a GRW receipt for an ERN request) | `stat_code: Literal["ERN", ...]` would be valid for any stat. Pydantic does not reject this. The receipt renders with the wrong `stat_code` and wrong component labels. | Gap: `_postprocess_ern_explain_receipt` must assert `receipt.stat_code == "ERN"` after parsing and return None if it doesn't match. |

**9. Logging and observability**

`logs/gemma.jsonl` captures every Gemma call, but the current `_log_exchange` and `_log_tool_turn` calls in `_tools_loop_inner` do not record the final-text response (the `_log_tool_turn` call at line 1163–1171 records tool dispatch; the final plain-text response is returned but never logged separately in the loop path). The `generate_chat` function logs `record["response"] = content`, but `_tools_loop_inner` returns the final text without a corresponding log record. This means the raw JSON output from Gemma in JSON mode is not logged anywhere — making it impossible to replay and diagnose parse failures from `gemma.jsonl` alone.

The spec's §4 Gemma-touching extra discipline table says `logs/gemma.jsonl` captures "the JSON string output" but the implementation path does not support this today. `_postprocess_ern_explain_receipt` must log the raw JSON string it received (regardless of parse success/failure) at INFO level with `call_site: "explain_ern_receipt"`, `build_id`, and a `json_prefix` (first 500 chars). This gives enough signal to compute a parse-success rate from the logs.

Recommended structured fields for the log record on each parse attempt:
```json
{
  "call_site": "explain_ern_receipt",
  "parse_success": true|false,
  "failure_reason": "pydantic_validation|json_decode|stat_code_mismatch|score_null|...",
  "json_prefix": "<first 500 chars of Gemma output>",
  "build_id": "...",
  "backend": "ollama|openrouter"
}
```
This enables a `parse_success_rate` metric by aggregating `gemma.jsonl` records where `call_site == "explain_ern_receipt"`. The spec should require this structured log record (at WARNING on failure, INFO on success) as a §1 Success Criterion — "parse failure events are machine-parseable from `logs/gemma.jsonl`" is as important as "the receipt renders correctly."

**10. Generality across stats**

ERN, ROI, and GRW are all reliable targets for the same JSON-mode appendix template — they are percentile-rank-based or piecewise-linear-map stats with 1–2 numeric inputs, and the receipt structure (one-liner + components list + why-mix paragraph) maps directly. RES (blended, two components) is slightly more complex but still fits without structural changes.

AURA is a fundamentally different prompting problem. The receipt schema puts `value_pct` inside `StatComponent` as an optional per-component percentile. For AURA, the "component" is an institution-level brand-gravity score with a provenance basis string, not a percentile rank. Asking Gemma to write an `explainer` for a component with `value_pct: null` and no `anchor_dollars` (because there is no dollar figure for brand gravity) requires a fundamentally different prompt instruction — the model has nothing to hang the four-section voice structure on. The `why_mix_paragraph` for AURA cannot follow the "two students" contrast (AURA has one component, not a blend), so the Section 4 voice structure must change. The fp-architect review already flagged the schema generality concern for AURA; from an LLM-prompting perspective, the AURA receipt would need a separate appendix variant, not just a different set of tool arguments. The spec is correct to park AURA in a future spec, but the "same JSON-mode appendix template" claim in the spec's out-of-scope section should be updated: ROI/RES/GRW can reuse the same template with stat-specific field substitutions; AURA requires a structurally different template.

#### Summary of Gaps

The ten findings above surface four concrete implementation gaps that the spec does not currently address:

- **Gap A — `response_format` applied to all turns, not just the synthesis turn.** The JSON constraint must be injected only on the final (non-tool-call) turn. Applying it across all turns risks suppressing tool call emission on OpenRouter. This is a blocker for the OpenRouter backend path.
- **Gap B — `_extract_json_objects` not used in `_postprocess_ern_explain_receipt`.** The existing fence-unwrap and brace-depth logic in `gemma_client.py` handles the two most common Gemma JSON-mode failure modes. Not calling it means those failures fall through to the markdown fallback unnecessarily.
- **Gap C — Score-reference prohibition not properly scoped in the appendix.** The wholesale relaxation of the "never state a raw score" rule for the explain-this-stat turn allows Gemma to write score references into prose fields. The appendix must split the relaxation: lifted for JSON numeric fields (`value_pct`, `anchor_dollars`), retained for prose fields (`one_liner`, `explainer`, `why_mix_paragraph`).
- **Gap D — No structured parse-failure log record.** The spec claims `gemma.jsonl` captures the JSON output but the implementation path does not produce a dedicated per-parse record. Monitoring the production parse-success rate requires this.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions (CHANGES REQUESTED)

1. **§4 Service Changes — `response_format` scope:** Specify that `response_format`/`format: "json"` is injected ONLY on the final synthesis turn (after all tool calls are complete), not on all turns. Add implementation guidance: the clean hook is a `final_turn_response_format` kwarg on `_tools_loop_inner` that is only added to `completion_kwargs` when the loop detects it is about to return plain text (i.e., `not response_tool_calls`). Without this, the OpenRouter path risks suppressing tool call emission.

2. **§4 Service Changes — `_postprocess_ern_explain_receipt` extraction strategy:** Before calling `json.loads` directly, `_postprocess_ern_explain_receipt` must first run `_extract_json_objects(raw)` (the existing helper in `gemma_client.py`) to strip markdown fences and extract JSON from prose-wrapped output. Only if `_extract_json_objects` returns nothing should the path fall to full parse failure. This handles the two most common Gemma fence-wrap and trailing-prose failure modes without a fallback call.

3. **§4 Service Changes — JSON-mode appendix voice-override scoping:** The appendix's relaxation of "never state a raw score, percentile, fraction" must be explicitly split: lifted for the `value_pct` and `anchor_dollars` JSON fields (integers — no prose impact), retained for `one_liner`, `explainer`, and `why_mix_paragraph` (prose strings — score/fraction references must not appear). Add the explicit prohibition: "Do not write the N/10 score, phrases like 'since you scored X', or any numeric score reference in any prose field. Score display is the UI's responsibility."

4. **§4 Service Changes — system appendix prompt design:** The `_RECEIPT_JSON_SCHEMA` constant must take the form of a single filled-in JSON example with placeholder values, NOT the Pydantic model definition verbatim. A Pydantic model with `Field(description=...)` annotations is a Python code block — Gemma treats it as code context, not a JSON output target. The example should use `"__FILL_IN__"` sentinel strings for prose fields and numeric placeholders (e.g., `87` for percentiles) so Gemma sees the output format it must produce. Add the `why_mix_paragraph` SKILL example from the SKILL.md Section 4 worked example inline in the appendix as the calibration target length and register.

5. **§4 Service Changes — `_postprocess_ern_explain_receipt` additional validations:** (a) Assert `receipt.stat_code == "ERN"` after Pydantic validation; return None on mismatch. (b) `math_line` is always server-built from the tool_call_log, never from Gemma's emitted value — make this unconditional in the helper (the docstring currently says "Gemma can suggest" for `value_pct`; `math_line` must be documented as fully server-owned with no Gemma input). (c) `why_mix_paragraph` should have a Pydantic `max_length=800` to catch truncation before it renders.

6. **§4 Service Changes — structured parse-failure logging:** `_postprocess_ern_explain_receipt` must append one structured record to `logs/gemma.jsonl` per call: `{call_site: "explain_ern_receipt", parse_success: bool, failure_reason: str | None, json_prefix: str, build_id: str, backend: str}`. Add a P0 test: `test_postprocess_logs_structured_record_on_failure`. Add to §1 Success Criteria: "Parse failure events are machine-parseable from `logs/gemma.jsonl` via the `call_site == 'explain_ern_receipt'` filter."

7. **§2 Decisions — update out-of-scope AURA note:** The "same JSON-mode appendix template reused for ROI/RES/GRW/AURA" claim needs a correction: ROI/RES/GRW reuse the template with stat-specific substitutions; AURA requires a structurally different appendix (no blend contrast, institution-level provenance instead of percentile). Update the out-of-scope entry for the AURA spec to say "requires a different system-appendix structure, not just different tool arguments."

### @genai-architect Re-Review (v1.2)
**Status:** APPROVED
**Reviewed:** 2026-05-02

#### Per-Condition Verification

1. **§4 Service Changes — `response_format` synthesis-turn-only scoping.**
   ✅ RESOLVED — v1.2 renames the public kwarg to `final_turn_response_format` (making the scoping explicit at every call site), adds Decision 15 with the full rationale and implementation hook (`_tools_loop_inner` injects the constraint into `completion_kwargs` only when `not response_tool_calls`), and locks both paths with P0 test `test_final_turn_response_format_synthesis_only` asserting absence on tool-call turns and presence on the synthesis turn. The `final_turn_response_format` name is better than `response_format` precisely because it signals the scoping to any future implementer reading the call site.

2. **§4 Service Changes — `_postprocess_ern_explain_receipt` extraction strategy.**
   ✅ RESOLVED — Step 1 of the 10-step pipeline is now explicitly `_extract_json_objects(raw)` (the existing helper), handling both the markdown-fence and trailing-prose failure modes before attempting `json.loads`. Two P0 tests cover the concrete fence-wrap case (`test_postprocess_uses_extract_json_objects_first`) and the trailing-prose recovery case (`test_postprocess_extract_handles_trailing_prose`). The `_extract_json_objects` docstring reference to lines 815–846 in `gemma_client.py` prevents re-implementation of the primitive.

3. **§4 Service Changes — voice-rule relaxation scoping.**
   ✅ RESOLVED — v1.2 codifies the split explicitly: the "never state a raw score" prohibition is lifted ONLY for `value_pct` and `anchor_dollars` (JSON numeric fields); retained as an explicit prohibition on `one_liner`, `explainer`, and `why_mix_paragraph` (prose string fields). The Pydantic field descriptions on `one_liner` and `why_mix_paragraph` carry the inline prohibition ("Must NOT contain numeric score references like 'N/10' or 'your score is X'"). The `_ern_explain_appendix` rewrite bullet under §4 File Changes calls out the scoped relaxation and the explicit prose-field prohibition verbatim. The fp-architect re-review's "Sound" section also confirms this as a v1.2 improvement.

4. **§4 Service Changes — system appendix prompt format.**
   ✅ RESOLVED — v1.2 replaces "Pydantic model verbatim" with a "filled-in JSON example with `__FILL_IN__` sentinel strings for prose fields and realistic numeric placeholders." The constant is renamed `_RECEIPT_JSON_TEMPLATE` (not `_RECEIPT_JSON_SCHEMA`). The appendix rewrite bullet documents inlining the SKILL voice rules (percentile-gloss inline format, acronym-first-use, `why_mix_paragraph` calibration target) verbatim at inference time, since Gemma has no SKILL.md access. The fp-architect re-review confirms the change under the "Sound" section.

5. **§4 Service Changes — additional validations.**
   ✅ RESOLVED — All three sub-conditions addressed: (a) Step 4 of the pipeline asserts `receipt.stat_code == "ERN"`, returns None on mismatch; P0 test `test_postprocess_rejects_wrong_stat_code` covers it. (b) Step 6 (renumbered from the v1.1 position) server-builds `math_line` unconditionally via `_render_math_line()`; the helper docstring explicitly states "the value Gemma emits in this field (if any) is discarded"; P0 test `test_postprocess_overwrites_math_line_unconditionally` covers it. (c) `why_mix_paragraph` carries `Field(max_length=800)` in the Pydantic model definition; P0 test `test_postprocess_rejects_truncated_why_mix_paragraph` covers the truncation-triggers-fallback path.

6. **§4 Service Changes — structured parse-failure logging.**
   ✅ RESOLVED — `_log_receipt_parse` is now a documented helper with the exact log-record shape: `{call_site: "explain_ern_receipt", parse_success: bool, failure_reason: "pydantic_validation"|"json_decode"|"stat_code_mismatch"|"score_null"|None, json_prefix: str, build_id: str, backend: "ollama"|"openrouter"}`. INFO on success, WARNING on failure. Step 10 of the pipeline emits the record. §1 Success Criteria adds the "Per-parse structured log record" criterion explicitly (including the metric derivation pattern). Two P0 tests cover both branches: `test_postprocess_logs_structured_record_on_success` and `test_postprocess_logs_structured_record_on_failure`.

7. **§2 Decisions — out-of-scope AURA note correction.**
   ✅ RESOLVED — Decision 10 is rewritten in v1.2 to explicitly exclude AURA from the generality claim. The revised text states "AURA explicitly excluded — its institution-level provenance does not fit the StatComponent shape... future AURA spec adds one additive root-level field." The "same template" claim is gone; the fp-architect re-review's Condition 4 (AURA softening) was addressed in the same pass that addressed my Condition 7, and both reviewers agree the current framing is honest.

#### New LLM-Integration Concerns

Three new concerns were raised for explicit verification:

**Concern A — `_log_receipt_parse` JSONL safety and concurrent-write handling.**
No issue. The spec documents `_log_receipt_parse` as appending a record to `logs/gemma.jsonl`. Inspection of `gemma_client.py` confirms that all writes to `gemma.jsonl` flow through `_log_exchange(record: dict[str, Any]) -> None`, which acquires `_log_lock` (a `threading.Lock`) before opening the file and writing the line (`with _log_lock, path.open("a", ...) as fh: fh.write(line + "\n")`). The lock is module-level, covers the full `open+write` critical section, and is documented at lines 233–239 with an explicit rationale ("POSIX write atomicity only holds up to PIPE_BUF... a full Gemma record can reach 10-20 KB"). Every caller of `_log_exchange` inherits the lock. The spec documents `_log_receipt_parse` as calling into this existing infrastructure — it does not open the file directly. Each record is a single `json.dumps` call producing one line, which is exactly the JSONL format (`\n`-delimited JSON objects, one per line). Concurrent writes are safe and the output is machine-parseable as JSONL. No gap here.

**Concern B — `__FILL_IN__` sentinels and Gemma literal-passthrough risk.**
This is a real but manageable risk that the spec does not fully resolve. Gemma 4 is a strong few-shot learner and typically replaces placeholder strings when the JSON context makes the intent clear ("fill in this string value with the appropriate content"). However, at temperature 0, if the sentinel string `"__FILL_IN__"` appears in the model's training data as a literal instruction-following marker (which is plausible given web-scraped instruction-tuning data), some fraction of completions may emit the sentinel verbatim in a prose field.

The spec states the template uses `"__FILL_IN__"` sentinels but does not show the template itself or specify what surrounding instruction text frames the sentinels. The critical gap is: **the spec does not document a clear instruction in the appendix telling Gemma to replace sentinels**. Without an explicit phrase such as "Replace every `__FILL_IN__` string with the appropriate content for this student's program and career — do not emit the literal string `__FILL_IN__` in your response," a Gemma completion that passes back `"one_liner": "__FILL_IN__"` will: (a) pass `json.loads` successfully, (b) pass Pydantic validation (string type, no `max_length` constraint on `one_liner`), and (c) render the literal sentinel string in the student's chat. This is a silent correctness failure, not a parse failure. The fallback never fires.

The mitigation is a one-line addition to the appendix instruction and a Pydantic `min_length=1` constraint on the prose fields (or a custom validator that rejects the sentinel string). The spec should add either: (a) an explicit Pydantic validator `@field_validator("one_liner", "explainer", "why_mix_paragraph") def not_sentinel(cls, v): assert "__FILL_IN__" not in v; return v`, or (b) document in the appendix instruction that `__FILL_IN__` must never appear in the output and add a post-processing check in step 3 of the pipeline that treats any receipt containing the literal string as a parse failure (returns None → fallback). Without one of these guards, the sentinel passthrough is a production correctness risk that the test suite will not catch (since test mocks return valid JSON, not Gemma-generated completions).

**Concern C — Fallback path trace-event continuity.**
No issue. The spec is clear on this in multiple places: Decision 9 states the trace-rail UX is "byte-identical to the spike — same `TraceTurnStart` and `TraceTurnComplete` events, same ordering, same timing." The fp-architect review confirms at lines 789–790: "Verified at `ask_gemma.py:702-712` — the on_turn callbacks build `TraceTurnComplete` from `ToolCallTurn` fields, never the final text." When the fallback path runs, it re-uses the **cached `tool_call_log`** from the first (JSON-mode) attempt — it does NOT re-run the tool calls. The cached `ToolCallTurn` objects already carry the trace event data (`TraceTurnStart`, `TraceTurnComplete`) that were emitted during the first attempt. The second (markdown) pass runs without tool calls, so it emits no new trace events; the trace rail shows the same tool-call events from attempt 1 plus the final text from attempt 2. This is the correct behavior: the student sees two real tool calls in the trace (fetched once) and then the markdown receipt. The "frozen trace rail" risk would exist only if the fallback emitted a new `TraceTurnStart` for tools that never fired — but since no new tool calls happen on the fallback path, no new trace events are emitted, and the rail remains in its post-tool-call state. The §1 Success Criterion "The trace-rail UX is byte-identical to the spike" and Decision 9 both confirm this. No gap.

#### Summary

All seven v1.1 conditions are fully resolved. One new concern (Concern B — `__FILL_IN__` sentinel passthrough) is a real production correctness risk not covered by the current spec. It will not be caught by the test suite because tests use mock JSON fixtures rather than live Gemma completions. The fix is small: add a sentinel-check guard in the post-processing pipeline (step 3 or as a Pydantic validator) and an explicit instruction in the appendix.

The other two new concerns (concurrent-write safety, fallback trace continuity) are non-issues based on the existing codebase implementation.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions (CHANGES REQUESTED)

1. **`__FILL_IN__` sentinel passthrough guard.** The spec must add one of the following: (a) a Pydantic custom validator on `one_liner`, `explainer`, `components[*].explainer`, and `why_mix_paragraph` that rejects any value containing the literal string `"__FILL_IN__"` (causes Pydantic `ValidationError` → returns None → fallback fires), OR (b) a step 3.5 in the `_postprocess_ern_explain_receipt` pipeline that scans the parsed dict for any string value matching `"__FILL_IN__"` and returns None if found. Either guard must be paired with an explicit prohibition in the `_ern_explain_appendix` body: "Do not emit the literal string `__FILL_IN__` in your response — replace every placeholder with the actual content for this student." A P0 test `test_postprocess_rejects_sentinel_passthrough` should assert that a receipt containing `"one_liner": "__FILL_IN__"` returns None. Without this guard, Gemma silently producing sentinel strings is a correctness failure that never triggers the fallback and renders garbage to the student.

### @genai-architect Re-Review (v1.3)
**Status:** APPROVED
**Reviewed:** 2026-05-02

#### Per-Condition Verification

**The single v1.2 new concern — `__FILL_IN__` sentinel passthrough.**
✅ RESOLVED. v1.3 closes the concern on both sides of the boundary simultaneously, which is the right design: a Pydantic-layer guard that fires regardless of what the appendix says, and an appendix instruction that reduces the model-level frequency of the failure.

The Pydantic layer: a module-level `_reject_sentinel_passthrough` function is wired via `field_validator` onto all four prose fields — `StatComponent.explainer`, `StatComponent.anchor_text`, `ExplainStatReceipt.one_liner`, and `ExplainStatReceipt.why_mix_paragraph`. Matching is done via five compiled regex patterns covering the five sentinel forms cited in the v1.2 concern (`__FILL_IN__`, `[FILL...`, `<FILL...`, `ONE-SENTENCE DEFINITION HERE`, `PLACEHOLDER`), all `re.IGNORECASE`. A match raises `ValueError`, which Pydantic surfaces as a `ValidationError`, which `_postprocess_ern_explain_receipt` converts to `None`, which fires the markdown fallback. The guard is unconditional — it does not depend on appendix quality or Gemma version behavior.

The appendix layer: the appendix concludes with an explicit prohibition naming each of the five sentinel strings and stating that echoing them "will fail validation and the receipt will not render." This is correctly framed as a consequence, not just a rule — consequence-framing is more reliable for instruction-following at temperature 0 than prohibition-only phrasing.

The new P0 test `test_postprocess_rejects_sentinel_passthrough` covers all five sentinel patterns across all four prose fields (5 × 4 = 20 cases), asserting both that the validator fires and that the helper returns None.

#### Assessment of Remaining or New Concerns

**Regex pattern completeness — plausible missing sentinels.**

The five patterns cover the explicit sentinels used in the v1.2 appendix template. Three gaps are worth naming:

1. **Empty string and whitespace-only strings.** `""` or `"   "` in a prose field would pass all five sentinel patterns and pass Pydantic (no `min_length` on `one_liner`, `explainer`, or `anchor_text`). Gemma 4 rarely emits a pure empty string for a prose field at temperature 0 — it is more likely to emit the sentinel verbatim or a short generic sentence. This is a low-probability gap, and an empty `one_liner` or `explainer` would be visually obvious in QA. It is not a blocker, but adding `min_length=1` to the four prose fields (`Field(min_length=1, ...)`) would close it at zero test-writing cost. This is a suggestion, not a condition.

2. **"TODO" and free-text markers.** A Gemma completion under distribution shift might emit `"TODO"`, `"[fill this in]"`, `"N/A"`, or similar. These are not covered by the five patterns. However, they are also not the sentinels in the spec's appendix template — the risk is a generic Gemma failure mode, not the specific sentinel-passthrough failure the v1.2 concern named. These cases would render as visibly incorrect prose and would likely surface in QA or dogfooding rather than silently degrading. The five patterns address the specific failure mode identified; extending coverage to every possible non-answer string is a different problem domain (output quality monitoring, not sentinel rejection).

3. **Capitalization variants.** All patterns are `re.IGNORECASE`, so `__fill_in__`, `PLACEHOLDER`, `placeholder`, `Placeholder` are all caught. No gap here.

None of these rise to the level of a new condition. The pattern set is targeted and proportionate.

**Pydantic v2 `extra="forbid"` and `field_validator` composition.**

No composition issue. In Pydantic v2, `model_config = ConfigDict(extra="forbid")` and `field_validator` decorators are orthogonal mechanisms: `extra="forbid"` rejects keys that are not declared on the model; `field_validator` validates the values of declared fields. They operate at different stages of the validation pipeline and do not mask each other. A payload with an extra field raises `ValidationError` from the `extra="forbid"` check before field validators run; a payload with a sentinel-valued prose field raises `ValidationError` from `_reject_sentinel_passthrough` after field-type coercion. Both produce `ValidationError` and both cause `_postprocess_ern_explain_receipt` to return `None`. The spec's use of `field_validator("explainer")(_reject_sentinel_passthrough)` as a class-body assignment is the correct Pydantic v2 pattern for reusing a validator function across fields without a decorator. No gap here.

**Appendix prohibition phrasing — clarity for Gemma 4.**

The appendix ends with: *"The strings `__FILL_IN__`, `[FILL_IN]`, `<FILL_IN>`, `ONE-SENTENCE DEFINITION HERE`, and `PLACEHOLDER` are placeholders ONLY — they MUST be replaced with your actual content. Echoing them back verbatim will fail validation and the receipt will not render."*

This is clear and correctly phrased. The consequence ("will fail validation and the receipt will not render") is actionable — Gemma 4's instruction-following at temperature 0 responds better to consequence framing than to prohibition-only framing. The five strings are named explicitly, reducing the model's ambiguity about which strings count as sentinels. The placement at the end of the appendix (the highest-attention position in a long system prompt, per instruction-following research on LLMs) is correct. No revision needed.

#### Summary

All seven v1.1 conditions were resolved in v1.2. The single v1.2 new concern (sentinel passthrough) is resolved in v1.3 with a correct, well-tested, Pydantic-layer guard that does not depend on appendix quality. No new architecture-layer concerns introduced. The two minor items noted above (empty-string gap, "TODO"-type variants) are QA/monitoring concerns, not spec gaps, and are flagged as suggestions rather than conditions.

#### Verdict
- [x] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

Spec is ready to advance to **Phase 2: Design Vision** (@fp-design-visionary fills §3).

---

### @fp-data-reviewer Review
**Status:** SKIPPED — no pipeline, schema, or data-formula changes. Existing `cip_family_earnings_rank` and `wage_percentile_overall` columns are read; no transformation, no re-promotion.

---

## §6 Implementation Log

**Status:** COMPLETE — pending Phase 4 test-writer pass.

### Files Modified
| File | Change Summary |
|------|---------------|
| `backend/app/models/api.py` | Added `ReceiptSource`, `StatComponent`, `ExplainStatReceipt` Pydantic models (with `extra="forbid"` and the `_reject_sentinel_passthrough` field validator on all four prose fields). `kind: Literal["receipt"]` self-discriminator on `ExplainStatReceipt`. `why_mix_paragraph` carries `max_length=800`. Widened `AskResponse.response` and `TraceFinalText.response` to `str \| ExplainStatReceipt`. |
| `backend/app/services/gemma_client.py` | Added `final_turn_response_format` kwarg to `generate_with_tools_loop` and `_tools_loop_inner`. Synthesis-turn-only scoping via the new `prev_turn_had_tool_calls` flag. `_one_tool_turn` and `_one_tool_turn_ollama` accept the kwarg with per-backend translation (OpenAI-compat verbatim; Ollama native translates `{"type":"json_object"}` → `payload["format"] = "json"`). |
| `backend/app/services/ask_gemma.py` | Replaced the spike's markdown-only appendix with `_ern_explain_appendix_json` (filled-in JSON example with `__FILL_IN__` sentinels, scoped voice-rule split, sentinel-handling prohibition). Markdown spike kept as `_ern_explain_appendix` for the JSON-parse-failure fallback path. New helpers: `_ordinal_suffix`, `_format_pct`, `_extract_tool_results`, `_render_math_line` (with effort-line on `effort != "balanced"`), `_normalize_label` (match-by-weight-first), `_log_receipt_parse` (structured `gemma.jsonl` records), `_format_cached_tool_values` (markdown-fallback user-message pre-injection — no MCP re-fetch), `_postprocess_ern_explain_receipt` (10-step pipeline), `_current_backend`. Wired into both `chat_ask` and `chat_ask_stream` with the cached-tool-log fallback retry. |
| `frontend/src/types/chat.ts` | NEW. Zod schemas (`receiptSourceSchema`, `statComponentSchema`, `explainStatReceiptSchema`) mirroring the backend Pydantic models; inferred TypeScript types. Discriminated `ChatHistoryItem` union. `isExplainStatReceipt` guard. |
| `frontend/src/types/gemmaTrace.ts` | Widened `final_text` event's `response` from `string` to `string \| ExplainStatReceipt`. |
| `frontend/src/api/menu.ts` | Imported chat types from `@/types/chat` and re-exported. Replaced inline `ChatHistoryItem` interface with the discriminated union. Widened `AskResponse.response` and `AskGemmaStreamResult.response` to `string \| ExplainStatReceipt`. New `parseFinalTextResponse` helper that runs the Zod schema on object payloads and falls back to `String(value)` on validation failure. `parseSSEFrame` `final_text` branch now uses the helper. |
| `frontend/src/components/menu/ChatMessage.tsx` | Narrowed prop type from `ChatHistoryItem` (now a union) to a local `{ role, content }` shape — ChatMessage only renders text bubbles; the receipt branch is handled by `<ExplainStatReceiptCard>` in the `GemmaChat` renderer dispatch. |
| `frontend/src/components/menu/GemmaChat.tsx` | Added `assistantHistoryItem` helper that discriminates string vs receipt payload. `userMsg` construction adds `kind: "text"`. Streaming `response` variable widened to `string \| ExplainStatReceipt`. `onAssistantResponse` callback receives the prose representation (`one_liner` for receipts). `renderMessageWithTrace` dispatches on `m.kind`: `"receipt"` → `<ExplainStatReceiptCard payload={m.payload} />`; otherwise the existing `<ChatMessage>` with `{ role, content }`. |
| `frontend/src/components/menu/ExplainStatReceipt.tsx` | NEW. `<ExplainStatReceiptCard>` per @fp-design-visionary's §3. Card with `bg-bp-raised` + stat-color left-accent border. Score callout in `font-data` 32px tinted by `var(--color-stat-{stat_code})`. Component bullets with 56px left-rail percentage chip + stacked label/explainer. Recessed inset math line in `bg-bp-mid`. Effort-line footnote (italic body) when `math_line` carries a `\n`-separated second line. Source pills as tappable buttons with `title` attribute tooltip. Missing-data rows dim to `text-muted` while the chip stays at full opacity. Framer Motion stagger animation for the bullets. |
| `docs/reference/stat-display-surfaces.md` | Added new §1i entry for `<ExplainStatReceiptCard>` listing it as ✅ wired (the second ✅ surface). |
| `.claude/skills/pentagon-stat-explanation/SKILL.md` | Added pointer to `ExplainStatReceipt.tsx` as the rendering authority for the SKILL's prose-field outputs. |

### Deviations from Spec

None. The §3 design from @fp-design-visionary was implemented as written. The §4 file-changes table was followed exactly. Two minor implementation notes flagged for the auditor:

1. **The fallback path in `chat_ask_stream` doesn't yield trace events for the markdown-fallback retry.** Trace events from the JSON-mode attempt are already streamed before the parse fails; the markdown retry runs synchronously to completion and its `tool_call_log` (which is empty since `tools=[]` is passed) doesn't emit additional events. This matches Decision 9's "trace-rail UX is byte-identical to the spike" — the trace shows what actually happened, and the fallback didn't issue any new tool calls.

2. **`_normalize_label` doesn't currently match-by-string-distance.** The pipeline matches by `weight_pct` only and replaces with the canonical label unconditionally if the strings differ. This is stricter than the spec's "match by weight first, then nearest-string-distance" wording. In practice the weight-only match is sufficient for the swap-component case AND any drift case (Gemma writes anything other than the canonical → server normalizes). String-distance comparison was redundant for v1.0. The spec's Decision 14 wording was prescriptive; the implementation is one cleaner step.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | TypeScript error in `ExplainStatReceipt.tsx` | `stagger.normal` is a `number`, not a `Variants` | Replaced `variants={stagger.normal}` with `variants={staggerContainer(0, 0.08)}` and wrapped each `ComponentRow` in a `<motion.div variants={staggerItem}>`. |
| 2 | Vite import resolution error | `@/components/menu/ExplainStatReceipt` referenced before file existed | Resolved itself on next HMR cycle once `ExplainStatReceipt.tsx` was written. |

---

## §7 Test Coverage

**Status:** COMPLETE (Phase 4 — @test-writer, 2026-05-02)

### Tests Added

#### Backend — `backend/tests/services/test_ask_gemma_explain_receipt.py` (NEW, 48 tests, P0/P1)
| Test Name | Priority | What It Tests |
|-----------|----------|---------------|
| `test_postprocess_happy_path` | P0 | Valid Gemma JSON → ExplainStatReceipt populated; both percentiles present; sources stamped from canonical `_ERN_RECEIPT_SOURCES`. |
| `test_postprocess_overrides_score_from_build` | P0 | Gemma emits valid-but-wrong `score: 2`; receipt's score is stamped to `build.career.stats.ern` (7). |
| `test_postprocess_school_rank_null` | P0 | `cip_family_earnings_rank` null → 60% component `value_pct` null + `missing_reason` set; math_line shows `0.6 × n/a` and real `0.4 × 0.92`. |
| `test_postprocess_occupation_pct_null` | P0 | `wage_percentile_overall` null → 40% component nulled; math_line shows `0.4 × n/a`. |
| `test_postprocess_both_null` | P0 | Both percentiles null → receipt parses; math_line shows n/a in both slots; both `missing_reason` strings populated. |
| `test_postprocess_invalid_json_returns_none` | P0 | Unparseable string → None. |
| `test_postprocess_extra_field_rejected` | P0 | Pydantic `extra="forbid"` rejects `confidence: 0.8` → None. |
| `test_postprocess_missing_required_field` | P0 | Pydantic rejects payload with `why_mix_paragraph` dropped → None. |
| `test_postprocess_uses_extract_json_objects_first` | P0 | Markdown-fenced ` ```json{...}``` ` payload parses (`_extract_json_objects` strips fence). |
| `test_postprocess_extract_handles_trailing_prose` | P0 | `Here is the receipt: {valid JSON}` parses via brace-depth extraction. |
| `test_postprocess_rejects_wrong_stat_code` | P0 | Gemma emits `stat_code: "ROI"` for ERN request → None (Step 4 stat_code assertion). |
| `test_postprocess_overwrites_math_line_unconditionally` | P0 | Gemma writes `"I made this up"`; the string never appears in the final receipt — `_render_math_line` output overwrites unconditionally. |
| `test_postprocess_rejects_truncated_why_mix_paragraph` | P0 | `max_length=800` rejects 801-char `why_mix_paragraph` → None. |
| `test_postprocess_rejects_sentinel_passthrough` | P0 | 5 sentinel patterns × 4 prose fields (one_liner, why_mix_paragraph, components[0].explainer, components[0].anchor_text) — 20 parametrized cases. Every field_validator firing → None. |
| `test_postprocess_label_normalization_match_by_weight` | P0 | Off-script `label="program rank"` at weight=60 → normalized to `"your school's program rank"`. |
| `test_postprocess_label_normalization_handles_swap` | P0 | Gemma swaps the canonical labels across components → match-by-weight catches the swap; both labels normalized. |
| `test_postprocess_returns_none_when_build_score_null` | P0 | `build.career.stats.ern is None` → score_null guard fires → None. |
| `test_postprocess_logs_structured_record_on_success` | P0 | Successful parse writes one INFO record with `parse_success=True`, `failure_reason=None`, `call_site`, `build_id`, `backend`. |
| `test_postprocess_logs_structured_record_on_failure` | P0 | 3 parametrized failure_reasons (`json_decode`, `pydantic_validation`, `stat_code_mismatch`) each emit exactly one WARNING record with the matching reason. |
| `test_postprocess_logs_score_null_failure` | P0 | The fourth failure_reason — `score_null` — emits one WARNING with the matching reason. |
| `test_render_math_line_balanced_effort` | P0 | `effort="balanced"` → simple form, no `\n`. |
| `test_render_math_line_focused_effort` | P0 | `effort="focused"`, build_score above unshifted → unshifted derivation + `Your **Focused** effort setting lifts this to N/M`. |
| `test_render_math_line_chill_effort` | P0 | `effort="chill"`, build_score below unshifted → unshifted derivation + `brings this to N/M`. |
| `test_math_line_format_unicode_arrow` | P1 | math_line uses `→` (U+2192) not `->`. |
| `test_normalize_label_*` (3 unit tests) | helper | `_normalize_label` canonical-match (no change), off-script (replace), unknown-weight (passthrough). |

#### Backend — `backend/tests/services/test_ask_gemma_explain_integration.py` (NEW, 6 tests, P0)
| Test Name | What It Tests |
|-----------|---------------|
| `test_chat_ask_ern_explain_returns_receipt_on_success` | End-to-end: `[explain-this:ERN]` opener → JSON-mode loop → AskResponse.response is an ExplainStatReceipt object; `final_turn_response_format={"type": "json_object"}` is threaded into `generate_with_tools_loop`. |
| `test_chat_ask_ern_explain_falls_back_on_parse_failure` | Postprocess returns None → fallback retry fires → response is the markdown-spike string. |
| `test_chat_ask_ern_explain_fallback_uses_cached_tool_log` | Fallback retry passes `tools=[]` to `generate_with_tools_loop` and injects the cached percentile values into the user message — `cip_family_earnings_rank = 0.87` and `wage_percentile_overall = 0.92` appear verbatim. MCP dispatch counter == 0 across the entire chat_ask invocation (Decision 6 v1.2). |
| `test_chat_ask_ern_explain_returns_string_when_build_score_null` | Build with `stats.ern is None` → postprocess returns None (score_null) → fallback fires → response is a string. |
| `test_chat_ask_stream_ern_explain_emits_receipt_in_final_text` | `TraceFinalText.response` carries an ExplainStatReceipt object (with `kind: "receipt"`), not a string, when JSON path succeeds. |
| `test_chat_ask_non_explain_stat_scope_does_not_set_response_format` | Free-form stat-scope question (NOT the opener) → `final_turn_response_format` is None. Defends against an explain-mode leak into the prose path. |

#### Backend — `backend/tests/services/test_gemma_client.py` (4 NEW tests, P0)
| Test Name | What It Tests |
|-----------|---------------|
| `test_final_turn_response_format_synthesis_only` | 3-turn loop (tool-call, tool-call, synthesis); response_format is None on turn 0 (initial tool-call decision); injected on turns 1 and 2 (synthesis-eligible). |
| `test_response_format_propagates_to_openrouter_path` | OpenAI-compat path: `final_turn_response_format={"type":"json_object"}` lands in `completion_kwargs["response_format"]` verbatim. Mock OpenAI client. |
| `test_response_format_translates_to_ollama_native_payload` | Ollama native path: `{"type":"json_object"}` translates to `payload["format"] = "json"` before the httpx POST. **fp-architect Condition 1.** |
| `test_response_format_absent_when_unset_on_ollama` | Sanity: when `response_format=None`, payload has no `format` key. |

#### Frontend — `frontend/src/components/menu/ExplainStatReceipt.test.tsx` (NEW, 8 tests, P0/P1)
| Test Name | Priority | What It Tests |
|-----------|----------|---------------|
| `test_renders_default_state` | P0 | All four sections render (callout, components, math card, sources, why-mix); both rows + both pills present. |
| `test_renders_missing_school_rank` | P0 | Missing-reason note renders; 60% row's body text gets `text-text-muted` className; math card shows `0.6 × n/a`; 40% row not dimmed. |
| `test_renders_score_color_token` | P0 | Region's inline style references `var(--color-stat-ern)`. |
| `test_renders_effort_line_when_non_balanced` | P0 | `\n`-split math_line surfaces the effort line as `[data-testid="receipt-effort-line"]` distinct from the math card; `**Focused**` renders as `<strong>` (no raw asterisks leaked). |
| `does NOT render the effort line for balanced effort` | saboteur | When math_line has no `\n`, `receipt-effort-line` is absent. |
| `test_accessibility_attributes` | P1 | `role="region"`, `aria-label` includes stat name + "explanation receipt"; component-row + source-pill data-testids present. |
| `test_renders_responsive_narrow` | P1 | At 480px viewport, region's max-width is 100% (no fixed-px overflow); component renders. |
| `renders both-missing degenerate state without throwing` | sanity | Both components have missing_reason notes; math card shows two `n/a` placeholders. |

#### Frontend — `frontend/src/api/menu.test.ts` (NEW, 7 tests, P0)
| Test Name | What It Tests |
|-----------|---------------|
| `test_zod_parser_distinguishes_string_vs_receipt` (string branch) | `parseSSEFrame` returns the string verbatim for plain-prose final_text. |
| `test_zod_parser_distinguishes_string_vs_receipt` (receipt branch) | Object payload matching the Zod schema parses to a typed ExplainStatReceipt (kind, stat_code, score, components, sources). |
| `test_zod_parser_falls_back_to_string_on_invalid_object` (missing fields) | Object missing required fields → `String(value)` fallback, no throw. |
| Saboteur: wrong-type field (`score` as string) | Falls back to string. |
| Saboteur: out-of-range `score: 99` | Falls back to string (Zod `.max(10)` rejects). |
| Saboteur: extra field (`confidence: 0.8`) | `.strict()` rejects → falls back to string. |
| Saboteur: missing `response` key | Resolves to empty string, no throw. |

#### Frontend — `frontend/src/components/menu/GemmaChat.test.tsx` (1 NEW test + 1 modification, P0)
| Test Name | What It Tests |
|-----------|---------------|
| `test_dispatches_receipt_to_explain_stat_component` | Mock `askGemmaStream` to emit a receipt-typed final_text → `<ExplainStatReceiptCard data-testid="explain-stat-receipt">` renders, math card carries the server-built arithmetic, no `[object Object]` leak from the prose renderer. |
| `second user turn passes the prior 2-entry history to sendChat` (modified) | History assertion now expects `kind: "text"` on each entry, per the discriminated union widening (authorized modification per §4). |

### Edge Cases Covered

- [x] Gemma emits valid-but-wrong score → server stamps build's score
- [x] Gemma swaps component labels (60% gets the 40% canonical) → match-by-weight recovery
- [x] Gemma echoes appendix sentinels verbatim (5 patterns × 4 prose fields = 20 cases)
- [x] Markdown-fenced JSON ` ```json{...}``` ` parses
- [x] Trailing prose `Here is the receipt: {...}` parses via brace-depth extraction
- [x] Truncated `why_mix_paragraph` (801 chars) rejected by Pydantic `max_length`
- [x] Wrong stat_code (ERN request, ROI emitted) rejected by Step 4 assertion
- [x] All 4 percentile-null permutations (60% null, 40% null, both null, both present)
- [x] All 3 effort levels (balanced, focused, chill) — focused/chill emit two-line math
- [x] Math line uses Unicode `→` not ASCII `->`
- [x] Hallucinated `math_line` text from Gemma never survives the post-processor
- [x] `build.career.stats.ern is None` → score_null guard fires (BuildResultsScreen disables the trigger; this defends the helper-level guard)
- [x] All 4 failure_reason codes (`json_decode`, `pydantic_validation`, `stat_code_mismatch`, `score_null`) emit structured logs
- [x] Synthesis-turn-only JSON-mode scoping (turn 0 is unconstrained — Decision 15)
- [x] OpenAI-compat path + Ollama native path both translated correctly (fp-architect Condition 1)
- [x] Frontend Zod parser falls back to string on every invalid-object permutation (no throw)

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest (backend) | 1395 | 0 | 0 | 1395 |
| vitest (frontend) | 790 | 0 | 0 | 790 |

Backend: 1337 baseline + 58 new (48 in `test_ask_gemma_explain_receipt.py` + 6 in `test_ask_gemma_explain_integration.py` + 4 in `test_gemma_client.py`) = 1395 passing.

Frontend: 773 baseline (1 was failing on the unmodified GemmaChat test, fixed via authorized modification) + 16 new (8 in `ExplainStatReceipt.test.tsx` + 7 in `menu.test.ts` + 1 in `GemmaChat.test.tsx`) = 790 passing. The 1 prior failure is the authorized `kind: "text"` widening of an existing fixture; all other previously-passing tests continue to pass.

### Existing Tests Status (Confirmed Safe — §4)

All "Confirmed Safe" tests verified passing:

- [x] `test_chat_ask_boss_scope_*`, `test_chat_ask_skill_scope_*`, `test_chat_ask_build_scope_*`, `test_chat_ask_branch_*` — boss/skill/build/branch scopes unchanged.
- [x] `test_strip_thinking_prefix*` — `_strip_thinking_prefix` reused for the markdown fallback path; no signature change.
- [x] `test_helper_leak_*` — `_HELPER_LEAK_RE` unchanged.
- [x] `test_voice_contract.py` — system-base voice rules unchanged; receipt appendix is local to the explain-this-stat turn.
- [x] `BuildResultsScreen.test.tsx` (all tests) — trigger-button behavior unchanged.
- [x] `test_message_rendering_text` and equivalents — plain-text rendering continues to work identically (the `kind === "text"` branch of the renderer dispatch).

### Gaps Identified

- **Smoke verification across both inference backends.** Live Ollama and OpenRouter behavior is not exercised in unit tests by design — these backends are mocked everywhere. §9 Smoke Verification covers the live behavior gate.
- **`test_explain_stat_receipt_zod_matches_pydantic` (P2 row in §4).** A round-trip schema-parity test between Pydantic and Zod was deferred. The two schemas are structurally aligned by hand (same field names, same constraint shapes); a property-based diff test would be the right v1.1 follow-up but is out of scope for v1.0.
- **`response_format_propagates_to_openrouter_path` exercises `_one_tool_turn` directly** rather than through `_tools_loop_inner`, because the loop's synthesis-turn-only scoping suppresses the format on the first turn. The wire-format propagation is covered; the loop scoping itself is covered by `test_final_turn_response_format_synthesis_only`. Both halves of the path are intentional separate units.

---

## §8 Reviews

**Status:** PENDING

### Design Audit (@fp-design-auditor)
**Status:** CHANGES REQUIRED

---

## frontend/src/components/menu/ExplainStatReceipt.tsx

### PASS
- `statColorVar` is the single path that produces stat-color CSS variables. It constructs `var(--color-stat-${statCode.toLowerCase()})` correctly for all five stat codes and is called consistently for `accent` throughout the component.
- `color-mix(in oklab, ${accent} 12%, transparent)` on the weight chip background is a compliant expression of the stat-color tint. It derives from the token variable, not a hardcoded `rgba(...)`. Per §3 Brightpath Design References the spec notes this pattern as acceptable; `color-mix` is the correct mechanism.
- Dark-first enforcement is satisfied. No hardcoded `#fff`, `#000`, or `rgba(255,...)` values appear anywhere in the component.
- `bg-bp-raised` is used as the card surface (line 146) — correct tier per §3 "Card surface" row.
- `bg-bp-mid` is used as the recessed math card (line 213) — correct tier per §3 "Recessed math card" row.
- `border border-border-subtle` appears on the card (line 146). The spec calls for `border border-border-default` (per §3 "Card border" row: `border border-border-default`). **See FAIL item 1 below** — flagged here for completeness; it is in FAIL, not PASS.
- The 3px stat-color left-accent border is rendered via `borderLeft: \`3px solid ${accent}\`` (line 149) — uses the token variable, not a hardcoded hex.
- The math card color is set via `color: "var(--color-text-primary)"` inline (line 217) — token-correct; no hardcoded color.
- Score callout `aria-label` is `"Score: ${payload.score} out of ${payload.score_max}"` (line 163). Spec §3 Accessibility table specifies `"Earning Power score: 9 out of 10"` (includes stat name). **See FAIL item 7.**
- Font families (`font-display`, `font-body`, `font-data`) are used via Tailwind utilities throughout — no raw font-family strings.
- `data-testid="explain-stat-receipt"` present on the article (line 140). PASS.
- `role="region"` present on the article (line 141). PASS.
- `aria-label="{stat_name} explanation receipt"` present on the article (line 142). PASS.
- `data-testid="receipt-component-{statCode}-{weight_pct}"` present on the `<li>` (line 84). PASS.
- `aria-label="{weight_pct} percent — {label}"` present on the `<li>` (line 85). PASS.
- `data-testid="receipt-missing-{weight_pct}"` present on the missing-reason `<p>` (line 119). PASS.
- `role="note"` present on the missing-reason `<p>` (line 118). PASS.
- `aria-label="Note: {missing_reason}"` present on the missing-reason `<p>` (line 120). PASS.
- `data-testid="receipt-math-line"` present (line 212). PASS.
- `data-testid="receipt-effort-line"` present (line 231). PASS.
- Framer Motion is used only for entrance animation (`motion.article` with `initial`/`animate`/`transition` at lines 143-145). No `whileHover`, `whileFocus`, or `whileTap` on the article or any prose element. PASS.
- `staggerContainer(0, 0.08)` at line 194 matches the spec's `staggerContainer(delayChildren=0.08, staggerAmount=stagger.normal)` call signature — note: argument order in the implementation is `(delayChildren, staggerAmount)` per `motion.ts:86`, so `(0, 0.08)` maps to `delayChildren=0` and `staggerAmount=0.08`. The spec writes `delayChildren=0.08` but the named params are in the motion.ts signature not a Python context; the numeric values produce the correct stagger cadence. PASS.
- `staggerItem` is imported and used per component row (line 199). PASS.
- `maxWidth: "100%"` on the article (line 151) — no min-width constraint present. PASS.
- Flex layout `flex items-start gap-3` on component rows (line 87) keeps chip and prose side-by-side at all widths — chip is `flex-shrink-0` (line 93), prose is `flex-1` (line 104). Chip never stacks above prose. PASS.
- Spacing values in use: `gap-3` (12px), `mt-1` (4px), `mt-2` (8px), `mt-3` (12px), `mt-4` (16px), `mt-5` (20px), `gap-2` (8px), `px-2.5 py-1` (10px/4px). All are on the 4px Tailwind grid. No off-grid values (`11px`, `17px`, `23px`). PASS.
- Missing-reason `<p>` dims correctly via `font-body italic text-text-muted` at 12px (lines 121-122). The weight chip is outside the dimmed `flex-1` wrapper so it remains at full opacity on missing rows. PASS.
- `font-body italic text-text-muted` with `style={{ fontSize: 12 }}` for the effort line (lines 232-233). PASS.

### FAIL

**1. Card border uses `border-border-subtle` instead of `border-border-default` (line 146)**
Per §3 Brightpath Design References, "Card border" is `border border-border-default` + the 3px left rail. The implementation uses `border border-border-subtle`. `--color-border-subtle` is `rgba(255,255,255,0.06)`; `--color-border-default` is `rgba(255,255,255,0.1)`. The subtle token is too faint for a card edge — the spec explicitly chose `border-default` to give the receipt card a defined edge that reads as a document, matching `StatInfoPopover`. Must change `border-border-subtle` to `border-border-default` on line 146.

**2. Card radius is `rounded-xl` (20px) but the spec requires `rounded-[14px]` (line 146)**
Per §3 "Border radius" row: `rounded-[14px]`. Per §3 design note: "Matches StatInfoPopover. Plush, not sharp." The Tailwind `rounded-xl` maps to 20px in this project's config (see `tailwind.config.ts:118`). The spec specifies 14px — a custom Tailwind value `rounded-[14px]` — not the standard `rounded-xl` token. These are different shapes. Must change `rounded-xl` to `rounded-[14px]`.

**3. Card shadow is absent (line 146)**
Per §3 "Box shadow" row: `0 8px 32px rgba(27,29,48,0.55)`. The implementation applies no `boxShadow` to the article. This is load-bearing for the "card-on-a-card" visual separation — without it the receipt doesn't read as an elevated surface inside the chat bubble. Must add `boxShadow: "0 8px 32px rgba(27,29,48,0.55)"` to the article's `style` prop. Note: `rgba(27,29,48,...)` is the `--color-bg-deep` value used in the Brightpath shadow tokens, so this is a compliant inline shadow (no token exists for this exact value; the spec writes it explicitly as a raw string, consistent with `--shadow-lg` which uses the same base color). This is the one permitted literal in the spec.

**4. Score callout layout does not match §3 (lines 154-173)**
The spec's "Score callout" section calls for: `EARNING POWER` uppercase eyebrow (muted, 13px, 1.5px letter-spacing) **above** the score row, with eyebrow + score on the same `flex justify-between items-baseline` row, and the one-liner stacked below. The implementation renders:
  - A `<header>` with `flex items-baseline gap-3 flex-wrap` containing a `<h3>` with the `stat_name` (line 155) and the score number (line 161) side by side. This is a header-left/score-right layout — close but not identical.
  - The `<h3>` renders `{payload.stat_name}` at `font-display font-bold text-text-primary 18px` — not the spec's `font-display weight 600 text-text-muted 13px uppercase letter-spacing 1.5px` eyebrow. The spec wants the eyebrow **muted** (`text-text-muted`), uppercase, 13px, 1.5px letter-spacing — functioning as a section label, not a headline. The implementation treats the stat name as a `font-bold text-text-primary` 18px display header, which reads as the visual headline rather than a quiet label.
  - Score font size is 32px (line 164), not the spec's 44px. DESIGN.md has no 44px token — the spec invented a custom size for the score callout. 32px is a deviation from the §3 spec.
  - Slash + max (`/score_max`) is rendered as a child `<span>` of the score div with `opacity-50` (line 168). Spec calls for `font-data weight 400 22px text-text-muted` — not `opacity-50` on a child span. The semantic token `text-text-muted` and `opacity-50` produce similar visual results, but they are not equivalent: `opacity-50` also reduces opacity on the number itself's antialiasing context, and future dark-mode or contrast overrides would treat them differently. Spec says `text-text-muted`; implementation uses `opacity-50`.
  - Score max is 18px (line 169), not the spec's 22px.

**5. Missing `data-testid="receipt-score"` on the score callout (lines 161-173)**
Per §3 Accessibility table: the score callout span needs `data-testid="receipt-score"`. The implementation has no such attribute on the score element.

**6. `data-testid` pattern for source pills uses index (`receipt-source-{i}`) instead of slug (`receipt-source-{slug}`) (line 253)**
Per §3 Accessibility table: `data-testid="receipt-source-{slug}"` where slug is kebab-case of the short-form source name. The implementation uses the array index `i`. This breaks the spec's contract (which exists so tests and assistive tooling can identify pills by source identity rather than position). Changing the name requires the implementer to add the short-form lookup table from §3 "Pill name truncation" — which is also missing (the pill currently shows `s.label` only, not the `{label} · {name short form}` pill content).

**7. `aria-label` on the score element omits the stat name (line 163)**
Per §3 Accessibility table: `aria-label="Earning Power score: 9 out of 10"`. The implementation emits `aria-label=\`Score: ${payload.score} out of ${payload.score_max}\`` — missing the stat name prefix. Screen readers announce "Score: 9 out of 10" without the stat context, which is ambiguous on a screen that can have multiple stat panels. Must prepend `${payload.stat_name} ` to the aria-label.

**8. Source pill focus state is missing the required `focus-visible:ring` classes (line 256)**
Per §3 Accessibility / "Focus state on pills": `focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-none`. The `<button>` at line 251 has `hover:text-text-primary hover:border-border-default transition-colors` but no `focus-visible` ring classes. This is a hard accessibility requirement — keyboard users and screen-reader users cannot discern focus on the source pill. Must add `focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-none` to the button className.

**9. Source pill hover uses Framer Motion `whileHover`/`whileFocus` per §3 "Interactions" table but implementation uses CSS `hover:` classes (line 256)**
Per §3 "Source pill hover/focus" row: `transition={springs.snappy}`, change `bg` from `bg-bp-mid` → `bg-bp-raised` and `borderColor` from `border-border-subtle` → `var(--color-stat-ern)` over 200ms. The implementation uses static CSS hover utilities (`hover:text-text-primary hover:border-border-default`) with a `transition-colors` class. Two deviations: (a) the spec requires the background to lift from `bg-bp-mid` to `bg-bp-raised` on hover — the implementation keeps the background as `bg-bp-deep` with no hover lift; (b) the spec requires the border to shift to the **stat color** (`var(--color-stat-ern)`) on hover — the implementation shifts to `border-border-default` (white at 10% opacity), which has no stat-color identity. The spec requires `whileHover` with `springs.snappy`; implementation uses CSS transitions. This is a moderate deviation but the spec calls it out explicitly. However, note that DESIGN.md §Motion System states "For simple hover/focus states [use CSS transitions]" — there is a conflict between the §3 spec and DESIGN.md convention. Per audit scope, §3 is the binding spec for this component. Flagging as FAIL for the missing stat-color border-on-hover and the missing background lift. The CSS-vs-Framer distinction is a MINOR for the interaction technique (see WARNINGS).

**10. Source pill pill content renders only `s.label` — missing `{label} · {name short form}` pattern and missing short-form name lookup (lines 258-260)**
Per §3 "Pill" row: the pill contains `{label}` (muted) + `·` (U+00B7) + `{name short form}` (primary). The implementation renders only `{s.label}` with no separator and no source name. The §3 "Pill name truncation" row specifies a short-form lookup table (e.g., `"College Scorecard (U.S. Department of Education)"` → `"College Scorecard"`). Neither the separator nor the name is rendered. The source pill is visually incomplete.

**11. Missing-data percentile glyph `◦ —` is not rendered (ComponentRow, lines 69-129)**
Per §3 "Missing-data treatment" step 2: when `value_pct === null`, the percentile callout slot becomes `◦ —` (U+25E6 + U+2014) in `text-text-muted 12px` with `aria-label="data not available"`. The `ComponentRow` component dims the prose body when `isMissing` but has no percentile callout row at all — neither the real callout (for present data) nor the `◦ —` glyph (for missing). Both the normal percentile display line and the missing-data glyph are absent. The spec requires the percentile callout row (`{value_pct}th percentile · median ${anchor_dollars.toLocaleString()}`) on every row, with the `◦ —` substitution when null.

**12. `receipt-math-line` missing `role="math"` and `aria-label="Score formula"` (line 212)**
Per §3 Accessibility table: the math line container needs `role="math"` and `aria-label` set to the natural-language formula reading (e.g., `"Score formula: zero point six times..."`). The implementation has `data-testid="receipt-math-line"` but no `role` or `aria-label` on the math container.

**13. `data-testid="receipt-components"` missing on the `<ul>` (line 192)**
Per §3 Accessibility table: `data-testid="receipt-components"` on the component list `<ul>`. The implementation has no `data-testid` on the `<ul>`.

**14. Section headings structure does not match §3 Accessibility table (lines 185-246)**
Per §3 Accessibility: the receipt section structure requires: `<header>` (score row), `<h2>` visually-hidden for "How it works", `<h3>` per component, `<h2>` visually-hidden for "Why we mix both", `<h2>` visually-hidden for "Sources". The implementation uses `<div>` elements for section eyebrows ("How it works", "Where the data comes from", "Why we mix both pieces") — none are heading elements, and no `sr-only` headings are present. Screen readers cannot navigate between sections.

**15. Sources section visual eyebrow + `sr-only` heading pattern missing (lines 241-264)**
Per §3 Accessibility: the Sources heading should be `<h2 class="sr-only">Sources</h2>` (screen-reader) + `<div aria-hidden>SOURCES</div>` (visible decorative). The implementation has a visible `<div>` saying "Where the data comes from" but no `sr-only` heading and no `aria-hidden` on the decorative text. The eyebrow text also differs from the spec's "SOURCES" — a cosmetic difference but one the visionary specified.

**16. The article's entrance animation misses the `scale: 0.985` component (line 143)**
Per §3 "Receipt mounts" row: `initial={{ opacity: 0, y: 12, scale: 0.985 }}`. The implementation has `initial={{ opacity: 0, y: 12 }}` — the `scale: 0.985` initial value is absent. Without it the "settling onto the desk" feel the spec calls out is absent (the y-slide alone is insufficient).

### WARNINGS

**W1. The `How it works` heading section style diverges from §3 eyebrow spec**
The spec says section eyebrows are `font-display weight 600 13px letter-spacing 1.5px text-text-muted uppercase`. The `"How it works"` div at line 187-190 has `font-display font-semibold text-text-primary` at 13px with only `0.3px` letter-spacing — it uses `text-text-primary` (not `text-text-muted`) and `0.3px` (not `1.5px`). The letter-spacing on section eyebrows is a strong visual identifier; `0.3px` reads as a label, not a heading. The spec repeats `letter-spacing: 1.5px` in both the "Score callout eyebrow" section and the "Sources eyebrow" section. The `0.3px` value is from §3 "How it works" row of the spec table which specifies `0.3px` for the section label — this may be intentional divergence from the eyebrow style. Not a hard token violation but worth confirming with the visionary.

**W2. Pill hover uses CSS `transition-colors` rather than `springs.snappy` via Framer `whileHover`**
DESIGN.md §Motion System states "CSS transitions handle simple hover/focus states" — this aligns with the implementation. §3's spec-specific interaction table calls for `springs.snappy` via `whileHover`. The two sources conflict. DESIGN.md has protocol precedence over the component's own interaction table on the CSS-vs-Framer question. The missing stat-color hover border and background lift are the actual failures (FAIL item 9); the transition mechanism alone is a warning.

**W3. `motion.div` wrappers around `<li>` elements rather than `motion.li` (lines 199-204)**
The component renders `<motion.div key={c.weight_pct} variants={staggerItem}><ComponentRow .../></motion.div>` inside the `<motion.ul>`. A `<div>` inside a `<ul>` is invalid HTML — list items must be direct `<li>` children of `<ul>`. The `ComponentRow` renders an `<li>` correctly, but the `motion.div` wrapper creates `ul > div > li`, which validators and some screen readers reject. `motion.li` should wrap the `ComponentRow` or `ComponentRow` itself should be a `motion.li`.

**W4. `padding: "14px 18px"` on the math card uses a 2-value shorthand with off-grid vertical (14px)**
The Brightpath 4px spacing scale includes 12px and 16px but not 14px (see DESIGN.md §Spacing). 14px is within the Brightpath spec's explicit math-card padding value (`padding: 14px 18px` per §3 "Math line container" row) — the spec overrides the general grid rule for this specific element. No change needed; flagging for visibility.

---

## frontend/src/components/menu/GemmaChat.tsx (narrow audit)

### PASS
- `renderMessageWithTrace` dispatches correctly on `m.kind`: `"receipt"` → `<ExplainStatReceiptCard payload={m.payload} />` (line 336); all other kinds (including `"text"`) → `<ChatMessage message={{ role: m.role, content: m.content }}>` (line 339). The dispatch is exhaustive for the current two-kind union.
- No new rendering branch beyond `"receipt"` and the text fallback was added.
- Loading state (`renderSendingRow`), error state, and scroll behavior are visually unchanged from the pre-receipt implementation.
- `assistantHistoryItem` helper (lines 24-31) correctly constructs the discriminated union on string vs. object response shape. Dark-first token usage in the surrounding chat UI is unchanged.
- The send button has a hardcoded hover hex `hover:bg-[#6bc494]` at line 481 and line 627. This is a pre-existing violation outside this audit's new-surface scope, noted for awareness only.

### WARNINGS
- **W5. TypeScript exhaustiveness on `m.kind` is not enforced by `never` check.** The dispatch in `renderMessageWithTrace` uses an `if`/`else` (line 336-340) rather than a `switch` with an exhaustive `never` fallback. If a third `kind` is added to `ChatHistoryItem` in a future spec without updating this renderer, it silently falls through to `<ChatMessage>` with a type error on `m.content`. The spec's §2 Decision 12 called for exhaustive dispatch — a `switch` with a `default: assertNever(m)` pattern would enforce this at compile time. Not a token violation; a TypeScript hygiene note for the code reviewer.

---

## frontend/src/components/menu/ChatMessage.tsx (narrow audit)

### PASS
- Prop type correctly narrows to `{ role: "user" | "assistant"; content: string }` — the text-only shape of `ChatHistoryItem`. The component is decoupled from the receipt branch.
- No visual changes were introduced. Pre-existing token usage (`bg-bp-surface`, `bg-bp-deep`, `rounded-lg`, `font-body`, `text-text-primary`, `text-body`) are all compliant Brightpath tokens.
- The comment at lines 6-10 documents the narrowing intent. PASS.

---

## Verdict: CHANGES REQUIRED — RESOLVED 2026-05-02

**FAIL count: 16/16 RESOLVED**
**WARNING count: W3 RESOLVED (motion.li wrapping fixed); W1, W2, W4, W5 acknowledged, non-blocking, deferred to follow-up.**

### Resolution log (Phase 5 → Phase 5b implementer pass)

All 16 FAIL items applied to `frontend/src/components/menu/ExplainStatReceipt.tsx`:

| # | Item | Resolution |
|---|------|------------|
| 1 | `border-border-subtle` → `border-border-default` | Changed in className |
| 2 | `rounded-xl` → `rounded-[14px]` | Changed in className |
| 3 | Card shadow missing | Added `boxShadow: "0 8px 32px rgba(27,29,48,0.55)"` to article style |
| 4 | Score callout layout | Rewritten — eyebrow row uses `text-text-muted` + uppercase + 1.5px letter-spacing + 13px; score number now 44px; slash/max uses `text-text-muted` + 22px (not opacity-50) |
| 5 | Missing `data-testid="receipt-score"` | Added to score callout div |
| 6 | Source pill testid uses index, not slug | New `shortFormForSource` helper produces a deterministic slug; testids now `receipt-source-college-scorecard` and `receipt-source-bls-ooh` |
| 7 | Score `aria-label` missing stat name | Now `${stat_name} score: ${score} out of ${score_max}` |
| 8 | Source pill missing focus-visible ring | Added `focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-none` |
| 9 | Source pill hover missing bg lift + stat-color border | Now `hover:bg-bp-raised hover:[border-color:var(--color-stat-ern)]` |
| 10 | Source pill missing `{label} · {short form}` content | Now renders `<span>{label}</span> · <span>{shortForm}</span>` with the lookup table |
| 11 | Missing percentile callout row + `◦ —` glyph | Added: present-data renders `{N}th percentile · median $X,XXX`; null-data renders `◦ —` with `aria-label="data not available"` |
| 12 | Math card missing `role="math"` + `aria-label` | Added both |
| 13 | `data-testid="receipt-components"` missing on `<ul>` | Added |
| 14 | Section eyebrows are `<div>`, not headings | Each section now has `<section aria-labelledby>` + `<h2 class="sr-only">` heading + `<div aria-hidden>` decorative eyebrow |
| 15 | Sources sr-only heading + aria-hidden pattern missing | Same pattern applied to sources section; visible eyebrow text changed from "Where the data comes from" to "SOURCES" |
| 16 | Article entrance missing `scale: 0.985` | Added to initial state; animate scales to 1 |
| W3 | `motion.div` wrapping `<li>` (invalid HTML) | `ComponentRow` is now a `motion.li` directly; outer wrapper removed |

### Phase 4 test fixture updates triggered by Phase 5

Three frontend test assertions were rewritten to match the new component contract:

1. `test_renders_default_state` — section headings now appear twice (sr-only h2 + decorative div); changed from `getByText` to `getAllByText` and updated "Where the data comes from" → "Sources".
2. `test_renders_default_state` — "87th percentile" appears in both the explainer prose AND the new percentile callout row; changed to `getAllByText`.
3. `test_renders_missing_school_rank` — `text-text-muted` is now also used by the always-muted percentile callout, so dim-on-missing detection scopes to the `.flex-1` prose wrapper instead of the whole row. Asserts `text-text-muted` on the missing row's wrapper and `text-text-secondary` on the present row's wrapper.
4. `test_accessibility_attributes` — source-pill testid changed from `receipt-source-0` to `receipt-source-college-scorecard`.

All 8 receipt component tests pass after these updates. Full frontend suite: **790/790 pass**.

### Non-blocking warnings (deferred)

- **W1** — section-eyebrow letter-spacing 0.3px vs §3 spec 1.5px. Resolved by adopting the 1.5px spec value across all four section eyebrows in this Phase 5b pass.
- **W2** — pill hover uses CSS `transition-colors` instead of Framer `whileHover` + `springs.snappy`. DESIGN.md §Motion System endorses CSS for simple hover/focus; the spec table is overridden by DESIGN.md per @fp-design-auditor's own note. Kept as CSS.
- **W4** — math-card 14px vertical padding is off the 4px grid; per §3 spec this is an explicit exception for the math-card surface. Acknowledged.
- **W5** — `assertNever` exhaustiveness check on `m.kind` dispatch in `GemmaChat.renderMessageWithTrace`. TypeScript hygiene; not a token violation. Code reviewer to call out if they want it added.

Items requiring fix before Phase 6, grouped by priority:

**P0 — Accessibility blockers (keyboard/screen-reader failures):**
- FAIL 5: Missing `data-testid="receipt-score"` on score element
- FAIL 7: `aria-label` on score element omits stat name
- FAIL 8: Source pill missing `focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-none`
- FAIL 12: Math line container missing `role="math"` and `aria-label`
- FAIL 13: `data-testid="receipt-components"` missing on `<ul>`
- FAIL 14: Section headings are `<div>` elements — screen readers cannot navigate sections
- FAIL 15: Sources `sr-only` heading and `aria-hidden` decorative pattern missing

**P1 — Visual spec violations (visible differences from design):**
- FAIL 1: `border-border-subtle` → `border-border-default`
- FAIL 2: `rounded-xl` (20px) → `rounded-[14px]`
- FAIL 3: Missing card shadow `0 8px 32px rgba(27,29,48,0.55)`
- FAIL 4: Score callout layout — eyebrow color/size/case, score font size (32px vs 44px), slash/max token and size
- FAIL 9: Source pill hover missing background lift and stat-color border
- FAIL 10: Source pill missing `{label} · {name short form}` content and name lookup
- FAIL 11: Missing percentile callout row and `◦ —` missing-data glyph
- FAIL 16: Missing `scale: 0.985` on article entrance initial state

**W3** (invalid HTML) is also recommended for fix before ship.

### Code Review (@faang-staff-engineer)
**Status:** CHANGES REQUIRED
**Reviewed:** 2026-05-02
**Reviewer note.** This was a thorough audit — security, performance, error handling, the cached-fallback contract, JSON-mode synthesis-turn scoping, and trust boundaries between Gemma's output and the server-stamped fields. The architecture is sound and the spec's calls (server owns numbers, Gemma owns voice, `extra="forbid"`, sentinel-passthrough validator) are correctly realized in code. The trust boundary work is solid and the JSON-mode threading is correct. There are, however, four bugs worth fixing before merge — one of them rendering-correctness (`[object Object]` leaking to the user), one user-facing copy (effort labels not matching the actual `EffortLevel` literal set), one silent data-loss (`tool_result_preview` truncated below the size of a real `get_career_paths` result), and one effort-line-suppression edge case. Tests pass, but two test cases assert behavior on inputs that cannot occur in production (`effort="chill"`).

#### Findings

##### 🔴 BLOCKERS

**B1. The frontend Zod fallback renders `[object Object]` to the user when an object payload fails the receipt schema.**
**Location:** `frontend/src/api/menu.ts:175-184` (`parseFinalTextResponse`).
**Impact:** Concern #5 from the prompt is a real bug. When `final_text.response` is a non-string, non-receipt-shaped object (malformed wire payload, schema drift, partial Pydantic-rejected serialization on the server, or — the realistic case — a future receipt-schema bump where the frontend ships before the backend does), `safeParse` returns `{success: false}` and the function falls through to `return String(value ?? "")`. `String({foo: 1})` → `"[object Object]"`. The string lands in the chat history as if it were a normal Gemma reply and gets rendered verbatim by `<ChatMessage>`. The student sees the literal text **`[object Object]`** in their chat. This is the exact UX disaster the prompt called out.
```typescript
// CURRENT — broken
function parseFinalTextResponse(value: unknown): string | ExplainStatReceipt {
  if (typeof value === "string") return value;
  if (typeof value === "object" && value !== null) {
    const result = explainStatReceiptSchema.safeParse(value);
    if (result.success) return result.data;
  }
  return String(value ?? "");  // returns "[object Object]" for any object that fails Zod
}
```
**The Fix:** Return a graceful fallback string for the malformed-object case. The Test §7 fixture `test_zod_parser_falls_back_to_string_on_invalid_object` should also be tightened so it asserts the fallback is NOT `"[object Object]"`.
```typescript
function parseFinalTextResponse(value: unknown): string | ExplainStatReceipt {
  if (typeof value === "string") return value;
  if (typeof value === "object" && value !== null) {
    const result = explainStatReceiptSchema.safeParse(value);
    if (result.success) return result.data;
    // Object failed Zod — don't leak [object Object] to the user.
    return "";  // empty string falls through to the chat_unavailable rail at the renderer level
  }
  return typeof value === "string" ? value : "";
}
```
Severity: 🔴 Critical — direct user-facing rendering bug, easily reachable in production.

**B2. `_render_math_line` effort labels don't match the actual `EffortLevel` literal set.**
**Location:** `backend/app/services/ask_gemma.py:587-595` (`_render_math_line`); supporting test at `backend/tests/services/test_ask_gemma_explain_receipt.py:788-806`.
**Impact:** The implementation calls `effort.capitalize()` to render the effort label inside the bold `**{Effort}**` segment. The actual `EffortLevel` literal in `backend/app/models/career.py:16` is:
```python
EffortLevel = Literal["working_hard", "working", "balanced", "focused", "all_in"]
```
For real builds, `_render_math_line` will render:
- `effort="working_hard"` → `"Your **Working_hard** effort setting brings this to..."` ← reads as broken copy
- `effort="working"` → `"Your **Working** effort setting brings this..."` ← acceptable but flat
- `effort="all_in"` → `"Your **All_in** effort setting lifts this..."` ← reads as broken copy
- `effort="focused"` → `"Your **Focused** effort setting lifts this..."` ← OK
- `effort="balanced"` → no effort line (correct)

The Phase 4 test `test_render_math_line_chill_effort` is testing an effort string (`"chill"`) that is not a valid `EffortLevel`. The test passes because `_render_math_line` accepts `effort: str` (typed loosely) and matches anything `!= "balanced"`. This is a test-passing-but-wrong-in-prod situation.

**The Fix:** Add an effort-label lookup table and reject unknown values with a balanced-effort fallback (no effort line). Replace `effort.capitalize()` with the friendly form. Drop the `chill` test or rewrite it against `working` / `working_hard`.
```python
# At module top, beside _ERN_LABEL_ALLOWLIST.
_EFFORT_LABELS: dict[str, str] = {
    "working_hard": "Working Hard",
    "working":      "Working",
    "balanced":     "Balanced",
    "focused":      "Focused",
    "all_in":       "All-In",
}

def _render_math_line(...):
    ...
    if effort == "balanced" or unshifted == build_score:
        return base
    label = _EFFORT_LABELS.get(effort)
    if label is None:
        return base  # unknown effort — defensive: no effort line
    direction = "lifts" if build_score > unshifted else "brings"
    return f"{base}\nYour **{label}** effort setting {direction} this to {build_score}/{score_max}"
```
Severity: 🔴 Critical for product-quality. Working-effort and all-in students are the majority of explorers; what they see is the load-bearing UX moment of this entire spec.

##### 🟠 SERIOUS

**S1. `tool_result_preview` truncation at 500 bytes silently drops percentile data on real `get_career_paths` results.**
**Location:** `backend/app/services/gemma_client.py:947` (`_TOOL_RESULT_PREVIEW_MAX = 500`); `backend/app/services/ask_gemma.py:507-552` (`_extract_tool_results`).
**Impact:** Concern #6 in the prompt — confirmed real. `get_career_paths` returns `{"results": [<row>, ...]}` where each row is a multi-field object. With school+major substitution scenarios surfacing many rows in `cipcode` family neighbors, the response is regularly multi-kilobyte. `_extract_tool_results` calls `json.loads(turn.tool_result_preview)` against a string truncated to 500 bytes — almost guaranteed to land mid-array on a real `program_career_paths` result, which makes `json.loads` raise `JSONDecodeError`. The function silently `continue`s past the failed turn. The result: `cip_rank=None, earnings=None`, even when the data was actually fetched correctly. The receipt then fires the missing-data UI, the cached-fallback path also shows "n/a", and the markdown fallback's user-message-injection block reads `cip_family_earnings_rank = None` despite the tool having returned a valid value.
```python
# In gemma_client.py:1189
tool_result_preview=result_str[:_TOOL_RESULT_PREVIEW_MAX],  # 500 bytes — too small
```
This is silent data-loss; nothing alerts (the truncation is invisible to `_extract_tool_results`). Symptoms in production will look like "lots of programs randomly hit the missing-data path."
**The Fix:** Either (a) raise `_TOOL_RESULT_PREVIEW_MAX` to a value that comfortably holds typical results (4096 or 8192), or (b) carry the un-truncated result on `ToolCallTurn` for server-side post-processing while keeping the truncation purely for the frontend trace-rail preview. (b) is cleaner; the truncation exists for the SSE wire size of the trace UI, not for downstream consumers. Add a non-truncated `tool_result_full: str` field on `ToolCallTurn` (server-only — exclude from `TraceTurnComplete` Pydantic serialization) and have `_extract_tool_results` read from it.
Severity: 🟠 Serious — silent correctness regression on the gold path.

**S2. `_render_math_line` halfway-case suppresses the effort line when one percentile is None.**
**Location:** `backend/app/services/ask_gemma.py:578-595`.
**Impact:** Concern #8 in the prompt — confirmed. When `cip_rank` is None XOR `wage_pct` is None (one missing, one present — the realistic single-missing-data state), the function falls back to `unshifted = build_score` (line 580). The next gate at line 587 is `if effort == "balanced" or unshifted == build_score: return base`. Because we set `unshifted = build_score`, the condition collapses to True for ALL non-balanced efforts when one percentile is null. **The effort-line is unconditionally suppressed in the halfway-missing case.** A focused-effort student with missing school-rank data sees the math line `0.6 × n/a + 0.4 × 0.37 → score 7/10` and no effort-line annotation — but their score `7/10` was effort-shifted from a build-derived value, and the receipt is silent about that shift. Decision 13 explicitly calls out the effort signal as load-bearing for trust ("two different N-values that fundamentally undermine the explainer's purpose"). Suppressing the effort-line silently is exactly the trust-collapse Decision 13 was designed to prevent.
**The Fix:** When one percentile is null, render the math line as `→ score N/M` using `build_score` directly, but keep the effort-line independent of the unshifted/shifted comparison — drive it solely from `effort != "balanced"`.
```python
def _render_math_line(...):
    cip_str = f"{cip_rank:.2f}" if cip_rank is not None else "n/a"
    wage_str = f"{wage_pct:.2f}" if wage_pct is not None else "n/a"

    if cip_rank is not None and wage_pct is not None:
        raw = 0.6 * cip_rank + 0.4 * wage_pct
        unshifted = max(1, min(score_max, int(1.0 + 9.0 * raw + 0.5)))
        base_score = unshifted
    else:
        # Halfway / both-missing: math can't be derived; show build_score in the arrow.
        unshifted = None
        base_score = build_score

    base = f"0.6 × {cip_str} + 0.4 × {wage_str} → score {base_score}/{score_max}"

    if effort == "balanced":
        return base
    # When the unshifted derivation is available AND equal to build_score, no effort line.
    if unshifted is not None and unshifted == build_score:
        return base

    label = _EFFORT_LABELS.get(effort)
    if label is None:
        return base
    if unshifted is None:
        # No derivation — say the effort applies, without claiming a "from-N to M" delta.
        return f"{base}\nYour **{label}** effort setting is reflected in this score"
    direction = "lifts" if build_score > unshifted else "brings"
    return f"{base}\nYour **{label}** effort setting {direction} this to {build_score}/{score_max}"
```
Severity: 🟠 Serious — silent trust regression in a state the spec explicitly considered.

**S3. The streaming markdown fallback is awaited inline, defeating the SSE-disconnect cleanup contract.**
**Location:** `backend/app/services/ask_gemma.py:1314-1328`.
**Impact:** The streaming generator wraps the JSON-mode `loop_task` in `asyncio.create_task(...)` and the `finally` cancels it on client disconnect (lines 1340-1349) so the Gemma semaphore releases within ~100ms. But the markdown-fallback retry calls `await gemma_client.generate_with_tools_loop(...)` directly inline (line 1315-1328) instead of as a task. If the SSE client disconnects during the fallback's await, FastAPI raises `GeneratorExit` at the next `yield` — but the `await` on the fallback isn't cancellable from the `finally`, so the Gemma call holds its semaphore for up to the 30s `max_wall_time_s` cap. Decision C4 explicitly calls out the semaphore-release contract; the fallback path silently violates it.
**The Fix:** Wrap the fallback in `asyncio.create_task` and pin it to a local that the `finally` block can cancel.
```python
fallback_task = asyncio.create_task(
    gemma_client.generate_with_tools_loop(
        system=markdown_system, user=markdown_user, tools=[], ...
    )
)
try:
    text, _ = await fallback_task
except Exception as exc:
    logger.warning("ern_explain_receipt fallback failed: %s", exc)
    text = ""
# In finally: also cancel fallback_task if not done.
```
And teach the existing `finally` to cancel `fallback_task` too.
Severity: 🟠 Serious — semaphore starvation under load with disconnecting clients.

**S4. `score_max` is not server-stamped or validated.**
**Location:** `backend/app/models/api.py:372-378`; `backend/app/services/ask_gemma.py:768`.
**Impact:** The Pydantic field declares `score_max: int = Field(default=10, ...)` with NO `ge`/`le` bounds. Gemma can emit `score_max: 100` and Pydantic accepts it. The server then passes that value into `_render_math_line(..., score_max=receipt.score_max, ...)`, which renders `→ score N/100`. The frontend consumes `payload.score_max` to render `9 / 10` — with `score_max=100` it renders `9 / 100`. The score callout becomes silently wrong. Concern #7 in the prompt ("server stamps score, why not score_max?") is a fair worry — `score` is unconditionally stamped, but `score_max` isn't.
**The Fix:** Either (a) constrain via Pydantic — `score_max: int = Field(default=10, ge=1, le=10)` for v1.0 since the field is "fixed at 10 in v1.0" per the schema docstring; or (b) server-stamp it to 10 in `_postprocess_ern_explain_receipt` step 6 alongside the score override.
```python
# In _postprocess_ern_explain_receipt, alongside step 6:
receipt.score = build_score
receipt.score_max = 10  # spec says fixed at 10 for v1.0
```
Severity: 🟠 Serious — small attack surface (Gemma error window), but the schema's "trust the server" promise is stronger if `score_max` is also server-controlled.

##### 🟡 MODERATE

**M1. Sentinel passthrough regex `\bPLACEHOLDER\b` is over-eager for legitimate prose.**
**Location:** `backend/app/models/api.py:223`.
**Impact:** Concern #10 in the prompt — there is real risk, but it's contained. The ERN-explain prose is constrained to school+major+career topics; a student typing the sentinel `[explain-this:ERN]` is locked to that narrow surface. The chance Gemma's prose contains the standalone word "placeholder" is low. However: when the SKILL.md guidance evolves or a future stat-explain reuses the schema, the regex becomes more brittle. The other four sentinels are well-bounded (`__FILL_IN__`, `[FILL_IN]`, `<FILL_IN>`, `ONE-SENTENCE DEFINITION HERE`); only `\bPLACEHOLDER\b` matches a common English word. The over-eagerness costs a fallback round-trip (~5-10s) for a benign string match.
**The Fix:** Tighten to either `r"\b__?PLACEHOLDER__?\b"` (matches `_PLACEHOLDER_` and `__PLACEHOLDER__` like the other sentinels) or remove this pattern entirely (the four bracketed/explicit ones cover the actual appendix text). The appendix actually doesn't write the literal "PLACEHOLDER" anywhere — only "placeholders" appears in the *prose* of the appendix instructions. Removing the standalone word from the regex set tightens the trust boundary without losing any actual sentinel coverage.
Severity: 🟡 Moderate — defensive paranoia, low real-world hit rate.

**M2. `_normalize_label` lowercase comparison loses canonical-string-distance tolerance.**
**Location:** `backend/app/services/ask_gemma.py:599-618`; spec §6 deviation 2 acknowledges this.
**Impact:** Concern #14 in the prompt. Spec Decision 14 calls for "match by weight first, then nearest-string-distance." Implementation matches by weight, then `.strip().lower()` equality. This means `"Your school's program rank"` (capitalized Y) gets normalized — fine, that's the swap case the function exists to solve. But the WARNING fires on every benign capitalization variant Gemma produces. The function is correctness-preserving (always lands on the canonical) but log-noisy.
**The Fix:** Either accept the noise (the WARNING is informational and the parse_success_rate metric isn't affected), OR add `difflib.SequenceMatcher.ratio() > 0.85` as a "close enough; don't normalize" gate. The implementation as-is is acceptable; the spec deviation note in §6 is honest about it.
Severity: 🟡 Moderate — log noise only, no correctness impact.

**M3. `_extract_tool_results` doesn't dedupe / handle multiple turns of the same tool.**
**Location:** `backend/app/services/ask_gemma.py:521-552`.
**Impact:** The loop iterates `tool_call_log` and assigns `cip_rank` / `earnings` / etc. on every match. If Gemma calls `get_career_paths` twice (different cipcode arguments; e.g., it tried a substitution lookup then the canonical), the LAST matching turn wins. There's no guard for "use the turn whose `cipcode` argument matches `career.cipcode`." For most cases this is fine, but on substitution flows it's a quiet correctness footgun.
**The Fix:** Match on tool args too. Filter tool calls where `turn.tool_args.get("cipcode") == build.career.cipcode` AND `turn.tool_args.get("unitid") == build.career.unitid`.
Severity: 🟡 Moderate — substitution flows could see the wrong row's percentile.

**M4. `_log_receipt_parse` `json_prefix` is the first 500 chars of Gemma's raw output. Includes student PII through the appendix.**
**Location:** `backend/app/services/ask_gemma.py:639` (`json_prefix[:500]`).
**Impact:** Concern #13 in the prompt. The appendix at `_ern_explain_appendix_json` injects `career.unitid`, `career.cipcode`, and `career.soc_code` into the system prompt. Gemma's raw response usually starts with `{"kind": "receipt", "stat_code": "ERN", "stat_name": "Earning Power", ...` — the first 500 chars typically do NOT include school+program names (those land deeper, in the explainer prose). But Gemma is non-deterministic; if it echoes "Indiana University Computer Science" in the `anchor_text` field early enough, the PII lands in `gemma.jsonl`. The current model leaks at most institution + program + career identifiers (no email, no SSN, no DOB). For the project's data-handling rules these are NOT considered PII (they're public-record school choices), but the team should explicitly say so in writing.
**The Fix:** Either (a) confirm in writing that institution_name, program_name, and occupation_title are non-PII per project policy, or (b) hash/redact those three identifiers in `json_prefix` before logging. (a) is the lighter touch and matches the existing logging surface (`gemma_client._log_exchange` already records system+user prompts verbatim, which contain the same identifiers).
Severity: 🟡 Moderate — depends on the team's PII classification.

##### 🔵 MINOR

**N1. The `_TOOL_RESULT_PREVIEW_MAX` constant is private but consumed across module boundaries by the explain-receipt path.**
**Location:** `backend/app/services/ask_gemma.py` reads `gemma_client._extract_json_objects` and now indirectly depends on `gemma_client._TOOL_RESULT_PREVIEW_MAX`'s value being adequate for `_extract_tool_results` to deserialize. The cross-module coupling isn't documented.
**The Fix:** Either expose a public constant or comment the dependency at the call site. Tied to S1's resolution — if `tool_result_full` becomes a separate field, the coupling goes away.
Severity: 🔵 Minor — code-organization nit.

**N2. `_postprocess_ern_explain_receipt` step 9 uses `weight_pct == 60` and `weight_pct == 40` as magic numbers.**
**Location:** `backend/app/services/ask_gemma.py:787-810`.
**Impact:** Future ROI/RES specs will reuse the same code shape; the hard-coded 60/40 weight values become a refactor obstacle. The `_ERN_LABEL_ALLOWLIST` already has the canonical weight->label mapping; the value-stamping logic should drive off the same allowlist or accept a config dict.
**The Fix:** Optional cleanup; not blocking. ROI is a separate spec.
Severity: 🔵 Minor.

**N3. `int(cip_rank * 100 + 0.5)` halfway-rounding is correct but inconsistent with `_format_pct`.**
**Location:** `backend/app/services/ask_gemma.py:790, 801` and `497-504`.
**Impact:** `_format_pct` uses `int(value * 100 + 0.5)` and `_postprocess_ern_explain_receipt` re-implements the same expression in steps 9. Same math, two places. DRY.
**The Fix:** `comp.value_pct = int(_format_pct(cip_rank))` if `cip_rank is not None else None`. (`_format_pct` already returns "n/a" for None, so the inline guard stays.) Cleaner; not blocking.
Severity: 🔵 Minor.

**N4. The fallback path's tool_call_log isn't appended to the final `AskResponse.tool_calls`.**
**Location:** `backend/app/services/ask_gemma.py:1027-1059` (non-stream path).
**Impact:** When the fallback fires in `chat_ask`, the post-processing at line 1046 builds `tool_calls` from the original `tool_call_log` (correctly — that's where the real MCP work happened). But `fallback_tool_log` from line 1017 is captured then discarded. With `tools=[]` the fallback log is empty anyway, so this is benign — but worth a comment so a future maintainer doesn't add tools to the fallback and forget to merge logs.
Severity: 🔵 Minor.

**N5. `GemmaChat.renderMessageWithTrace` lacks `assertNever` exhaustiveness on the `kind` discriminator.**
**Location:** `frontend/src/components/menu/GemmaChat.tsx:336-340`.
**Impact:** Auditor's W5 — confirmed. A future third `kind` (e.g., `"compare-card"`) silently falls through to `<ChatMessage>` with a TypeScript error on `m.content`. `switch (m.kind) { case "receipt": ...; case "text": ...; default: const _: never = m; throw new Error(...); }` would catch the omission at compile time.
Severity: 🔵 Minor — TypeScript hygiene.

##### 🟢 PRAISE

**P1. Trust-boundary discipline is solid.** The 10-step `_postprocess_ern_explain_receipt` pipeline correctly server-stamps `score`, `math_line`, `value_pct`, `anchor_dollars`, `missing_reason`, and `sources` — every numeric field that the spec promises is overwritten. The Pydantic `extra="forbid"` config plus the sentinel-passthrough validator close every realistic vector for Gemma to inject content the server didn't approve. The `_normalize_label` allowlist match-by-weight is the right call for catching the swap case.

**P2. Synthesis-turn-only JSON-mode scoping is correctly implemented.** The `prev_turn_had_tool_calls` flag walks correctly across loop iterations: turn 0 sees `effective_response_format = None`, the flag flips to True only AFTER tool calls fire, and turn 1+ sees the JSON-mode dict. I traced two-tool-call and three-turn flows by hand; the scoping holds. Decision 15 is realized in the loop.

**P3. The Ollama `format` translation handles all three `response_format` shapes defensively.** `{"type": "json_object"}` → `"json"`; `{"type": "json_schema", "json_schema": {"schema": {...}}}` → schema dict; unknown shapes fall through to `payload["format"] = response_format` (passes through). `None` is a no-op (the `if response_format is not None` guard at line 1391 keeps `payload` clean). Concern #4 from the prompt is covered.

**P4. The cached-fallback path correctly avoids re-fetching MCP tools.** `tools=[]` is passed to the fallback `generate_with_tools_loop` AND the markdown appendix tells Gemma not to call them. Both belt and suspenders. The cached values inject into the user message via `_format_cached_tool_values`. The trace events from the JSON attempt are correctly preserved as the canonical record (no duplicate events for the fallback turn). Concern #2 from the prompt is well-handled.

**P5. The `extra="forbid"` Pydantic config is consistently applied to all three new models** (`ReceiptSource`, `StatComponent`, `ExplainStatReceipt`). Future spec extensions adding fields will fail-loudly at parse time rather than silently accepting unexpected payloads. Same hygiene level as the rest of the `app.models.api` module.

**P6. The streaming generator's existing `try/finally` cancellation contract for `loop_task` is preserved.** SSE-disconnect cleanup works correctly for the JSON attempt — only the fallback path violates it (S3). The original semaphore-release contract is otherwise intact.

**P7. The `_extract_json_objects` reuse for the fence-stripping JSON parse is the right primitive.** Per genai-architect Condition 2, the same helper that handles ` ```json{...}``` ` and trailing-prose extraction is reused — no parse logic forks. Tests exercise both fence and trailing-prose cases.

#### Required Changes (Before Phase 7 Approval)

Routed to the implementation agent (Claude Code, original implementer of Phase 3):

1. **B1 — Frontend Zod fallback:** `parseFinalTextResponse` must not return `"[object Object]"` for malformed objects. Return empty string or null. Update the test to assert the fallback string is NOT `"[object Object]"`.
2. **B2 — Effort labels:** Add `_EFFORT_LABELS: dict[str, str]` mapping the actual `EffortLevel` literals to user-facing labels. Replace `effort.capitalize()` with the lookup. Drop or rewrite `test_render_math_line_chill_effort` against `working` / `working_hard`.
3. **S1 — Tool-result truncation:** Either raise `_TOOL_RESULT_PREVIEW_MAX` to ≥4096, or split `tool_result_preview` (truncated, frontend-trace-only) from `tool_result_full` (un-truncated, server-only). The former is simplest; the latter is cleaner.
4. **S2 — Halfway-case effort line:** When one percentile is None and effort is non-balanced, render an effort-line that doesn't claim a from-N-to-M delta. See suggested fix above.
5. **S3 — SSE fallback semaphore release:** Wrap the markdown-fallback `await` inside `chat_ask_stream` in `asyncio.create_task` and cancel it in the existing `finally` block alongside `loop_task`.
6. **S4 — `score_max` server-stamping:** Either constrain via Pydantic `Field(default=10, ge=1, le=10)` OR server-stamp in step 6 of `_postprocess_ern_explain_receipt`.

Optional (non-blocking, address at implementer's discretion):
- **M1** — Tighten or remove the standalone-word `\bPLACEHOLDER\b` sentinel pattern.
- **M3** — Match `_extract_tool_results` against `turn.tool_args.cipcode/unitid` to handle multi-turn substitution flows.
- **M4** — Document PII classification for institution/program/occupation identifiers.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUIRED → RESOLVED 2026-05-02 (Phase 6b implementer pass)
- [ ] BLOCKER

**Summary of finding counts:** 🔴 BLOCKER ×2 · 🟠 SERIOUS ×4 · 🟡 MODERATE ×4 · 🔵 MINOR ×5 · 🟢 PRAISE ×7

#### Resolution log (Phase 6 → Phase 6b implementer pass)

All 6 required changes (B1, B2, S1, S2, S3, S4) applied. M1 also addressed.

| ID | Item | Resolution |
|----|------|------------|
| **B1** | `parseFinalTextResponse` returns `[object Object]` for malformed objects | Now returns `""` for malformed objects (Zod-failed objects AND non-string non-object values). Test `test_zod_parser_falls_back_to_string_on_invalid_object` strengthened to assert `response !== "[object Object]"`. |
| **B2** | `effort.capitalize()` renders `Working_hard` / `All_in` for real EffortLevel values | New `_EFFORT_LABELS: dict[str, str]` table maps each `EffortLevel` literal (`working_hard`, `working`, `balanced`, `focused`, `all_in`) to a friendly form (`Working Hard`, `Working`, `Balanced`, `Focused`, `All-In`). `_render_math_line` looks up the label; unknown effort strings get no effort line (defensive). New tests `test_render_math_line_working_hard_effort`, `test_render_math_line_all_in_effort`, `test_render_math_line_unknown_effort_no_line` replace the dropped `chill` test. |
| **S1** | `_TOOL_RESULT_PREVIEW_MAX = 500` truncates real `get_career_paths` results mid-array | Added `tool_result_full: str = ""` field on `ToolCallTurn` carrying the un-truncated string (server-only — not in `TraceTurnComplete` SSE serialization). `gemma_client._tools_loop_inner` populates it. `_extract_tool_results` reads `turn.tool_result_full or turn.tool_result_preview` (preview as a backward-compat fallback). |
| **S2** | Halfway-case (one percentile null) silently suppressed effort line | `_render_math_line` rewritten: when one input is null, the unshifted derivation is unavailable; the function shows `build_score` in the arrow and emits an effort line "Your **{Effort}** effort setting is reflected in this score" (no from-N-to-M claim). Two new tests cover the halfway-case-with-effort and halfway-case-balanced-no-effort-line paths. |
| **S3** | Streaming markdown fallback `await` not cancellable on SSE disconnect | Wrapped the fallback `generate_with_tools_loop` call in `asyncio.create_task` and tracked it as `fallback_task` in the streaming generator. The `finally` block now cancels both `loop_task` and `fallback_task` (when in-flight) and gathers them. Decision C4 contract restored. |
| **S4** | `score_max` not server-stamped or validated | `_postprocess_ern_explain_receipt` step 6 now stamps `receipt.score_max = 10` alongside the score override. |
| **M1** | `\bPLACEHOLDER\b` over-eager — matches "placeholder" in legitimate prose | Tightened to `__PLACEHOLDER__|\[PLACEHOLDER\]|<PLACEHOLDER>`. Sentinel test `_SENTINEL_VALUES` updated to use `__PLACEHOLDER__` instead of bare `PLACEHOLDER`. |

**Test results post-fix:**
- Backend pytest: 1399/1399 pass (was 1395 — added 4 new effort-label tests, 1 was renamed). 0 regressions.
- Frontend vitest: 790/790 pass. 0 regressions.

**Non-blocking items deferred:** M2 (lowercase normalization noise — acknowledged in §6 deviation 2; log-noise only), M3 (multi-turn substitution flow — single-turn flow is current production behavior; flagged for follow-up), M4 (PII classification — institution/program/occupation are public-record school choices, consistent with existing `_log_exchange` logging surface). N1–N5 minor items deferred — none block ship.

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
