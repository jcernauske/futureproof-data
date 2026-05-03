# Feature: Explain-Stat Receipt — ROI, RES, GRW (Reuse the ERN Path)

## Claude Code Prompt

```
Read the spec at docs/specs/feature-explain-stat-receipt-roi-res-grw.md in
its entirety. The architectural pattern is already established by
docs/specs/feature-explain-stat-receipt.md (ERN, COMPLETE on this branch);
this spec extends that path to ROI, RES, and GRW. No schema changes — the
existing ExplainStatReceipt Pydantic model fits all three as-is.

Execute the following workflow:

1. IMPLEMENTATION
   - Implement the spec as written in §4 (Technical Spec). §3 reuses the
     ERN spec's <ExplainStatReceipt> component verbatim — no per-stat
     visual variants other than the stat-color rail (which is already
     parameterized via `payload.stat_code`).
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly.
   - DURING coding: Update tests listed in "Authorized Test
     Modifications" only. Every other failure is STOP-and-escalate.
   - Log all work to §6.
   - Run backend (ruff + mypy + pytest) and frontend (tsc + vitest).
   - BUILD ACCOUNTABILITY: max 3 attempts before escalating via §10.

2. TESTING
   - Invoke @test-writer to review the spec and add coverage from §4.
   - The three new appendices, the three new label allowlists, the three
     new postprocessors, and the per-stat math-line renderers are P0.

3. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests.

4. VERIFICATION
   - Invoke @fp-builder to run full build verification.

5. COMPLETION
   - Update Status to COMPLETE and check off §1 Success Criteria.
   - Generate report to reports/feature-explain-stat-receipt-roi-res-grw-YYYY-MM-DD.md.

OUT OF SCOPE — REJECT as scope creep if a reviewer requests them:
  - AURA. Lives in feature-explain-stat-receipt-aura.md (separate spec
    because AURA's institution-level basis enum requires one additive
    root-level field on ExplainStatReceipt — anticipated by ERN spec
    Decision 10 v1.2).
  - Any change to the ExplainStatReceipt / StatComponent / ReceiptSource
    Pydantic models. The ERN spec verified the schema is generic across
    these four stats; this spec consumes the schema, it doesn't modify it.
  - New MCP tools. ROI uses get_career_paths (cost + earnings carried via
    program_career_paths); RES uses get_career_paths (raw stat_res +
    stat_hmn carried via program_career_paths); GRW uses
    get_occupation_data (employment_change_pct + the rounded grw_score).
    All three are already in _TOOLS allowlist.
  - Any change to compute_stat_roi, _blend_res, or compute_grw_score.
    Voice describes the formulas; it does not redefine them.
  - Removal of the markdown-spike fallback. Same deferral as the ERN
    spec — a future cleanup spec retires it once the JSON path is stable
    in production for ≥2 weeks across all four stats.
  - Backporting the structured-receipt path to non-stat scopes (boss,
    skill, build, branch, compare). Different problem domain.
```

---

