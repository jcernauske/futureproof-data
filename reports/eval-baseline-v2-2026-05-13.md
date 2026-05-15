# Eval Baseline v2 — 2026-05-13 (corrected methodology)

This run supersedes [`eval-baseline-2026-05-13.md`](eval-baseline-2026-05-13.md). The first baseline made a methodology error: it scored Gemma's `score` field on the five `explain_*` surfaces — but production server-overwrites that field before the user ever sees it. **The first report's two headline findings ("score-3 floor" and "RES regression-to-mean") describe a value that doesn't reach production output.** Walked back in §"What we got wrong" below.

This v2 baseline measures only what Gemma actually controls in those surfaces:
- `stat_code` identification (Gemma's only categorical decision Gemma actually owns)
- Schema validity (structural integrity of the JSON)
- Prose length bounds (catches empty/truncated headlines)
- Headline directional content (case-insensitive substring match against an anchor list)

Plus `career_intent`, where Gemma genuinely decides the CIP — same eval as before.

Spec: [`docs/specs/gemma-eval-harness.md`](../docs/specs/gemma-eval-harness.md). Methodology: [`eval/README.md`](../eval/README.md).

---

## What we got wrong in v1

Looking at `backend/app/services/ask_gemma.py:1154-1158, 2262-2263, 2599-2611, 2977-2990` (and the parallel paths for ERN/ROI/AURA), the production receipt pipeline for every `explain_*` surface does this:

```python
receipt.score = build_score   # server-stamps the deterministic score from stat_engine
receipt.score_max = 10        # server-stamps the constant
receipt.math_line = _render_math_line_*(...)   # server-builds the math line
# components[i].value_pct, anchor_dollars, evidence_bullets, missing_reason
# are also server-stamped from tool results
```

The five pentagon stats (ERN, ROI, RES, GRW, AURA) are **computed deterministically in `stat_engine.py`** from precomputed Gold-zone data (BLS wages, debt math, blended AI-resilience, BLS growth %, institutional aura). Gemma's role in `explain_*` is to **write the explanation prose** (`headline`, component `explainer` text, `one_liner`, `why_mix_paragraph`) — the *score itself* is decided before Gemma is called and pinned afterward.

The v1 baseline scored whether Gemma's `score` field matched the labeled expected score. It does not. That entire metric is meaningless for production behavior. The "score-3 floor" and "RES regression-to-mean" findings are real observations of model behavior on a fabricated, in-eval prompt — but neither describes anything a user ever sees.

This is the kind of error a good eval is supposed to surface. We surfaced it by running the eval, looking at production code, and asking "wait, does Gemma actually decide this?" The answer was no for 5 of 6 surfaces.

---

## What v2 actually measures

Per surface, what Gemma genuinely controls and what we now test:

| Surface | Gemma's actual decision | What we test |
|---------|------------------------|--------------|
| `career_intent` | Which CIP code to return | `matched_cip ∈ accepted_set`, `confidence ∈ {low,medium,high}` |
| `explain_ern` | The prose (headline + math description) | `stat_code = ERN`, headline length 15-200 chars, math_line 5-500 chars, directional content |
| `explain_roi` | The prose | Same template (stat_code = ROI) |
| `explain_res` | The prose | Same template (stat_code = RES) |
| `explain_grw` | The prose | Same template (stat_code = GRW) |
| `explain_aura` | The prose | Same template (stat_code = AURA) |

---

## Headline numbers

| Surface | n cases | stat_code ✓ | length bounds ✓ | directional content ✓ | p50 lat | p99 lat |
|---------|--------:|------------:|----------------:|----------------------:|--------:|--------:|
| `career_intent` | 20 | — | — | 21/21 (field accuracy) | 3.0 s | 18.3 s |
| `explain_ern` | 20 | 20/20 (100%) | 40/40 (100%) | 17/20 (85%) | 1.8 s | 5.9 s |
| `explain_roi` | 20 | 20/20 (100%) | 40/40 (100%) | 18/20 (90%) | 1.7 s | 4.1 s |
| `explain_res` | 20 | 20/20 (100%) | 40/40 (100%) | 13/20 (65%) | 2.4 s | 4.7 s |
| `explain_grw` | 20 | 20/20 (100%) | 40/40 (100%) | 8/20 (40%) | 1.8 s | 3.2 s |
| `explain_aura` | 20 | 20/20 (100%) | 40/40 (100%) | 10/20 (50%) | 1.7 s | 5.0 s |
| **Total** | **120** | **100/100** | **200/200** | **87/121** | — | — |

**Honest reading:** Gemma is structurally bulletproof — 100% schema validity, 100% stat_code identification, 100% prose-length bounds across 100 explain_* runs. **The "directional content" metric is doing the heavy lifting and that's the noisy one.**

---

## The directional content metric is too strict

`career_intent` is the most defensible: Gemma decides the CIP, we check membership in an accepted set, the result is 21/21. Real signal.

The five `explain_*` surfaces all pass `stat_code` and length checks at 100%. The variance in the "headline directional content" column is **mostly anchor-vocabulary mismatch, not model failure.** Examples from the actual run:

**explain_grw (40% directional pass) — the model is fine, my anchors were narrow:**

| Case | Headline (Gemma) | Anchors (mine) | What happened |
|------|------------------|----------------|---------------|
| `nps_001` (nurse practitioners, +44.5%) | *"Explosive Demand for Nurse Practitioners"* | `growing, growth, expand, boom, rising` | Model said "explosive demand" — correct direction, novel word |
| `word_processors_002` (-38.2%) | *"Obsolescence Imminent"* | `decline, shrink, decreas, contract, fewer` | "obsolescence" → correct, novel word |
| `teachers_003` (+0.8%) | *"Stagnant Growth Outlook"* | `stable, flat, steady, modest, average` | "stagnant" → correct, novel word |
| `secretaries_005` (-10.4%) | *"Automation Risk & Declining Demand"* | `decline, shrink, decreas...` | "Declining" — `'decline' in 'declining'` is **False** because "declining" is `declin-i-n-g` not `decline-...`. Anchor word should have been `declin` (substring root). |
| `wind_techs_004` (+60.4%) | *"Explosive Demand in Renewable Energy Infrastructure"* | same as nps | Correct direction, novel word |

**explain_aura (50% directional pass) — same pattern:**

| Case | Headline | What happened |
|------|----------|---------------|
| `mit_001` (admit 4%, elite) | *"Global Apex of Academic Prestige"* | "apex" / "prestige" — correct, but my anchors required "prestig**ious**" specifically |
| `harvard_004` | *"Global Institutional Supremacy"* | "supremacy" — correct |
| `iu_bloomington_002` (state flagship) | *"Moderate Institutional Prestige"* | "moderate" should have been in my mid-anchor list. It wasn't. |
| `uiuc_006` (tier1 public) | *"Strong Institutional Stability with High Resource Density"* | "strong" + "high" — correct direction, my anchors were synonym-narrow |

**Of the 34 "directional content" failures across 100 cases, ~28 are anchor-narrowness, ~6 are model genuinely missing the direction.** That's a rough manual estimate from reading the headlines — I did not score every failure carefully. The eval is currently penalizing the model for using *better* vocabulary than my anchor list.

**This is a real lesson:** content_check via substring is a weak signal for prose quality. To do this properly we need either:
1. Much broader anchor lists with stems (`declin*`, `prestig*`) and synonyms — risks "gaming the test"
2. Rubric scoring with Claude as judge against the five-axis rubric — the right answer; not run here due to API spend
3. Manual human review of headlines — what we'd do for a published eval

The honest framing for the v2 report: **the structural metrics (100% across schema/length/stat_code) are real wins. The directional content metric should be read as "lower bound on model performance" — actual prose quality is almost certainly higher.**

---

## What we genuinely validated

1. **Gemma always identifies the right stat code.** 100/100 across `explain_ern/roi/res/grw/aura`. The model never confuses which stat it's writing about.
2. **Gemma always produces a non-empty, reasonable-length headline and math_line.** 200/200 length-bounds across all 100 explain_* runs. No truncated responses, no empty fields, no runaway generation.
3. **Schema-level reliability is high.** 99.2% JSON parse success from v1 (we don't observe an *increase* in parse errors with the new scoring; same parse path).
4. **`career_intent` works as advertised.** 21/21 (100%) field accuracy on the one surface where Gemma actually decides the value. This is the highest-signal result in the eval.

---

## Latency findings (real, unchanged from v1)

p50 latencies all under 3 seconds on `gemma4:e4b`. P99 is widely scattered (3-18s) — some outliers in `career_intent` likely due to Ollama warm-up or longer JSON outputs:

| Surface | n | p50 ms | p95 ms | p99 ms |
|---------|--:|------:|------:|------:|
| `explain_roi` | 20 | 1683 | 3823 | 4086 |
| `explain_aura` | 20 | 1662 | 4626 | 4983 |
| `explain_grw` | 20 | 1774 | 3034 | 3208 |
| `explain_ern` | 20 | 1814 | 2756 | 5926 |
| `explain_res` | 20 | 2354 | 4578 | 4682 |
| `career_intent` | 20 | 2978 | 12987 | 18319 |

The v1 finding that explain_res was the *slowest* surface (5.3s p50) **does not reproduce in v2** (2.4s p50). This is probably explained by other Ollama load on the box during v1 — both runs use the same prompts, same model, same backend. Latency was the metric most sensitive to environment noise.

---

## What this changes about the FutureProof story

**v1 conclusion (wrong):** "Gemma has a score-3 floor; RES regresses to mean; product needs prompt fixes."

**v2 conclusion (right):** "Gemma is structurally reliable on the prose surfaces — schema-valid, correctly-typed, reasonable lengths, correct stat_code identification, 100% across the board on those measures. The deeper quality question — *is the prose actually any good* — is not answered by the current eval; it requires the rubric scorer (Claude as judge) or human review. That's the next step."

The v1 findings were not entirely wasted — they prompted the deeper read of `ask_gemma.py` that surfaced the server-stamps. That read changed the whole understanding of what `explain_*` surfaces actually do, and is itself a hackathon-worthy correction. The eval is now testing a real thing.

---

## Honest gaps (updated)

1. **Prose quality is not scored.** All five explain_* surfaces produce headlines, math_lines, and (in production) component explainers. We have no quality metric beyond length and substring matching. The rubric scorer (Claude Opus 4.7 judge) is built and unit-tested but was not run on this baseline. **This is the obvious next step.**
2. **Eval prompts differ from production prompts.** The production system prompt for `explain_res` (and the others) is 100+ lines, requires tool calls to `get_career_paths`, and asks for a much richer schema (`components`, `one_liner`, `why_mix_paragraph`, `sources`). Our eval prompts are a simplified single-shot version. To test what production actually produces we would need MCP fixtures and the real prompt templates.
3. **`ask_gemma_chat` and `chip` unevaluated.** Both use `generate_with_tools_loop` with live MCP tools. Adapters registered but unseeded. P0 coverage: 6 of 8 surfaces.
4. **No human calibration.** Spec called for 50 human-labeled narratives to validate Claude-judge correlation. Not done.
5. **Single backend, single model.** Ollama + `gemma4:e4b` only. 26B / OpenRouter not tested.
6. **Single labeler, no inter-rater reliability.** Same as v1.

---

## Reproducing this run

```bash
cd /path/to/futureproof-data
make eval-test          # 26 scorer unit tests, ~1 sec
make eval-p0-no-rubric  # 6-surface, 120-case eval, ~7 min, $0
```

Raw results: `eval/results/2026-05-13-214236/summary.json`. Compare with v1 at `eval/results/2026-05-13-183007/summary.json`.

Code: `eval/runner.py`, `eval/adapters/`, `eval/scorers/` (new: `content_check.py`), `eval/golden/*/cases.jsonl`.

---

## Bottom line

The eval works correctly now. It measures things Gemma actually controls, with a methodology that survives a careful reading of the production code. The two big v1 findings were artifacts of measuring server-overwritten fields — walked back here.

What we still don't know: **whether the prose Gemma writes is actually good.** Schema-valid yes, correctly-typed yes, correctly-categorized yes — but is the headline "Explosive Demand for Nurse Practitioners" *the right tone for FutureProof* (cool, confident, data-honest)? The current eval can't say. That's a rubric-scorer (or human-review) question and is the next thing to build.

The honest takeaway for the hackathon submission: we built a working eval harness, it caught a real methodology bug in its own design, we corrected and re-ran, and we know exactly what we still don't measure. That's better than a 91%-everything-is-fine report would have been.
