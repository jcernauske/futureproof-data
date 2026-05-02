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

---

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