## Status: COMPLETE

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
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
| Blocked By | — (ERN spec is COMPLETE pending manual smoke; this spec ships after ERN's smoke verification) |
| Related Specs | `docs/specs/feature-explain-stat-receipt.md` (the ERN spec — required reading; this spec consumes its Pydantic models, gemma_client kwarg, frontend component, and §3 visual treatment verbatim); `docs/specs/pentagon-stat-reshape.md` (HMN→AURA + blended RES — RES voice in this spec describes the post-reshape blend); commit `f06fa6e refactor(cost): switch ROI + Loans Boss to published 4yr COA (sticker), kill debt_median fallback` (the cost anchor that ROI's voice in this spec describes — `published_cost_4yr` is the canonical cost basis, NOT `net_price × 4`) |
| Related References | `.claude/skills/pentagon-stat-explanation/SKILL.md` Step 5b (voice authority — the ROI/RES/GRW worked examples become the calibration material in each stat's system appendix); `docs/reference/stat-display-surfaces.md` (surface index — §1a/§1b legend triggers gain ROI/RES/GRW wiring; §1i gains three new entries) |

---

## §1 Feature Description

### Overview

Extend the structured `ExplainStatReceipt` JSON-mode path (built for ERN in `feature-explain-stat-receipt.md`) to **ROI, RES, and GRW**. The architecture, schema, fallback path, and frontend component are reused as-is. This spec authors three per-stat appendices (formula descriptions, voice calibration, sentinel-passthrough prohibition), three per-stat label allowlists, three per-stat postprocessors, and three per-stat math-line renderers. No schema changes, no new MCP tools, no formula changes.

### Problem Statement

The ERN explain-receipt feature ships with a load-bearing claim in §1 Success Criterion #11 of that spec: *"The `ExplainStatReceipt` schema fits ERN, ROI, RES, and GRW in future specs without breaking-change additions to the Pydantic model."* This spec is the proof. Until ROI, RES, and GRW also render structured receipts, the four stat rows on `BuildResultsScreen` are inconsistent: ERN's "✦ Explain this to me" link returns a typed receipt with server-owned math; the other four return either nothing wired or, post-AURA, a free-form Gemma prose blob with the same arithmetic risks the ERN spike exhibited.

The data shape per stat:

| Stat | Components in receipt | Per-component data | Server-owned numeric fields |
|------|----------------------|--------------------|----------------------------|
| ROI | 1 | DTE bucket: `weight_pct=100`, `value_pct=null` (DTE is a ratio, not a percentile rank), `anchor_dollars=published_cost_4yr / 4 × 4 = published_cost_4yr` for the "cost over 4 years" anchor. | `score`, `math_line` (DTE bucket form), `value_pct=null`, `anchor_dollars`, `missing_reason` |
| RES | 2 (50/50) | AI exposure piece: `weight_pct=50`, `value_pct = round(raw stat_res × 10)`, no dollar anchor. Human-essential piece: `weight_pct=50`, `value_pct = round(raw stat_hmn × 10)`, no dollar anchor. | `score`, `math_line` (`0.5 × A + 0.5 × B → score N/10`), per-component `value_pct`, `missing_reason` |
| GRW | 1 | Employment-change band: `weight_pct=100`, `value_pct = bucketed-percentile-derived`, `anchor_dollars=null` (no dollar figure for growth), `anchor_text` carries the percent-change phrase ("+15% over the next decade"). | `score`, `math_line` (band form: `+15% employment change → score 8/10`), `value_pct`, `missing_reason` |

The ERN spec already proved the parts: server-stamped score, server-built math line, sentinel-passthrough rejection, label-allowlist normalization, cached-tool-log fallback, synthesis-turn-only JSON-mode scoping. This spec wires those parts to three more stat dispatches.

### Success Criteria

- [x] Clicking "✦ Explain this to me" on the ROI row of `BuildResultsScreen` opens the slide-in chat, fires `[explain-this:ROI]`, streams one tool-call event (`get_career_paths`), and renders an `<ExplainStatReceipt>` with `stat_code="ROI"`, the green ROI rail, a single 100% component (DTE bucket), the COA cost anchor in the explainer, and the bucketed math line `published_cost_4yr / earnings_1yr_median = X.YZ → ROI score N/10`.
- [x] Clicking the RES row fires `[explain-this:RES]`, streams `get_career_paths` (which already carries the raw row scores via `program_career_paths`), and renders a 2-component receipt with the 50/50 AI-exposure + human-essential split. Math line: `0.5 × A + 0.5 × B → score N/10`.
- [x] Clicking the GRW row fires `[explain-this:GRW]`, streams `get_occupation_data`, and renders a 1-component receipt anchored on `employment_change_pct`. Math line: `+15% employment change → GRW score 8/10` (band form, not weighted-blend form).
- [x] All three receipts honor the sentinel-passthrough rejection (`_reject_sentinel_passthrough` validator on every prose field — already shipped in the ERN path) and the label-allowlist normalization (per-stat allowlist replaces drifted Gemma labels with canonical strings, WARNING logged).
- [x] `score` is server-stamped from `build.career.stats.{roi,res,grw}` unconditionally; `math_line` is server-built from the tool-result inputs unconditionally. Whatever Gemma emits in those fields is discarded. The Pydantic model already enforces this — this spec's `_postprocess_*_explain_receipt` helpers must implement it.
- [x] **Effort-shift coherence (Decision 13 of the ERN spec) applies to ROI ONLY.** RES and GRW are not effort-shifted (`_apply_effort` in `stat_engine.py:124-135` only touches ERN; the EFFORT_SHIFT comment explicitly excludes ROI from the legend description, but check the actual code path — the comment is aspirational about "ROI effort-excluded" but only ERN is shifted in the implementation today). Verify in §4 Service Changes which stats are effort-shifted before authoring per-stat math-line renderers; surface an effort line ONLY for stats that are actually shifted by `_apply_effort`.
- [x] Per-parse structured log records (call_site `"explain_roi_receipt"`, `"explain_res_receipt"`, `"explain_grw_receipt"`) appear in `logs/gemma.jsonl` so the per-stat parse-success rate is computable from the same log filter pattern the ERN spec established.
- [x] Both `INFERENCE_BACKEND=ollama` and `INFERENCE_BACKEND=openrouter` produce valid JSON receipts for all three stats under temperature 0, with JSON mode applied **only on the final synthesis turn** (Decision 15 of the ERN spec — already wired into `gemma_client.generate_with_tools_loop`'s `final_turn_response_format` kwarg). Manual smoke verification on each backend before VERIFICATION marks green. *Deferred to human run, same as ERN.*
- [x] `docs/reference/stat-display-surfaces.md` §1i gains three new entries (ROI, RES, GRW) tagged ✅ alongside ERN. §1a (pentagon legend) and §1b (pentagon chart axis label) gain notes that the explain-this affordance is wired for all four percentile-rank stats; AURA stays ⚠️ until the AURA spec ships.
- [x] No regressions to the ERN explain-receipt path. The ERN postprocessor, ERN appendix, ERN label allowlist, and ERN-specific tests remain untouched.

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | **Per-stat dispatch via a `_STAT_EXPLAIN_REGISTRY: dict[StatCode, _StatExplainConfig]` table.** Each entry carries: the appendix template constant, the label allowlist, the postprocessor helper, the math-line renderer, the call-site log key, and the trigger sentinel. The dispatch in `chat_ask` and `chat_ask_stream` switches on the sentinel's stat code and looks up the config. | Three sibling stat extensions deserve a single dispatch table, not three parallel `if explain_ern: ... elif explain_roi: ...` chains. The ERN spec authored a one-stat path that's safe to ship as-is, but extending it to four stats by copy-paste produces a maintenance disaster (every Decision 13 / Decision 14 / Decision 15 fix would have to be applied four times). The registry pattern is the cleanest way to keep the ERN code path intact while adding three siblings. | (a) Inline `if/elif` chain per stat. Rejected — quadratic maintenance cost; one-stat changes to the ERN spike code already proved this when fp-architect's review surfaced the cascade. (b) A class hierarchy (`StatExplainer` ABC with `ERNExplainer`, `ROIExplainer`, etc.). Rejected — over-engineered for four implementations; the registry pattern fits the data shape (config + functions) without inventing inheritance. (c) Per-stat modules (`ask_gemma_ern.py`, `ask_gemma_roi.py`, ...). Rejected — splits a tightly-coupled domain across files; the appendices and postprocessors share helpers (sentinel rejection, label normalization, log writers) that would either duplicate or require a shared base module anyway. |
| 2 | **The ERN code path stays where it is, then gets refactored INTO the registry as the first entry.** First commit: introduce the registry with the ERN entry; verify ERN still passes all existing tests; only then add ROI, RES, GRW. | Migrating ERN to the registry as the same commit that adds three new stats would mix risk. Splitting the work means the ERN-only refactor is reviewable in isolation, the three new stats land cleanly, and any regression in the registry refactor surfaces against the ERN test suite first (which is the most thorough). | (a) Add ROI/RES/GRW alongside the existing ERN code path as parallel dispatch arms; refactor later. Rejected — locks in the cascade Decision 1 wants to avoid, and "later" doesn't ship. (b) Bigger-bang: registry + four stats in one commit. Rejected — review surface too large to keep coherent. |
| 3 | **ROI is rendered as a single 100% DTE-bucket component, NOT as a 2-component "cost vs. earnings" split.** The single component's `label = "your debt-to-earnings ratio"`, `weight_pct = 100`, `value_pct = null` (DTE is a ratio, not a percentile rank — Pydantic allows null per the existing schema), `anchor_dollars = published_cost_4yr` (the cost over 4 years, residency-adjusted), and `anchor_text = "Indiana University Computer Science 4-year published cost"`. The math line shows the bucket form: `published_cost_4yr / earnings_1yr_median = 1.42 → ROI score 4/10`. | The ROI formula in `compute_stat_roi` (`src/gold/futureproof_engine.py:92`) is a piecewise-linear map from a single DTE input. Splitting it into "cost piece" and "earnings piece" would invent a structure that isn't in the formula — the bucket lookup IS the math. The single-component receipt mirrors the formula honestly. | (a) Two components: `weight_pct=50` cost, `weight_pct=50` earnings. Rejected — it's not a weighted blend; it's a ratio mapped through a bucket table. The visualization would be lying about the mechanism. (b) Skip the component entirely, render only the math line. Rejected — the receipt's information architecture (component bullets explain WHAT goes into the score) is the moat; ablating the section for ROI alone breaks visual consistency across stats. (c) Render the bucket table itself as the components. Rejected — bucket-table-as-component is structurally what GRW does (band membership), but ROI's piecewise-linear interpolation produces a continuous score, so band membership isn't a clean fit. |
| 4 | **ROI's anchor uses `published_cost_4yr` (full sticker, residency-adjusted), NOT `net_price_annual × 4`.** The postprocessor reads `build.career.published_cost_4yr` directly — the value is already computed by `stat_engine._published_cost_4yr` at build time using the student's `home_state` for residency determination. The postprocessor does NOT recompute from raw MCP tool fields (`cost_of_attendance_annual`, `tuition_in_state`, etc.) because `home_state` is session-level context on the Build object, not in the MCP response. Reading from the build guarantees the receipt's cost anchor matches the score. | Per `stat_engine.py:178-180` the cost basis for ROI and the Student Loans Boss switched to `_published_cost_4yr` on 2026-05-02 with the explicit comment "net_price/debt_median are no longer used." Echoing the legacy net-price anchor in the ROI explainer would directly contradict the shipped formula and create a "the math doesn't add up" failure mode of the same shape that motivated the ERN spec. | (a) Show net_price for context as a sub-line. Rejected per `feedback_single_source_cost`: "net_price_annual must carry the student's actual cost; never use sidecar adjusted fields" — for ROI display, the sticker IS the actual cost; net price is a separate concept. (b) Show both costs and let the student decide. Rejected — explainers exist to make the math legible, not to surface every available number. (c) Use `debt_median × 4` as a fallback when published_cost_4yr is null. Rejected — the cost-anchor refactor explicitly killed this fallback (commit `f06fa6e` "kill debt_median fallback"). When published_cost_4yr is null, the receipt's cost component renders as missing-data (open-ring + missing_reason) just like a missing percentile. (d) Recompute `_published_cost_4yr` from raw MCP tool fields at receipt time. Rejected — `home_state` is not in the MCP response; the build already carries the canonical computed value; recomputing introduces divergence risk. |
| 5 | **RES is rendered as a 2-component 50/50 receipt: AI exposure (`stat_res`-derived percentile) + human-essential (`stat_hmn`-derived percentile).** The components carry `weight_pct=50` each. `value_pct` for each component is computed server-side from the raw `stat_res` / `stat_hmn` integers (1-10, read from the `get_career_paths` MCP tool response, NOT from the build's blended `stats.res`): `value_pct = stat_res × 10` (e.g., `stat_res=8 → value_pct=80`). The math line shows `0.5 × 8 + 0.5 × 7 → score 8/10` (the actual blend per `_blend_res`). **Partial-null behavior:** `_blend_res` returns the single available value when one input is None (e.g., `stat_hmn=7` with `stat_res=None` → `res=7`). The receipt must show the raw inputs honestly — `0.5 × n/a + 0.5 × 7 → score 7/10` — not hide the missing signal. | The post-reshape blend in `stat_engine._blend_res` averages the two raw row scores (`stat_res` from Karpathy/Anthropic AI exposure; `stat_hmn` from O*NET human-essential signals). The receipt mirrors the formula 1:1: two components, equal weight, half-up rounding visible in the math line. The voice from SKILL Step 5b RES section becomes the calibration material in the appendix — Registered Nurse hits high on both, Bookkeeper hits low on both. | (a) Show the blend as a single component with `value_pct=res_score`. Rejected — it would hide the structural fact that RES is a *blend*, which is the whole pedagogical move (the SKILL voice example for RES leans hard on "we blend two signals because they measure related-but-different things"). (b) Three components (Karpathy / Anthropic / O*NET separately). Rejected — the data pipeline already collapses Karpathy + Anthropic + Gemma composite into a single `stat_res`; the receipt should mirror what the formula does, not the source datasets that fed the formula. (c) Show the blend with a 60/40 weight (tilting toward AI exposure). Rejected — the formula is 50/50 today (`_blend_res`'s docstring is explicit: "DRAFT 50/50 mean of the two AI-resilience signals"); voice describes the formula, doesn't redesign it. |
| 6 | **GRW is rendered as a single 100% employment-change-band component, NOT a percentile.** `weight_pct=100`, `value_pct=null` (the GRW score isn't derived from a percentile rank; it's piecewise-linear-mapped from the raw percent-change), `anchor_dollars=null` (no dollar figure), `anchor_text` carries the percent-change phrase (e.g., "+15% projected employment change over the next decade"). The math line shows the band form: `+15% employment change → GRW score 8/10` (NOT `0.6 × X + 0.4 × Y → ...`). | Per `compute_grw_score` (`src/gold/bls_ooh_occupation_profiles.py:67`) the GRW formula is a piecewise-linear map from a single input — `employment_change_pct`. Same structural argument as ROI: one input, one bucket, one score. The math line's band form is honest about the mechanism; the components list still has one entry because the receipt's information architecture is "what feeds the score," not "what's blended." | (a) Two components: "current employment" (LongType `employment_current`) + "projected employment" (LongType `employment_projected`), with delta computed by the renderer. Rejected — the formula doesn't multiply by the levels; it operates on the percent change. The components would be lying about the mechanism. (b) Show the bucket table itself in the receipt as inline content (not a component). Rejected — the bucket table belongs in the optional "Why this design" voice paragraph if anywhere; cluttering the math line with the full table reads as documentation, not a receipt. |
| 7 | **Per-stat appendix templates live as separate constants per stat, not parameterized template strings.** `_ROI_RECEIPT_JSON_TEMPLATE`, `_RES_RECEIPT_JSON_TEMPLATE`, `_GRW_RECEIPT_JSON_TEMPLATE` (mirrors `_RECEIPT_JSON_TEMPLATE` from the ERN spec, which becomes `_ERN_RECEIPT_JSON_TEMPLATE` during the registry refactor). Each template carries the per-stat filled-in JSON example with `__FILL_IN__` sentinels and the stat-specific voice rules inlined verbatim from SKILL Step 5b. | A parameterized template (e.g., `_make_appendix(stat_code: str, voice_example: str) → str`) would force the four stats' voice into a one-size-fits-all skeleton, defeating the SKILL's per-stat calibration. The four stats genuinely diverge on examples ("two students contrast" only fits ERN's blend; ROI's voice anchors on the cost-anchor refactor; RES leans on the "two signals measure related-but-different things" contrast; GRW leans on "10-year projection vs. past growth"). Separate constants let each appendix carry its own voice DNA. | (a) Single parameterized template. Rejected per the divergence above. (b) Templates loaded from disk (`appendices/roi.txt` etc.). Rejected — adds file-loading machinery for no benefit; constants in `ask_gemma.py` are tracked, type-checked, and grep-able. |
| 8 | **Per-stat label allowlist constants** mirror the ERN spec's `_ERN_LABEL_ALLOWLIST` shape. ROI: `{100: "your debt-to-earnings ratio"}`. GRW: `{100: "this career's projected employment change"}`. RES: a list-keyed allowlist `[(50, "AI exposure"), (50, "human-essential skills")]` (NOT a dict — two 50% components can't be keyed on weight alone, and Gemma may swap the components order). The RES `_normalize_label` function takes the position index (0 or 1) plus the gemma_label and the canonical-by-position list, and matches first by position, then by nearest-string-distance against the canonical list, then logs a WARNING with both values. The position-first match implicitly catches the swap-component case (RES has a stable convention: index 0 = AI exposure, index 1 = human-essential). | The ERN allowlist's match-by-weight strategy works because ERN has two distinct weights (60 and 40). RES has two identical weights (50 and 50), so matching by weight is ambiguous. The position-based allowlist exploits the JSON list's stable order — Gemma may swap the labels but it can't swap the positions without re-emitting `weight_pct` (which the allowlist also matches against, defensively). | (a) Single canonical RES allowlist with both labels and a similarity-only match. Rejected — produces label drift on the swap case (Gemma puts the AI-exposure label at index 1 and human-essential at index 0; receipt renders with both labels swapped relative to the actual percentile data). (b) Force a deterministic order in the appendix prompt and reject any other order. Rejected — too brittle; benign label paraphrases would fall back to markdown for no real-world reason. (c) Single dict keyed on weight with a list of acceptable labels as the value. Rejected — same ambiguity as (a) since both keys are 50. |
| 9 | **None of ROI, RES, or GRW are effort-shifted; none of their math-line renderers accept an `effort` parameter.** | Per `stat_engine._apply_effort` (line 124-135) the effort slider only shifts ERN. Verified 2026-05-02: `_apply_effort` modifies only `stats.ern`; ROI/RES/GRW are passed through unchanged. No effort parameter is plumbed into any of the three new renderers — YAGNI. If a future spec extends effort to another stat, add the parameter at that time. | (a) Plumb `effort` defensively into `_render_math_line_roi` as dead code. Rejected — dead parameters invite misuse and confuse readers. (b) Wire the effort line for all three stats defensively. Rejected — introduces visible UI for behavior that doesn't fire. |
| 10 | **`extra="forbid"`, sentinel-passthrough rejection, and `_extract_json_objects`-first parsing all carry over from the ERN spec verbatim.** Each per-stat postprocessor (`_postprocess_roi_explain_receipt`, etc.) follows the same 10-step pipeline as `_postprocess_ern_explain_receipt`: extract → loads → validate → assert stat_code matches → check build score not None → server-stamp score → server-build math_line → normalize labels → server-stamp per-component data → log structured record. | The whole architectural value of the ERN spec is the 10-step pipeline. Diverging from it per stat re-opens every failure mode the ERN review surfaced (sentinel passthrough, score divergence, label drift, swallowed JSON-mode parse failures). The pipeline is the contract. | (a) Per-stat divergent pipelines optimized for each formula's quirks. Rejected — multiplies the test surface and review burden by 4x for no real-world gain. (b) Single shared `_postprocess_explain_receipt(stat_code, build, tool_call_log) -> ExplainStatReceipt | None` that switches internally. Considered — could collapse the four postprocessors into one; promote during implementation if the per-stat differences are thinner than expected. The current decision is "four parallel postprocessors that share helpers"; if the differences shake out to 5 lines per stat, refactor to one. |

### Constraints

- **Cost anchor for ROI is `published_cost_4yr`, not `net_price × 4`.** Per the `feedback_single_source_cost` memory, `net_price_annual` must carry the student's actual cost; for the explainer-receipt surface the published sticker IS the cost basis (per commit `f06fa6e` and `_published_cost_4yr` in `stat_engine.py:245`). No sidecar adjusted fields.
- **No data-pipeline changes.** Same constraint as the ERN spec. ROI reads `published_cost_4yr` and `earnings_1yr_median` directly from the `Build` object (already computed by `stat_engine._published_cost_4yr` at build time). RES reads `stat_res` and `stat_hmn` from the MCP `get_career_paths` response (both are stored columns in `consumable.program_career_paths`). GRW reads `employment_change_pct` from the MCP `get_occupation_data` response (stored in `consumable.occupation_profiles`).
- **No new MCP tools.** ROI uses `get_career_paths` (which returns the cost components and earnings via the `program_career_paths` join). RES uses `get_career_paths` (which surfaces `stat_res` and `stat_hmn` raw row scores). GRW uses `get_occupation_data` (which surfaces `employment_change_pct` and the rounded GRW score). All three are already in the `_TOOLS` allowlist for chat-time calls.
- **No formula changes.** This spec describes the formulas; it does not redefine them. Any change to `compute_stat_roi`, `_blend_res`, `compute_grw_score`, or the cost anchor is OUT OF SCOPE and routes through a different spec.
- **No removal of the ERN spec's helpers.** `_postprocess_ern_explain_receipt`, `_render_math_line` (renamed to `_render_math_line_ern` during the registry refactor), `_normalize_label`, `_log_receipt_parse`, `_extract_json_objects` — all stay. The registry refactor MOVES the ERN-specific helpers (template constant, allowlist, postprocessor, math-line renderer) into the registry; it does NOT delete them.
- **Voice authority remains the SKILL.** Each per-stat appendix inlines the relevant voice rules from `pentagon-stat-explanation/SKILL.md` Step 5b verbatim (Gemma has no SKILL access at inference time). Schema and voice stay decoupled — the schema dictates structure, the SKILL dictates the words.
- **JSON-mode synthesis-turn-only scoping (Decision 15 of the ERN spec) applies to all three stat dispatches.** The `final_turn_response_format={"type":"json_object"}` kwarg is passed to `gemma_client.generate_with_tools_loop` for each per-stat dispatch; per-backend translation (OpenRouter `response_format` verbatim, Ollama native `format: "json"`) is already wired into the tool loop and needs no per-stat work.

### Out of Scope

| Item | Park as |
|------|---------|
| AURA explain-receipt | `docs/specs/feature-explain-stat-receipt-aura.md` (separate spec — additive `score_provenance` root field on the schema) |
| Schema changes to `ExplainStatReceipt` / `StatComponent` / `ReceiptSource` | Out — the ERN spec verified the schema is generic across these four stats |
| New MCP tools | Out — existing tools cover the data |
| Formula changes (`compute_stat_roi`, `_blend_res`, `compute_grw_score`) | Out — separate spec if ever needed |
| Removal of the markdown-spike fallback | Future cleanup spec after ≥2 weeks of stable production usage across all four stats |
| Backporting structured receipts to non-stat scopes (boss, skill, build, branch, compare) | Different problem domain. Future specs only if the design pattern proves out for stats. |
| Localization of the math-line strings | Out for v1.0. The English strings are server-rendered; a `Locale` parameter to each `_render_math_line_*` is the obvious extension point. |
| Effort-line for non-ERN stats | Out — `_apply_effort` only shifts ERN (verified 2026-05-02, Decision 9). Revisit if a future spec extends effort to ROI or others. |

---

## §3 UI/UX Design

> **SKIPPED — visual treatment fully inherited from `feature-explain-stat-receipt.md` §3.**

The `<ExplainStatReceipt>` React component built for ERN already parameterizes on `payload.stat_code`:

- The 3px stat-color left rail reads `var(--color-stat-{stat_code.toLowerCase()})` — automatically green for ROI, blue for RES, red for GRW (per the existing `STAT_COLORS` map in `frontend/src/components/build-results/bossData.ts`).
- The score-callout number is rendered in the same stat color via the same CSS variable.
- The component-row weight chip uses the stat-color tint background pattern from the ERN spec, parameterized identically.
- The component count adapts: ROI/GRW receipts render 1 component; RES renders 2 (50/50). The existing `<ul>` + `<li>` enumeration in `<ExplainStatReceipt>` handles both length-1 and length-2 component lists without modification — the stagger animation already keys off the list length.
- Missing-data treatment (open-ring `◦ —` glyph + dimmed row + italic missing-reason) applies identically when a per-component value is null. ROI specifically can have `value_pct=null` always (DTE is a ratio, not a percentile) — the renderer must NOT show the "open-ring + em-dash" missing-data glyph in the percentile callout slot for components that legitimately carry `value_pct=null` by design (vs. by missing data). **This requires one small renderer change:** when `value_pct === null` AND `missing_reason === null`, suppress the percentile-callout row entirely instead of rendering the missing-data glyph. ROI's component shows only the dollar-anchor row (`anchor_dollars` formatted). GRW's component shows only the percent-change anchor in `anchor_text`. See §4 File Changes.

The math-line inset card, sources pill row, why-mix paragraph, skeleton loading, and accessibility attributes are all reused without per-stat customization. The only per-stat axis is the math-line *string content*, which the server builds — the renderer never inspects the math expression's structure.

### One renderer change required

| Concern | Today (ERN) | After this spec |
|---|---|---|
| Component row with `value_pct === null` AND `missing_reason === null` | Renders the open-ring + em-dash glyph (because the ERN path's only null-value-pct case is the missing-data branch) | Suppress the percentile-callout row entirely; render only the `anchor_text` and `anchor_dollars` (if present) below the explainer prose. The component is intentionally non-percentile, not missing. |
| Component row with `value_pct === null` AND `missing_reason !== null` | Existing missing-data treatment (dim row + open-ring + italic missing-reason note) | Unchanged. |

Visual examples:

ROI (1 component, value_pct=null by design, anchor_dollars present):

```
┌─────┐  Your debt-to-earnings ratio
│ 100%│  Indiana University Computer Science published cost over four
└─────┘  years is $112,400 (in-state sticker). Software Developer grads
         from this program earn a median of $78,400 within a year. That
         puts your debt-to-earnings ratio at 1.43 — every $1.43 of
         schooling cost weighs against $1.00 of starting pay.

         $112,400 cost  ·  $78,400 starting pay
```

RES (2 components, both value_pct populated as integers from the raw row scores):

```
┌─────┐  AI exposure
│ 50% │  Software Developers score 8/10 on the AI-exposure side — the
└─────┘  task profile is highly automatable on its surface, but the
         (...explainer continues...)

         AI-exposure rating: 8/10

┌─────┐  Human-essential skills
│ 50% │  On the human-essential side (from the federal Occupational
└─────┘  Information Network, or O*NET) Software Developers score 7/10
         — the work depends on judgment and collaboration in ways that
         resist automation.

         Human-essential rating: 7/10
```

GRW (1 component, value_pct=null, anchor_text carries the percent change):

```
┌─────┐  This career's projected employment change
│ 100%│  The Bureau of Labor Statistics expects Software Developer
└─────┘  jobs to grow about 15% over the next decade — that's strong
         growth (their classification: "Much faster than average").

         +15.2% projected change over 10 years
```

Math-line treatment per stat (the string the server emits):

| Stat | Balanced effort math line | Non-balanced (effort line below, ROI only — but see Decision 9) |
|---|---|---|
| ROI | `$112,400 / $78,400 = 1.43  →  ROI score 4/10` | (effort line not emitted today; reserved if `_apply_effort` ever shifts ROI) |
| RES | `0.5 × 8 + 0.5 × 7  →  score 8/10` | n/a |
| GRW | `+15.2% employment change  →  GRW score 8/10` | n/a |

The math-line inset card's `bg-bp-mid` recessed treatment, U+2192 arrow, and `font-data` typography are unchanged.

### What is NOT changing

- No new design tokens. No new font roles. No new color values. The receipt is composed entirely from the existing Brightpath primitives the ERN spec specified.
- No new accessibility attributes. The `aria-label` patterns generalize: `"Earning Power explanation receipt"` becomes `"Return on Investment explanation receipt"` etc., driven by `payload.stat_name`.
- No new motion presets. Stagger, mount, score-appear, source-pill hover all carry over.

### Stat-display surface index updates

`docs/reference/stat-display-surfaces.md` gains:

- §1a (pentagon legend): note that the explain-this affordance now wires for ERN, ROI, RES, GRW (AURA still gated on its separate spec).
- §1b (pentagon chart axis label): same — when the user clicks the ROI/RES/GRW axis label, the explain-this dispatch fires.
- §1f (FinancesCard ROI receipt): note that the ROI explain-this affordance is now wired and dispatches the same JSON-mode path.
- §1i: three new entries (one per stat) following the same shape as the existing ERN entry.

---

## §4 Technical Specification

### Architecture Overview

This spec adds three sibling stat dispatches to the explain-receipt path that the ERN spec built. The shape is:

1. A new `_StatExplainConfig` dataclass in `backend/app/services/ask_gemma.py` carries: the appendix template constant, the label allowlist, the postprocessor callable, the math-line renderer callable, the call-site log key, and the trigger sentinel.
2. A new `_STAT_EXPLAIN_REGISTRY: dict[Literal["ERN", "ROI", "RES", "GRW"], _StatExplainConfig]` table is the dispatch source-of-truth. The first commit of this spec migrates the existing ERN code path INTO the registry as the first entry; subsequent commits add the three new entries.
3. The `chat_ask` and `chat_ask_stream` sentinel detection in `ask_gemma.py` is rewritten to switch on the sentinel's stat code (e.g., `[explain-this:ROI]` extracts `"ROI"`) and look up the config in the registry. The dispatch is identical to the ERN spec's pattern: append the appendix to the system prompt, call `gemma_client.generate_with_tools_loop` with `final_turn_response_format={"type":"json_object"}`, capture the `tool_call_log`, run the per-stat postprocessor, fall back to the markdown-spike path on parse failure with the cached tool log injected.
4. Three new postprocessors (`_postprocess_roi_explain_receipt`, `_postprocess_res_explain_receipt`, `_postprocess_grw_explain_receipt`) each implement the same 10-step pipeline as the ERN postprocessor with stat-specific math-line construction and per-component data extraction. Each postprocessor reads from the `tool_call_log`'s captured tool-result row and stamps `value_pct`, `anchor_dollars`, `missing_reason` per component.
5. Three new math-line renderers (`_render_math_line_roi`, `_render_math_line_res`, `_render_math_line_grw`) each produce the per-stat string with the U+2192 arrow and the `font-data` formatting expected by the receipt's inset card. Only `_render_math_line_roi` accepts an `effort` parameter (Decision 9), and only when `_apply_effort` is verified to shift ROI (which it does NOT today — so the parameter is plumbed but the formatting branch is dead code as of 2026-05-02; flagged in §6 implementation log).
6. Three new appendix template constants are filled-in JSON examples with `__FILL_IN__` sentinels (matching the ERN spec's `_RECEIPT_JSON_TEMPLATE` shape) and inlined SKILL voice rules for each stat.
7. Three new label allowlist constants (one dict, one list-keyed mapping for RES). The RES allowlist exposes a new `_normalize_label_by_position(idx, gemma_label, allowlist) -> tuple[str, bool]` helper alongside the existing `_normalize_label` (which stays for ERN/ROI/GRW dict-by-weight matches).
8. The frontend cascades from the ERN spec require ZERO additional changes for ROI/RES/GRW. The Zod parser at the SSE boundary already discriminates on `payload.kind === "receipt"` — it doesn't care which stat. The `<ExplainStatReceipt>` component already parameterizes on `payload.stat_code`. The only frontend touch is one renderer change (per §3 above) to suppress the open-ring percentile glyph when `value_pct === null` AND `missing_reason === null`.
9. The `BuildResultsScreen` "✦ Explain this to me" link is already wired for ERN. ROI, RES, GRW each get their own equivalent link on their respective legend rows. The trigger sentinel changes (`[explain-this:ERN]` → `[explain-this:ROI]` etc.); the chat-open + scope-set logic is reused.
10. The MCP tool surface is unchanged. ROI dispatches `get_career_paths` (one tool call, returns the cost columns and `earnings_1yr_median`). RES dispatches `get_career_paths` (returns `stat_res` and `stat_hmn` from `program_career_paths`). GRW dispatches `get_occupation_data` (returns `employment_change_pct` and the rounded score).

The fallback path is unchanged from the ERN spec. When any per-stat postprocessor returns None, the dispatch falls through to a markdown-spike retry with the cached tool log injected into the user message (no MCP re-fetch). The markdown-spike appendix today only exists for ERN; for ROI, RES, GRW, the markdown-fallback's appendix is a per-stat markdown template that mirrors the SKILL voice example for that stat (also stored as a constant per stat). On both backends (Ollama, OpenRouter), the synthesis-turn-only JSON-mode kwarg is already wired through `gemma_client.generate_with_tools_loop` and needs no per-stat work.

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/app/services/ask_gemma.py` | Modify | Major refactor: introduce `_StatExplainConfig` dataclass, `_STAT_EXPLAIN_REGISTRY`, dispatch rewrite. Add three new appendix templates (`_ROI_RECEIPT_JSON_TEMPLATE`, `_RES_RECEIPT_JSON_TEMPLATE`, `_GRW_RECEIPT_JSON_TEMPLATE`), three new label allowlists (`_ROI_LABEL_ALLOWLIST: dict[int, str]`, `_GRW_LABEL_ALLOWLIST: dict[int, str]`, `_RES_LABEL_ALLOWLIST: list[tuple[int, str]]`), three new postprocessors (`_postprocess_roi_explain_receipt`, `_postprocess_res_explain_receipt`, `_postprocess_grw_explain_receipt`), three new math-line renderers (`_render_math_line_roi`, `_render_math_line_res`, `_render_math_line_grw`), three new markdown-fallback appendix templates (one per stat, used only on JSON parse failure), and one new label normalizer (`_normalize_label_by_position` for RES). The existing ERN helpers move INTO the registry as the first entry but are not deleted. The `_HELPER_LEAK_RE` stripper continues to apply only to markdown-fallback paths. |
| `backend/app/services/ask_gemma.py` (sentinel detection) | Modify | Rewrite the sentinel detection block in `chat_ask` and `chat_ask_stream` to extract the stat code from `[explain-this:{STAT}]` and dispatch via `_STAT_EXPLAIN_REGISTRY`. The match must be exact: `[explain-this:ERN]`, `[explain-this:ROI]`, `[explain-this:RES]`, `[explain-this:GRW]` — anything else falls through to the existing free-form scope handler. AURA sentinels are deliberately NOT registered here; the AURA spec adds the registry entry. |
| `backend/tests/services/test_ask_gemma_explain_receipt.py` | Modify | Add three new test classes (`TestPostprocessROIExplainReceipt`, `TestPostprocessRESExplainReceipt`, `TestPostprocessGRWExplainReceipt`) mirroring the existing ERN test class structure. Each covers happy path, score-from-build override, math-line construction (per-stat shape), Pydantic-validation failures, sentinel passthrough on prose fields, label normalization (with the position-based RES variant), structured log records on success and failure, JSON extraction edge cases (markdown fence, trailing prose). |
| `backend/tests/services/test_ask_gemma.py` | Modify | Add per-stat sentinel-dispatch integration tests: `test_chat_ask_roi_explain_dispatches_via_registry`, `test_chat_ask_res_explain_dispatches_via_registry`, `test_chat_ask_grw_explain_dispatches_via_registry`. Each verifies the registry lookup hits the right config and the response payload is an `ExplainStatReceipt` with the correct `stat_code`. Plus three fallback tests confirming each per-stat path falls back to its markdown-fallback appendix when the postprocessor returns None, and the cached tool log is injected (no MCP re-fetch). |
| `backend/app/services/__init__.py` | Modify (only if exports change) | If the per-stat postprocessors are part of the package's public surface, re-export. Otherwise no-op. |
| `frontend/src/components/menu/ExplainStatReceipt.tsx` | Modify | One renderer change: in the component-row rendering, when `component.value_pct === null` AND `component.missing_reason === null`, suppress the percentile-callout row (no open-ring glyph, no em-dash, no callout line). Render only the `anchor_text` + `anchor_dollars` (if present). When `value_pct === null` AND `missing_reason !== null`, render unchanged (existing missing-data treatment). The change is gated on the missing-reason being null vs. populated — no new prop, no new variant. |
| `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | Modify | Add three test cases: `test_renders_roi_receipt_no_percentile_callout` (value_pct=null + missing_reason=null → no glyph, only anchor_dollars row), `test_renders_grw_receipt_no_percentile_callout` (same), `test_renders_res_receipt_with_two_components` (length-2 components list renders both rows with stagger). |
| `frontend/src/screens/BuildResultsScreen.tsx` | Modify | Add "✦ Explain this to me" trigger handlers for ROI, RES, GRW legend rows. Wire each to the existing `handleAskStat` pattern (already used by ERN). The sentinel string is parameterized by stat code: `` `[explain-this:${stat.toUpperCase()}]` ``. No new state shape; the existing chat-open logic carries the stat scope already. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | Modify | Add tests for the new triggers: clicking the ROI/RES/GRW explain link fires the sentinel with the correct stat code. |
| `docs/reference/stat-display-surfaces.md` | Modify | §1a, §1b, §1f get notes that ROI/RES/GRW explain-this is now wired (matching the ERN entry). §1i gains three new sub-entries (`§1i.roi`, `§1i.res`, `§1i.grw`) following the ERN entry's shape: file, when-it-shows, what-user-sees, affordance, spec, schema. |
| `.claude/skills/pentagon-stat-explanation/SKILL.md` | Modify | Add a line under "Companion reference" pointing to the per-stat appendix templates in `ask_gemma.py` as the rendering authority for ROI/RES/GRW receipts, alongside the existing ERN pointer. The voice rules stay where they are. |

### Data Model Changes

**No schema changes.** The ERN spec's `ExplainStatReceipt`, `StatComponent`, and `ReceiptSource` Pydantic models in `backend/app/models/api.py` are reused as-is. This spec consumes them; it does not modify them.

The existing models support all three stats:

- `stat_code: Literal["ERN", "ROI", "RES", "GRW", "AURA"]` — already includes ROI, RES, GRW.
- `components: list[StatComponent]` with `min_length=1, max_length=5` — accommodates ROI's 1, RES's 2, GRW's 1.
- `StatComponent.value_pct: int | None` — null is valid for ROI's DTE-bucket and GRW's employment-change-band components (which are not percentile-rank-based).
- `StatComponent.anchor_dollars: int | None` — null is valid for RES (no dollar figure for AI exposure or human-essential signals) and GRW (no dollar figure for growth).
- `StatComponent.anchor_text: str` — required, used to carry "Indiana University Computer Science 4-year published cost" for ROI, "AI-exposure rating" / "Human-essential rating" for RES components, "+15.2% projected change over 10 years" for GRW.
- `StatComponent.missing_reason: str | None` — server-stamped when the underlying tool field is null. Per-stat canned strings (see Service Changes).
- `kind: Literal["receipt"] = "receipt"` self-discriminator — unchanged; ROI/RES/GRW receipts emit `kind: "receipt"` like ERN.
- `score: int = Field(ge=1, le=10)` — unchanged; server-stamped from `build.career.stats.{roi,res,grw}` per stat.
- `score_max: int = 10` — unchanged.
- `one_liner: str`, `why_mix_paragraph: str` (with `max_length=800`) — unchanged.
- The `_reject_sentinel_passthrough` field validator on every prose field — unchanged; applies automatically to ROI/RES/GRW receipts.

`AskResponse.response: str | ExplainStatReceipt` and `TraceFinalText.response: str | ExplainStatReceipt` — already widened by the ERN spec, no change needed.

### Service Changes

New helpers in `backend/app/services/ask_gemma.py`:

```python
from dataclasses import dataclass
from typing import Awaitable, Callable, Literal


@dataclass(frozen=True)
class _StatExplainConfig:
    """Per-stat dispatch config for the explain-receipt JSON path."""
    stat_code: Literal["ERN", "ROI", "RES", "GRW"]
    sentinel: str  # e.g. "[explain-this:ROI]"
    appendix_template: str  # filled-in JSON example with __FILL_IN__ sentinels
    label_allowlist: dict[int, str] | list[tuple[int, str]]
    postprocessor: Callable[
        [str, "Build", list["gemma_client.ToolCallTurn"]],
        Awaitable["ExplainStatReceipt | None"],
    ]
    markdown_fallback_appendix: str  # used when postprocessor returns None
    log_call_site: str  # e.g. "explain_roi_receipt"


# The dispatch source-of-truth. ERN entry migrates from the existing
# ask_gemma.py code path; ROI/RES/GRW added by this spec. AURA NOT
# registered here — added by docs/specs/feature-explain-stat-receipt-aura.md.
_STAT_EXPLAIN_REGISTRY: dict[
    Literal["ERN", "ROI", "RES", "GRW"], _StatExplainConfig
] = {
    "ERN": _StatExplainConfig(
        stat_code="ERN",
        sentinel="[explain-this:ERN]",
        appendix_template=_ERN_RECEIPT_JSON_TEMPLATE,  # renamed during refactor
        label_allowlist=_ERN_LABEL_ALLOWLIST,
        postprocessor=_postprocess_ern_explain_receipt,
        markdown_fallback_appendix=_ERN_MARKDOWN_FALLBACK_APPENDIX,
        log_call_site="explain_ern_receipt",
    ),
    "ROI": _StatExplainConfig(
        stat_code="ROI",
        sentinel="[explain-this:ROI]",
        appendix_template=_ROI_RECEIPT_JSON_TEMPLATE,
        label_allowlist=_ROI_LABEL_ALLOWLIST,
        postprocessor=_postprocess_roi_explain_receipt,
        markdown_fallback_appendix=_ROI_MARKDOWN_FALLBACK_APPENDIX,
        log_call_site="explain_roi_receipt",
    ),
    "RES": _StatExplainConfig(
        stat_code="RES",
        sentinel="[explain-this:RES]",
        appendix_template=_RES_RECEIPT_JSON_TEMPLATE,
        label_allowlist=_RES_LABEL_ALLOWLIST,
        postprocessor=_postprocess_res_explain_receipt,
        markdown_fallback_appendix=_RES_MARKDOWN_FALLBACK_APPENDIX,
        log_call_site="explain_res_receipt",
    ),
    "GRW": _StatExplainConfig(
        stat_code="GRW",
        sentinel="[explain-this:GRW]",
        appendix_template=_GRW_RECEIPT_JSON_TEMPLATE,
        label_allowlist=_GRW_LABEL_ALLOWLIST,
        postprocessor=_postprocess_grw_explain_receipt,
        markdown_fallback_appendix=_GRW_MARKDOWN_FALLBACK_APPENDIX,
        log_call_site="explain_grw_receipt",
    ),
}


# ROI: single 100% DTE-bucket component (Decision 3).
_ROI_LABEL_ALLOWLIST: dict[int, str] = {
    100: "your debt-to-earnings ratio",
}


# GRW: single 100% employment-change-band component (Decision 6).
_GRW_LABEL_ALLOWLIST: dict[int, str] = {
    100: "this career's projected employment change",
}


# RES: 2-component 50/50 blend, position-keyed (Decision 5 + Decision 8).
# Position 0 = AI exposure (stat_res-derived);
# Position 1 = human-essential (stat_hmn-derived).
_RES_LABEL_ALLOWLIST: list[tuple[int, str]] = [
    (50, "AI exposure"),
    (50, "human-essential skills"),
]


def _normalize_label_by_position(
    idx: int,
    gemma_label: str,
    allowlist: list[tuple[int, str]],
) -> tuple[str, bool]:
    """Match Gemma's label against the per-position canonical allowlist.

    Used for stats where multiple components share the same weight_pct
    (RES has two 50% components) — position is the disambiguator.
    Returns (canonical_label, was_normalized). Logs WARNING with both
    values when normalization fires.
    """


async def _postprocess_roi_explain_receipt(
    raw: str,
    build: "Build",
    tool_call_log: list["gemma_client.ToolCallTurn"],
) -> "ExplainStatReceipt | None":
    """Same 10-step pipeline as _postprocess_ern_explain_receipt, with
    ROI-specific math-line construction and per-component data extraction.

    Pipeline (10 steps; mirrors the ERN postprocessor):
      1. _extract_json_objects(raw) — strip markdown fences, brace-depth
         extract.
      2. json.loads on the extracted object. ValueError -> None.
      3. ExplainStatReceipt.model_validate(parsed). ValidationError -> None.
      4. Assert receipt.stat_code == "ROI". Mismatch -> None.
      5. If build.career.stats.roi is None -> None.
      6. Server-stamp receipt.score = build.career.stats.roi.
      7. Server-build receipt.math_line via _render_math_line_roi using
         values from the Build object (NOT recomputed from MCP tool
         fields — the build already carries the canonical values):
           - build.career.published_cost_4yr (residency-aware 4-year
             COA sticker, already computed by stat_engine._published_cost_4yr
             at build time using the student's home_state)
           - build.career.earnings_1yr_median
           - dte = published_cost_4yr / earnings_1yr_median
         When either input is null, the math-line shows "n/a" placeholders
         and the score stays from the build.
         NOTE: home_state is session-level context on the Build object,
         NOT in the MCP tool response. Reading published_cost_4yr from
         the build avoids recomputing with incomplete inputs and
         guarantees the receipt's cost anchor matches the actual score.
      8. Normalize the single component's label via _normalize_label
         against _ROI_LABEL_ALLOWLIST (match by weight_pct=100).
      9. Server-stamp the single component's value_pct=None,
         anchor_dollars=build.career.published_cost_4yr (the 4-year cost),
         anchor_text is left from Gemma (e.g. "Indiana University Computer
         Science 4-year published cost") — anchor_text is voice-owned, not
         server-stamped, but Pydantic validates the sentinel-passthrough.
         missing_reason is set to a canned ROI-specific string when
         the build value is null:
           - "no published cost data for this institution yet"
             (when build.career.published_cost_4yr is None)
           - "no median earnings reported for this program yet"
             (when build.career.earnings_1yr_median is None)
        10. _log_receipt_parse(call_site="explain_roi_receipt", ...).
    """


async def _postprocess_res_explain_receipt(
    raw: str,
    build: "Build",
    tool_call_log: list["gemma_client.ToolCallTurn"],
) -> "ExplainStatReceipt | None":
    """RES-specific 10-step pipeline.

    Per-stat differences from ERN:
      - stat_code asserted == "RES".
      - components list-length asserted == 2.
      - Raw ``stat_res`` and ``stat_hmn`` values are read from the
        ``get_career_paths`` MCP tool response (they are stored columns
        in ``program_career_paths``), NOT derived from
        ``build.career.stats.res``. This matters because ``_blend_res``
        has a partial-null rule: if one input is None it returns the
        other (e.g. stat_hmn=7 with stat_res=None → res=7). The receipt
        must show the raw inputs honestly — ``0.5 × n/a + 0.5 × 7 →
        score 7/10`` — not hide the missing signal.
      - Each component server-stamped from raw row scores:
          components[0].value_pct = stat_res * 10  (raw 1-10 -> 10-100)
          components[1].value_pct = stat_hmn * 10
        The * 10 conversion turns the raw 1-10 row score into the 0-100
        range that the StatComponent.value_pct field expects (per the
        Pydantic ge=0, le=100 constraint). When a raw score is null,
        the corresponding value_pct is None and missing_reason is set.
        The math line shows the raw values:
          0.5 × stat_res + 0.5 × stat_hmn → score N/10.
      - anchor_dollars=None for both components (no dollar figure).
      - anchor_text per component (voice-owned: "AI-exposure rating",
        "Human-essential rating").
      - Label normalization uses _normalize_label_by_position (NOT
        _normalize_label) because both components carry weight_pct=50.
      - Math line built via _render_math_line_res.
      - missing_reason canned strings: "no AI-exposure score available
        for this career yet" / "no human-essential score available for
        this career yet" when respective raw row scores are null.
      - log_call_site = "explain_res_receipt".
    """


async def _postprocess_grw_explain_receipt(
    raw: str,
    build: "Build",
    tool_call_log: list["gemma_client.ToolCallTurn"],
) -> "ExplainStatReceipt | None":
    """GRW-specific 10-step pipeline.

    Per-stat differences from ERN:
      - stat_code asserted == "GRW".
      - Single 100% component.
      - value_pct=None (employment change is a percent, not a percentile
        rank — the formula maps it through compute_grw_score's piecewise
        bucket).
      - anchor_dollars=None.
      - anchor_text carries the percent-change phrase: server formats
        from the tool result's employment_change_pct field (e.g.,
        "+15.2% projected change over 10 years").
      - Math line built via _render_math_line_grw — band form:
          "+15.2% employment change → GRW score 8/10".
      - Label normalization via _normalize_label match-by-weight=100.
      - missing_reason canned: "no 10-year employment projection
        reported for this occupation yet" when employment_change_pct is
        null.
      - log_call_site = "explain_grw_receipt".
    """


def _render_math_line_roi(
    *,
    published_cost_4yr: float | None,
    earnings_1yr_median: float | None,
    build_score: int,
    score_max: int,
) -> str:
    """Build ROI's math-line string.

    Format: '$112,400 / $78,400 = 1.43 → ROI score 4/10'

    Null-input behavior:
      - published_cost_4yr is None: show 'n/a / $X = n/a → score N/10'
      - earnings_1yr_median is None: show '$X / n/a = n/a → score N/10'
      - both None: 'n/a / n/a = n/a → score N/10'

    No effort parameter. _apply_effort does not shift ROI (Decision 9).
    If a future spec extends effort to ROI, add the parameter then.
    """


def _render_math_line_res(
    *,
    stat_res_raw: int | None,
    stat_hmn_raw: int | None,
    build_score: int,
    score_max: int,
) -> str:
    """Build RES's math-line string.

    Format: '0.5 × 8 + 0.5 × 7 → score 8/10'

    Null-input behavior:
      - stat_res is None: show '0.5 × n/a + 0.5 × Y → score N/10'
      - stat_hmn is None: show '0.5 × X + 0.5 × n/a → score N/10'
      - both None: '0.5 × n/a + 0.5 × n/a → score N/10'

    No effort parameter (Decision 9). RES is not effort-shifted.
    """


def _render_math_line_grw(
    *,
    employment_change_pct: float | None,
    build_score: int,
    score_max: int,
) -> str:
    """Build GRW's math-line string.

    Format: '+15.2% employment change → GRW score 8/10'
    Negative values: '-3.4% employment change → GRW score 4/10'.

    Null-input behavior:
      - employment_change_pct is None: 'n/a employment change → score N/10'

    No effort parameter (Decision 9). GRW is not effort-shifted.
    """
```

Each per-stat appendix template (constant) carries the filled-in JSON example with `__FILL_IN__` sentinels for prose fields and realistic numeric placeholders, the inlined SKILL Step 5b voice example for that stat (verbatim — Gemma has no SKILL access at inference time), and the explicit prohibitions:

- "Do NOT write 'N/10', 'your score is X', or any numeric score reference in any prose field. Score display is the UI's responsibility."
- "The strings `__FILL_IN__`, `[FILL_IN]`, `<FILL_IN>`, `ONE-SENTENCE DEFINITION HERE`, `PLACEHOLDER` are placeholders ONLY — replace them with your actual content. Echoing them back verbatim will fail validation."
- "Do not include `[helper: ...]` blocks, `<thinking>...</thinking>` blocks, or any meta-commentary."

The ROI appendix's voice section anchors on the cost-anchor refactor: *"This score divides the school's full 4-year published cost (sticker price, in-state for public schools when home_state matches the school's state, out-of-state when it doesn't) by your starting salary one year out. We use the published sticker, NOT the average aided net price, because at the exploration phase you don't know what aid you'll receive."*

The RES appendix's voice section anchors on the post-reshape blend: *"Two signals are mixed 50/50: AI exposure (a composite of Karpathy + Anthropic + Gemma scoring how automatable the work is) and human-essential ratio (from the federal Occupational Information Network, O*NET, scoring how much the work depends on judgment, social awareness, or physical presence). The blend hedges against either signal being too pessimistic or too generous on its own."*

The GRW appendix's voice section anchors on the BLS 10-year projection: *"This score reads BLS's 10-year employment-change projection — a forecast of how many more (or fewer) people will be working in this career a decade from now — and maps it through a bucket: -20% or worse is a 1, flat is 4-5, +10% is 7.5, +20% or better is 9-10. We use a projection (not past growth) because for a college decision you care about the world you'll *enter*, not the world you'd have entered in 2018."*

### Gemma-touching extra discipline

This spec adds three new explain-receipt dispatches that re-use the ERN spec's `gemma_client.generate_with_tools_loop` integration. The call-site discipline matches the ERN spec verbatim — the table here notes per-stat differences only.

| Concern | Behavior |
|---------|----------|
| Fallback when transport fails | Existing: empty string from the loop → `fallback_text("chat_unavailable", locale)` 200 response. Unchanged. |
| Fallback when JSON parsing fails | **Per-stat parallel to ERN.** Each per-stat postprocessor returns None on parse failure → `_log_receipt_parse(parse_success=False, ..., call_site=config.log_call_site)` → re-run the tool loop ONCE without `final_turn_response_format` and with the per-stat markdown-fallback appendix, **injecting the cached `tool_call_log` percentile/cost values into the markdown appendix's user message** so no MCP re-fetch happens. Caps total wait at ~10-15s per stat. |
| Fallback when both attempts fail | Same as ERN: existing spike-style fallbacks (turn-cap, wall-time) yield `chat_unavailable` 200. |
| `logs/gemma.jsonl` capture | Three records per call (matches ERN): JSON-mode tool loop's exchange record + structured `_log_receipt_parse` record + (on fallback) markdown loop's exchange record with `extra["fallback_after_json_parse_failure"] = True`. The `call_site` filter (`explain_roi_receipt`, `explain_res_receipt`, `explain_grw_receipt`) computes per-stat parse-success rates. |
| `INFERENCE_BACKEND=ollama` | The native Ollama `_one_tool_turn_ollama` path's `payload["format"] = "json"` translation is already wired (Decision 15 of the ERN spec). No per-stat work. |
| `INFERENCE_BACKEND=openrouter` | The OpenAI-compat `_one_tool_turn` path's `response_format` propagation is already wired. No per-stat work. |
| Tool-call mechanism preservation | `final_turn_response_format` synthesis-turn-only scoping is already wired into `_tools_loop_inner`. No per-stat work. |
| Concurrency for cloud demo | One JSON-mode call per "Explain this to me" click per stat, plus possibly one markdown-fallback call. Same Gemma semaphore limits as existing chat. No new contention. |
| Token-budget impact | Each per-stat appendix is similar in size to the ERN appendix (~600-900 tokens of output for the JSON receipt). The existing `max_tokens=1500` budget covers all four stats. The `why_mix_paragraph` `max_length=800` Pydantic constraint catches truncation as a validation failure → fallback fires. |

### Testing Impact Analysis

> **Search performed:** `rg "_postprocess_ern\|_RECEIPT_JSON_TEMPLATE\|_render_math_line\|_normalize_label\|_log_receipt_parse" backend/` — surfaces the ERN spec's helpers; this spec extends them.

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `backend/tests/services/test_ask_gemma_explain_receipt.py` | All `test_postprocess_*` (the ERN postprocessor tests) | Medium | The registry refactor MOVES the ERN helpers behind `_STAT_EXPLAIN_REGISTRY["ERN"].postprocessor` but does not change their behavior. Tests that import the helpers by name (`from backend.app.services.ask_gemma import _postprocess_ern_explain_receipt`) continue to work because the helper is still exported. Tests that exercise the dispatch path (e.g., `test_chat_ask_ern_explain_*`) continue to work because the dispatch is functionally identical (looks up the same callable via the registry). |
| `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_ern_explain_*`, `test_chat_ask_stream_ern_explain_*` | Medium | Same as above. The registry refactor is functional-no-op for ERN. |
| `backend/tests/services/test_gemma_client.py` | `test_final_turn_response_format_*`, `test_response_format_propagates_to_*` | Low | The kwarg semantics are unchanged. New per-stat dispatches use the same kwarg verbatim. |
| `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | All ERN rendering tests | Low | The renderer change (suppress percentile-callout when value_pct=null AND missing_reason=null) is gated on a state ERN never enters — ERN's components always have either a populated value_pct or a populated missing_reason. The renderer change is silent for ERN payloads. |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | `test_ern_explain_link_dispatches_sentinel` (or whatever the existing ERN trigger test is named) | Low | Adding ROI/RES/GRW triggers does not modify the ERN trigger. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `backend/tests/services/test_ask_gemma_explain_receipt.py` (the existing ERN test class) | Reorganize as a base test class with per-stat subclasses that inherit shared setup/teardown but override stat-specific fixtures. Optional refactor — only if the ROI/RES/GRW test classes share enough setup to warrant it. | Reduces duplication if shared. Skipped if the per-stat fixtures diverge enough that a shared base adds complexity. |
| `backend/tests/services/test_ask_gemma.py` (existing ERN sentinel-dispatch test) | Replace the direct dispatch-arm-check assertion with a registry-lookup assertion (`_STAT_EXPLAIN_REGISTRY["ERN"].postprocessor == _postprocess_ern_explain_receipt`). | The registry refactor changes the dispatch implementation; the test should target the registry, not the inline arm. |

#### Confirmed Safe

These tests must NOT break. If they fail, escalate per §10:

- All `test_chat_ask_boss_scope_*` / `test_chat_ask_skill_scope_*` / `test_chat_ask_build_scope_*` / `test_chat_ask_branch_*` / `test_chat_ask_compare_*` — non-stat scopes are untouched by this spec.
- `test_strip_thinking_prefix*`, `test_helper_leak_*` — helper utilities are unchanged.
- `test_voice_contract.py` — global voice rules are unchanged; the per-stat appendix rules are LOCAL to the per-stat dispatch turn.
- The full ERN explain-receipt test suite — the registry refactor must be functionally identical for ERN.
- All `frontend/src/components/menu/GemmaChat.test.tsx` discriminated-union rendering tests — receipt vs text dispatch is unchanged.
- All `frontend/src/api/menu.test.ts` Zod-parser tests — schema is unchanged; same parser handles ROI/RES/GRW receipts because they have the same `kind: "receipt"` discriminator.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_roi_postprocess_happy_path` | Valid Gemma JSON for ROI → parsed `ExplainStatReceipt` with `stat_code="ROI"`, single component (`weight_pct=100`, `value_pct=None`), math line shape `$X / $Y = Z.ZZ → ROI score N/10`. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_roi_postprocess_score_from_build` | Gemma emits `score: 99` → server overwrites with `build.career.stats.roi`. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_roi_postprocess_anchor_uses_build_published_cost_4yr` | The `anchor_dollars` field carries `build.career.published_cost_4yr` (already residency-adjusted at build time), NOT recomputed from MCP tool fields. Test fixture sets `build.career.published_cost_4yr` directly and asserts the receipt's anchor matches. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_roi_postprocess_published_cost_null` | `build.career.published_cost_4yr` is None → component's `anchor_dollars=None`, `missing_reason="no published cost data for this institution yet"`, math_line shows `n/a / $Y = n/a → score N/10`. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_roi_postprocess_earnings_null` | `build.career.earnings_1yr_median` null → component's data partial-set, math_line shows `$X / n/a = n/a → score N/10`. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_roi_postprocess_label_normalization` | Gemma emits `label="cost-to-earnings"` (off-script) → `_normalize_label` matches by weight=100 → replaces with canonical "your debt-to-earnings ratio" → WARNING logged. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_roi_postprocess_rejects_wrong_stat_code` | Gemma emits `stat_code: "ERN"` for a ROI dispatch → assertion fails → returns None. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_roi_postprocess_rejects_sentinel_passthrough` | `one_liner: "__FILL_IN__"` → Pydantic field_validator raises → returns None → fallback fires. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_roi_postprocess_logs_structured_record` | After parse, `_log_receipt_parse` appends record with `call_site="explain_roi_receipt"`. Both success and failure branches. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_res_postprocess_happy_path` | Valid Gemma JSON for RES → 2-component receipt, position-0=AI exposure with `value_pct=80`, position-1=human-essential with `value_pct=70`, math line `0.5 × 8 + 0.5 × 7 → score 8/10`. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_res_postprocess_label_normalization_position_based` | Gemma emits `components[0].label="AI exposure score"` (off-script) → `_normalize_label_by_position(idx=0, ...)` matches → replaces with "AI exposure" → WARNING logged. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_res_postprocess_handles_swap` | Gemma emits the human-essential label at position 0 and the AI-exposure label at position 1. The position-based normalizer replaces both labels with the canonical-by-position values. The downstream value_pct stamping uses the correct row score per position (position 0 always reads stat_res, position 1 always reads stat_hmn — Gemma's swap doesn't reach the data extraction). |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_res_postprocess_value_pct_conversion` | Server-stamps `components[0].value_pct = stat_res * 10` (raw 1-10 → 10-100 range that StatComponent.value_pct expects). Test fixture: `stat_res=8` → `value_pct=80`. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_res_postprocess_partial_null` | One row score null → respective component's `value_pct=None`, `missing_reason=<canned>`, math_line shows `0.5 × n/a + 0.5 × Y → score N/10`. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_grw_postprocess_happy_path` | Valid Gemma JSON for GRW → single 100% component, `value_pct=None`, `anchor_text="+15.2% projected change over 10 years"`, math line `+15.2% employment change → GRW score 8/10`. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_grw_postprocess_employment_change_null` | `employment_change_pct` null → `anchor_text` shows missing-data form, missing_reason canned, math_line shows `n/a employment change → score N/10`. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_grw_postprocess_negative_change_format` | `employment_change_pct=-3.4` → math line shows `-3.4% employment change → GRW score 3/10` (no `+` sign for negatives). |
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_roi_explain_dispatches_via_registry` | `[explain-this:ROI]` sentinel → registry lookup hits the ROI config → response is `ExplainStatReceipt` with `stat_code="ROI"`. |
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_res_explain_dispatches_via_registry` | Same for RES. |
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_grw_explain_dispatches_via_registry` | Same for GRW. |
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_roi_explain_fallback_uses_cached_tool_log` | Per-stat parallel to ERN's existing fallback test — `_postprocess_roi_explain_receipt` returns None → markdown-fallback fires with cached tool log injected, no MCP re-fetch (assert MCP dispatch count == 1). |
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_res_explain_fallback_uses_cached_tool_log` | Same for RES. |
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_chat_ask_grw_explain_fallback_uses_cached_tool_log` | Same for GRW. |
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_unknown_explain_sentinel_falls_through` | Sentinel like `[explain-this:HMN]` (deprecated stat) or `[explain-this:FOO]` (unknown) is NOT in the registry → falls through to the existing free-form scope handler (no crash, no 5xx). |
| P0 | `backend/tests/services/test_ask_gemma.py` | `test_aura_explain_sentinel_not_yet_registered` | `[explain-this:AURA]` is deliberately NOT in the registry until the AURA spec ships. Verify the dispatch falls through to free-form prose handler today. (Test is removed by the AURA spec.) |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_render_math_line_roi_format` | `_render_math_line_roi` produces `'$112,400 / $78,400 = 1.43 → ROI score 4/10'` for valid inputs; `'n/a / $Y = n/a → score N/10'` for null published_cost_4yr; etc. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_render_math_line_res_format` | `_render_math_line_res` produces `'0.5 × 8 + 0.5 × 7 → score 8/10'` for valid; `'0.5 × n/a + 0.5 × 7 → score N/10'` for null stat_res; etc. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_render_math_line_grw_format` | `_render_math_line_grw` produces `'+15.2% employment change → GRW score 8/10'` for positive; `'-3.4% employment change → GRW score 3/10'` for negative; `'n/a employment change → score N/10'` for null. |
| P0 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_normalize_label_by_position_match` | Position-based label normalizer matches by index, replaces off-script paraphrase, returns `(canonical, True)` and logs WARNING. |
| P0 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_renders_roi_receipt_no_percentile_callout_when_value_pct_null_and_no_missing_reason` | ROI payload renders without the open-ring + em-dash glyph; only the `anchor_text` and `anchor_dollars` row appears below the explainer. |
| P0 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_renders_grw_receipt_no_percentile_callout` | Same for GRW. |
| P0 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_renders_res_receipt_two_components` | RES payload with 2 components renders both rows; stagger animation keys off length-2 list. |
| P0 | `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | `test_renders_missing_reason_still_shows_glyph_for_roi` | When ROI's component has `value_pct=null` AND `missing_reason !== null`, the open-ring glyph DOES render (existing missing-data treatment) — proves the suppression is gated on missing_reason being null. |
| P0 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `test_roi_explain_link_dispatches_sentinel` | Clicking the ROI legend's "✦ Explain this to me" fires `[explain-this:ROI]`. |
| P0 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `test_res_explain_link_dispatches_sentinel` | Same for RES. |
| P0 | `frontend/src/screens/BuildResultsScreen.test.tsx` | `test_grw_explain_link_dispatches_sentinel` | Same for GRW. |
| P1 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_roi_postprocess_reads_build_not_tool_fields` | Verify the postprocessor reads `build.career.published_cost_4yr` and `build.career.earnings_1yr_median` directly, not from MCP tool response fields. Set build values that differ from tool-result values; assert receipt uses the build values. (Residency-branch coverage for `_published_cost_4yr` itself lives in `stat_engine` tests, not here.) |
| P1 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_grw_math_line_zero_change` | `employment_change_pct=0` → math line shows `'0.0% employment change → GRW score N/10'` (no sign, no plus). |
| P1 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_registry_dispatch_completeness` | All four stats (`ERN`, `ROI`, `RES`, `GRW`) registered; AURA NOT registered. Iterate `_STAT_EXPLAIN_REGISTRY.keys()`. |
| P1 | `backend/tests/services/test_ask_gemma_explain_receipt.py` | `test_registry_config_has_all_fields` | Each `_StatExplainConfig` has non-empty `appendix_template`, `markdown_fallback_appendix`, callable `postprocessor`, `log_call_site` matching the pattern `explain_{stat_lower}_receipt`. |
| P2 | `frontend/src/lib/zodSchemas.test.ts` | `test_zod_parser_accepts_roi_receipt` / `test_zod_parser_accepts_res_receipt` / `test_zod_parser_accepts_grw_receipt` | The same Zod parser that ships for ERN parses ROI/RES/GRW payloads correctly (no per-stat schema variant needed). |

#### Test Data Requirements

- **Fixtures.** Three canonical builds per stat covering missing-data permutations:
  - ROI: published_cost_4yr present + earnings present (happy path); published_cost_4yr null; earnings null; both null. Use the same Indiana University → CS → Software Developer build for happy path; use a build with `cost_of_attendance_annual=null` for the published-cost-null case.
  - RES: stat_res + stat_hmn both present (happy); stat_res null; stat_hmn null; both null.
  - GRW: employment_change_pct present (happy, both positive and negative); null.
- **Mocks.** Per-stat mock Gemma client responses for: valid JSON, malformed JSON, sentinel-passthrough on prose fields, label drift (with the position-swap case for RES specifically), `score: 99` hallucination, `stat_code: "ERN"` cross-stat drift in a ROI dispatch.
- **Tool result mocks.** Mock `get_career_paths` (for ROI and RES) and `get_occupation_data` (for GRW) responses with the null permutations above. Use the existing ERN-spec mocks as a base where the row shape overlaps.
- **State.** No new env vars. `INFERENCE_BACKEND` is already set per dev environment; both backends covered by smoke verification (§9), not unit tests.

---

## §5 Architecture Review

### @fp-architect Review
**Status:** SKIPPED (Standard prompt weight — architecture established by ERN spec, this spec is a sibling extension; reviewer can be invoked post-hoc via §10 Discussion if any §4 service-changes detail proves contentious during implementation)

#### Findings
[ARCH REVIEW skipped per Standard calibration. Reasoning: no schema changes, no new MCP tools, no new public API surface, no formula changes. Three new helpers per stat that mirror the ERN spec's helpers verbatim. The registry refactor is the only architectural surface and it's a localized one-file change.]

#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review (if applicable)
**Status:** SKIPPED (no pipeline / no formula changes)

#### Findings
[Skipped — this spec describes existing formulas (`compute_stat_roi`, `_blend_res`, `compute_grw_score`) for the explainer voice; it does not modify any of them, does not change Gold-zone tables, and does not add new MCP tools.]

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
| `backend/app/services/ask_gemma.py` | Added `_EXPLAIN_SENTINEL_RE`, `_StatExplainConfig` dataclass, `_STAT_EXPLAIN_REGISTRY` (ERN/ROI/RES/GRW entries). Added ROI/RES/GRW postprocessors, math-line renderers, label allowlists, appendix templates (JSON + markdown fallback), `_normalize_label_by_position`, `_extract_res_raw_scores`, `_extract_grw_employment_change`, `_format_cached_tool_values_generic`. Refactored `chat_ask` and `chat_ask_stream` dispatch from ERN-only to registry-based. |
| `frontend/src/components/menu/ExplainStatReceipt.tsx` | Renderer change: 3-state logic for percentile-callout row (populated, intentionally-null, missing-data). Fixed component key to use index for RES 50/50 case. |
| `frontend/src/screens/BuildResultsScreen.tsx` | Replaced `handleExplainErn` with generalized `handleExplainStat(statKey)`. Extended "✦ Explain this to me" button to ERN, ROI, RES, GRW rows. |
| `docs/reference/stat-display-surfaces.md` | Updated §1a (all four stats wired), §1i (ROI/RES/GRW entries with per-stat details). |

### Deviations from Spec
- Did NOT rename `_render_math_line` to `_render_math_line_ern` per Decision 2's "renamed during refactor" note. Existing ERN tests import it by name; rename adds test churn for zero value. The new per-stat renderers have explicit `_roi`/`_res`/`_grw` suffixes.
- The `_StatExplainConfig.postprocessor` is synchronous (not `Awaitable`) since all three new postprocessors are sync (matching ERN's `_postprocess_ern_explain_receipt`). The spec's type signature showed `Awaitable` but the implementation doesn't need it.
- Skipped score-null paths for ROI/RES/GRW (only ERN has one). The spec doesn't require them — when `build_score is None` the postprocessor returns None and the markdown fallback fires.
- RES postprocessor reads `raw_stat_res`/`raw_stat_hmn` from the Build object first, falling back to tool_call_log extraction only when the build values are None.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | PASS | — | — |

### Effort-shift verification (Decision 9)
- [x] Verified 2026-05-02 during spec review: `_apply_effort` in `backend/app/services/stat_engine.py:124-135` shifts ERN only (`new_ern = _clamp_stat(... + shift)`; roi/res/grw/aura passed through unchanged). ROI/RES/GRW renderers omit the effort parameter entirely.

---

## §7 Test Coverage

**Status:** COMPLETE

### Tests Added

| Test File | Test Count | What It Tests |
|-----------|-----------|---------------|
| `backend/tests/services/test_ask_gemma_explain_receipt.py` | 83 new | ROI/RES/GRW postprocessors (happy path, score override, null inputs, label normalization, sentinel passthrough, stat_code mismatch), math-line renderers (all null permutations), registry dispatch completeness, `_normalize_label_by_position` |
| `frontend/src/components/menu/ExplainStatReceipt.test.tsx` | 4 new | ROI no-percentile-callout, ROI missing_reason shows glyph, GRW no-percentile-callout, RES 2-component rendering |
| `frontend/src/screens/BuildResultsScreen.test.tsx` | 4 new | ROI/RES/GRW explain link visibility, AURA explain link not shown |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest | 1475 | 0 | 0 | 1475 |
| vitest | 801 | 0 | 0 | 801 |

---

## §8 Reviews

**Status:** COMPLETE

### Design Audit (@design-builder)
**Status:** SKIPPED (visual treatment fully inherited from ERN spec; one renderer change covered by frontend tests)

### Code Review (@faang-staff-engineer)
**Status:** COMPLETE — all findings resolved

#### Findings
| ID | Severity | Issue | Resolution |
|----|----------|-------|------------|
| S1 | BLOCKER | Division by zero in `_render_math_line_roi` when `earnings_1yr_median == 0` | Fixed: treat zero same as None |
| S2 | BLOCKER | Frontend `isMissing` heuristic permanently dims text for non-ERN receipts | Fixed: `isMissing = component.missing_reason !== null` |
| S3 | Moderate | Score-null path only handled for ERN (degrade to markdown for ROI/RES/GRW) | Documented: added log line + comment at dispatch site; by-design per spec Decision 10 |
| S4 | Moderate | Unused `soc_code` param in `_extract_res_raw_scores` | Fixed: removed param and updated callsite |
| S5 | Moderate | RES `value_pct = raw * 10` has no range guard | Fixed: clamped to `min(max(raw * 10, 0), 100)` |

#### Verdict
- [x] APPROVED (after fixes)
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

---

## §9 Verification

**Status:** PASS (2026-05-02)

### Backend (@fp-builder)
| Check | Result |
|-------|--------|
| Lint (ruff) | PASS |
| Type check (mypy) | PASS |
| Tests (pytest) | PASS (1476 tests) |

### Frontend (@fp-builder)
| Check | Result |
|-------|--------|
| TypeScript | PASS |
| Tests (vitest) | PASS (53 receipt + BuildResults tests) |
| Production build (Vite) | PASS |

### Manual smoke verification (deferred to human)
| Backend | ROI | RES | GRW |
|---------|-----|-----|-----|
| Ollama (local) | | | |
| OpenRouter (cloud) | | | |

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

[Final thoughts, lessons learned, follow-up items.]
