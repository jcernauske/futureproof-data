# FutureProof Gemma Eval Harness

Reproducible eval for the 20 Gemma surfaces that power FutureProof. Measures four things every Gemma surface either should or could be judged on:

| Axis | What we measure | How |
|------|----------------|-----|
| **Schema validity** | Does the production output parse as the declared Pydantic model? | `eval/scorers/schema.py` |
| **Field accuracy** | Do specific fields (CIP codes, stat codes, scores) match the labeled ground truth? | `eval/scorers/exact_match.py`, `tolerant_match.py` |
| **Tool-call correctness** | For function-calling surfaces, does Gemma pick the right tool with reasonable args? | `eval/scorers/tool_call.py` |
| **Narrative quality** | A 5-axis rubric (relevance, specificity, voice, accuracy, length) scored 1-5 by **Claude Opus 4.7** as external judge. | `eval/scorers/rubric.py` |
| **Latency** | p50 / p95 / p99 from instrumented production logs, per surface | `eval/scorers/latency.py` |

Spec: [`docs/specs/gemma-eval-harness.md`](../docs/specs/gemma-eval-harness.md).

---

## Running

```bash
# Free, fast: aggregate latency from logs/gemma.jsonl for all 20 surfaces.
# Runs against existing production logs — no new tokens spent.
make eval-latency

# Run P0 surfaces against golden cases (8 surfaces × ~5 cases = ~40 inferences).
# Requires Gemma backend reachable (INFERENCE_BACKEND env) AND ANTHROPIC_API_KEY
# set for rubric scoring.
make eval-p0

# Same but skip rubric scoring — useful when you don't want Anthropic API spend.
make eval-p0-no-rubric

# Run the scorer unit tests (no live LLM calls).
make eval-test
```

Results land in `eval/results/<timestamp>/` — never overwritten, so baseline comparisons stay intact.

---

## Surface inventory

20 surfaces total. The map from production `extra["call_site"]` to canonical eval surface lives in `eval/instrumentation/call_site_map.py`.

| # | Surface | Output | Tool use | Tier |
|---|---------|--------|----------|------|
| 1 | `ask_gemma_chat` | Free text + tool trace | ✅ 5 tools | P0 |
| 2 | `career_intent` | JSON | ❌ | P0 |
| 3 | `chip` | JSON | ✅ | P0 |
| 4 | `explain_ern` | JSON | ✅ | P0 |
| 5 | `explain_roi` | JSON | ✅ | P0 |
| 6 | `explain_res` | JSON | ✅ | P0 |
| 7 | `explain_grw` | JSON | ✅ | P0 |
| 8 | `explain_aura` | JSON | ✅ | P0 |
| 9 | `boss_narrative` | Narrative | ❌ | P1 |
| 10 | `career_tiering` | Structured | ❌ | P1 |
| 11 | `career_description` | JSON | ❌ | P1 |
| 12 | `next_steps` | Narrative | ❌ | P1 |
| 13 | `guidance` | Narrative | ❌ | P1 |
| 14 | `skill_pool` | Narrative→Struct | ❌ | P2 |
| 15 | `skill_recs` | Narrative→Struct | ❌ | P2 |
| 16 | `reroll_commentary` | Narrative | ❌ | P2 |
| 17 | `career_pick_qna` | Narrative | ❌ | P2 |
| 18 | `initial_major_resolution` | Streaming narrative | ❌ | P2 |
| 19 | `pdf_questions` | JSON | ❌ | P2 |
| 20 | `soc_expansion` | JSON | ✅ | P2 |

---

## Methodology

### Why Claude as the rubric judge, not Gemma

Gemma-judging-Gemma is circular. A judge can poke holes in any "the model graded its own homework" story. Claude is external, capable, and the methodology is defensible. We use `claude-opus-4-7` with prompt caching on the static rubric prefix (~1.5K tokens cached for ~0.1× cost).

The judge prompt and 5-axis anchors live in `eval/scorers/rubric.py`. The voice guide quoted to the judge mirrors `docs/reference/voice-guide.md`.

### Why we don't run a 5,000-case eval

This is a 6-day hackathon submission. Each golden case has to be hand-labeled to be useful — fabricated labels just measure how well Gemma matches Claude's intuition, which is not what judges care about. The P0 set is ~5 cases per surface, hand-curated to cover happy path, edges (low/high wage, declining careers), out-of-distribution inputs (deaf education, dance), and adversarial inputs (typos, nonsense). That's enough to detect regression, not enough to publish.

To expand a golden set, append JSONL rows to `eval/golden/<surface>/cases.jsonl`.

### How latency works

Production already logs every Gemma call to `logs/gemma.jsonl` with `duration_ms` and `usage` fields, tagged with `extra["call_site"]`. The eval harness reads those logs and filters by surface. **No new instrumentation was added** for latency — we use what the app already records.

Synthetic records (`synthetic: true`, written by `log_synthetic_event` for parse-success/failure flags) are excluded from latency aggregation — they have no `duration_ms`.

**Known limitation:** the 5 `explain_*` surfaces use `log_synthetic_event` to tag receipt parse outcomes but route the underlying Gemma calls through other call_sites (e.g., `ask_gemma_stat`). Latency for explain receipts is currently aggregated under those upstream call_sites, not the explain surface itself. A future production change would split them; for the hackathon submission, eval runs that we kick off ourselves do pass `extra={"call_site": "explain_ern_receipt", "eval": true}` directly, so latency is attributable for our own runs.

### Reproducibility

```bash
git clone https://github.com/.../futureproof-data
cd futureproof-data
cd backend && pip install -e ".[dev]" && cd ..
pip install anthropic pydantic pandas  # eval-specific deps
export ANTHROPIC_API_KEY=sk-ant-...    # for rubric scoring
export INFERENCE_BACKEND=ollama         # or openrouter
make eval-p0
```

Results are deterministic for structured surfaces (`temperature=0.0, seed=<n>`) within a single Gemma model + backend. Rubric scores are stochastic at the Claude end (Opus 4.7 with adaptive thinking) — for headline numbers, run rubric scoring twice and report mean ± stdev.

### What we are NOT doing

This harness is intentionally NOT:
- a benchmark against other models (Llama, GPT, Claude)
- a Gemma-vs-Gemma model-size comparison (that's `gemma-model-profiles`)
- a prompt-optimization framework (no DSPy-style auto-tuning)

We measure what we ship, with enough rigor to defend the claim that we measure what we ship.

---

## Adding a new surface

1. Add the surface name + production `call_site` strings to `eval/instrumentation/call_site_map.py`.
2. Register an adapter in `eval/adapters/registry.py`. Most surfaces can use `GenericGemmaAdapter` if the golden case carries the full prompt; surfaces with non-trivial prompt construction should wrap the production function directly (see `career_intent.py`).
3. Add `eval/golden/<surface>/cases.jsonl` with hand-labeled cases.
4. Re-run `make eval-test` to verify scorers still pass, then `make eval-p0` to baseline.
