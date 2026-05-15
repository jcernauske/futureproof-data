# Eval Baseline — 2026-05-13

First end-to-end run of the Gemma eval harness against live Ollama (`gemma4:e4b`). 120 hand-labeled cases across 6 P0 surfaces, zero API spend (all structured output — no rubric required).

Spec: [`docs/specs/gemma-eval-harness.md`](../docs/specs/gemma-eval-harness.md). Methodology: [`eval/README.md`](../eval/README.md).

---

## Headline numbers

| Surface | n cases | field accuracy | adapter errors | p50 latency | p99 latency |
|---------|--------:|--------------:|---------------:|------------:|------------:|
| `career_intent` | 20 | **21/21 (100%)** | 0 | 5.1 s | 6.1 s |
| `explain_ern` | 20 | **36/39 (92%)** | 0 | 2.5 s | 3.3 s |
| `explain_roi` | 20 | **33/37 (89%)** | 1 (JSON parse) | 3.2 s | 18.4 s |
| `explain_res` | 20 | **28/40 (70%)** | 0 | 5.3 s | 6.2 s |
| `explain_grw` | 20 | **40/40 (100%)** | 0 | 2.4 s | 3.2 s |
| `explain_aura` | 20 | **39/40 (98%)** | 0 | 3.4 s | 5.3 s |
| **Total** | **120** | **197/217 (91%)** | **1 (0.8%)** | — | — |

**Headline:** 91% field accuracy across 217 scored checks. 99.2% JSON parse success. One genuinely weak surface (explain_res, 70%) with a coherent root cause.

---

## The interesting finding: Gemma's score-3 floor

**Gemma 4 (e4b) refuses to give scores below 3.** This is the dominant failure mode and it's consistent across every stat surface.

Every wage/ROI/AI-exposure case where ground truth was 1 or 2 came back with a 3 from the model:

| Case | Surface | Expected | Got | Difference |
|------|---------|---------:|----:|-----------:|
| `explain_ern_002_low_wage` (Childcare, $28K) | ERN | 1 | 3 | +2 |
| `explain_ern_016_cashier` (Cashiers, $28K) | ERN | 1 | 3 | +2 |
| `explain_ern_017_cook` (Cooks, $33K) | ERN | 1 | 3 | +2 |
| `explain_roi_006_columbia_journalism` ($324K → $48K wage) | ROI | 1 | 3 | +2 |
| `explain_roi_012_oberlin_music` ($318K → $43K wage) | ROI | 1 | 3 | +2 |
| `explain_res_014_customer_service_rep` (0.86 Karpathy) | RES | 1 | 3 | +2 |

**Why this matters:** FutureProof's value prop is *data-honest*. CLAUDE.md explicitly forbids softening negative information ([[feedback_no_sanitizing_negative_info]]). A childcare worker earning $28K with a CIP percentile of 6 is a 1/10 on earning power — not a 3. The model is hedging exactly where it shouldn't.

**This is the single most actionable finding from the eval.** Mitigations to try (in order of cost):
1. Add explicit "do not soften — score honestly even when negative" instruction to each explain_* system prompt
2. Add a few-shot example with score=1 in the prompt
3. Switch to the 26B model for stat scoring (would need to verify the floor is actually a model-size issue, not a training issue)

---

## The really interesting finding: explain_res regression-to-mean

`explain_res` is the worst-performing surface (70%) and the failure pattern is even more pronounced than the score-3 floor. **Almost everything regresses to 7.**

| Case | Karpathy AI exposure | Expected | Got | Direction |
|------|---------------------:|---------:|----:|-----------|
| Paralegals | 0.84 (high) | 2 | **7** | model under-scores danger |
| Translators | 0.81 (high) | 3 | **7** | model under-scores danger |
| Market Research Analysts | 0.78 (high) | 2 | **7** | model under-scores danger |
| Writers | 0.79 (high) | 2 | **6** | model under-scores danger |
| Graphic Designers | 0.74 (high) | 2 | **7** | model under-scores danger |
| Accountants | 0.72 (high) | 3 | **7** | model under-scores danger |
| Radiologists | 0.68 (moderate-high) | 4 | **7** | model under-scores danger |
| Electricians | 0.12 (very low) | 10 | **7** | model under-scores safety |
| Carpenters | 0.10 (very low) | 10 | **8** | model under-scores safety |
| PT Assistants | 0.14 (very low) | 10 | **8** | model under-scores safety |
| Firefighters | 0.08 (very low) | 10 | **8** | model under-scores safety |

**The model doesn't separate high-AI-exposure from low-AI-exposure careers.** It compresses everything into the 6–8 range regardless of the Karpathy score we provide in the prompt. This is the worst possible failure mode for a stat whose entire purpose is to *differentiate* careers by AI exposure.

The product implication: the RES stat in the live demo will look defensible at first glance (everything scores 6–8, which sounds reasonable) but will *not actually reflect underlying differences in AI exposure*. A paralegal and a carpenter score similar RES values when they should be at opposite ends.

**Why this matters for the hackathon submission:** RES is what the "AI 4 Good" hackathon judges will look at most carefully. We sell the product on AI-aware career planning. If RES doesn't distinguish jobs by AI exposure, the product's central premise is undercut. **This eval surfaced the issue. Without it, we'd ship a stat that looks fine in spot-checks but breaks under any systematic test.**

Mitigation: pass `effort: "high"` (we currently use the default), add per-axis reasoning steps to the prompt, or fall back to deterministic scoring from the Karpathy float directly with Gemma only generating the headline + math_line.

---

## What the model is genuinely good at

**Career intent resolution: 21/21 (100%).** Gemma is a strong CIP-code matcher. It correctly handled:
- Common majors ("nursing", "engineering", "psychology")
- Ambiguous inputs ("data science" → any of 3 valid CIPs)
- OOD inputs ("deaf education" → 13.1003 exactly; "mortuary science"; "tattoo artist" → fine arts)
- Typos ("engenering", "buisness")
- Conversational ("wait actually i want to do art history not business")
- Nonsense ("asdfqwerty") — correctly returned low/medium confidence rather than confidently fabricating

**Growth outlook: 40/40 (100%).** When BLS hands the model a real percentage, the model can map it to a 1-10 score correctly across the full range — including +60% (wind turbine techs → 10), -41% (telephone operators → 1), and flat (+0.8% teachers → 5). This is the only stat where the score-3 floor *isn't* observed — because BLS data is unambiguous enough that the model trusts it.

**Institution prestige: 39/40 (98%).** The model has strong priors on US college tiers — got the elite/mid/community tiers right consistently. Only failure was Southern New Hampshire University (expected 2 for an online mass-enrollment school, got 4). Reasonable disagreement, not an obvious model error.

---

## Latency findings

All P50s under 6 seconds on `gemma4:e4b` running locally on an M-series Mac. Tail latencies are much wider:

| Surface | p50 | p95 | p99 | Note |
|---------|----:|----:|----:|------|
| `explain_grw` | 2.4 s | 3.1 s | 3.2 s | Tightest distribution — model is confident here |
| `explain_ern` | 2.5 s | 2.9 s | 3.3 s | Same — confident on wage scoring |
| `explain_roi` | 3.2 s | 4.8 s | **18.4 s** | One major outlier (the case that returned a parse error) |
| `explain_aura` | 3.4 s | 4.7 s | 5.3 s | Slightly wider — more reasoning required |
| `career_intent` | 5.1 s | 6.0 s | 6.1 s | Longer because output JSON is larger (alternatives list, reasoning) |
| `explain_res` | 5.3 s | 6.0 s | 6.2 s | Longer despite poor accuracy — model is "thinking" but not productively |

**The explain_res latency-vs-accuracy tradeoff is interesting:** the model takes longer on RES (5.3s p50 vs 2.5s for ERN) but produces worse output. Whatever extra reasoning it's doing on RES is not adding value — it's just hedging more. This corroborates the regression-to-mean finding.

---

## Reliability metrics

- **Structured output success:** 119/120 (99.2%). One JSON parse error on a Brown Anthropology ROI case — Gemma returned an unterminated string mid-output, probably hit a token cap mid-quote.
- **Empty responses:** 0
- **Schema drift:** None observed in the structured outputs we tested. Every successful parse had the expected top-level fields (`stat_code`, `score`, `score_max`, `headline`, `math_line` for explain_*; `matched_cip`, `matched_title`, `confidence`, `alternatives`, `reasoning`, `parent_cip` for career_intent).

---

## Methodology bug we caught (and what it taught us)

The first run of `career_intent` reported **0/21** field accuracy — a result that would have looked catastrophic in a top-line table. Investigation revealed our golden cases used field names from the spec (`cipcode`, numeric `confidence`) rather than the field names the production prompt actually elicits from the model (`matched_cip`, string-bucket `confidence`).

After fixing the golden cases to match the production output schema, the same run came back at **21/21 (100%)**. The model's actual behavior was unchanged — only our measurement was wrong.

**Lesson for hackathon submission:** the eval is only as honest as its expected-field shapes. We've added a test in `eval/tests/test_call_site_map.py` that verifies the production call_site map stays consistent with the live log; we should add a similar test that verifies golden case field names parse against the actual response schemas. This is a real follow-up.

---

## What we did NOT measure (honest gaps)

1. **`ask_gemma_chat` and `chip` are unevaluated.** Both use `generate_with_tools_loop` with live MCP tool fixtures. Building golden cases requires reproducing the MCP environment, which we deferred for time. Adapters are registered but unseeded. P0 spec coverage: 6 of 8 surfaces.

2. **Narrative quality unscored.** All 6 surfaces tested here are structured JSON. The rubric scorer (Claude Opus 4.7 as judge) exists and is unit-tested, but no narrative surface (`boss_narrative`, `next_steps`, `guidance`) was run through it in this baseline. Plan: run rubric scoring on `next_steps` and `boss_narrative` once Anthropic API access is budgeted.

3. **No human calibration.** The spec called for 50 human-labeled narrative cases to validate Claude-as-judge correlation. We didn't do this. A judge can validly say "your rubric is uncalibrated." Future work.

4. **Single backend, single model.** All runs on Ollama + `gemma4:e4b`. The 26B model would likely score differently; OpenRouter behavior is untested.

5. **Single labeler.** 120 cases were all hand-labeled by the same person (me). Inter-rater reliability is not measured.

---

## Reproducing this run

```bash
cd /path/to/futureproof-data
make eval-test          # 26 scorer unit tests, ~1 sec
make eval-latency       # latency-only across 20 surfaces from existing logs, ~5 sec
make eval-p0-no-rubric  # full 6-surface, 120-case eval, ~7 min, $0
```

Raw results: `eval/results/2026-05-13-183007/summary.json` (initial run) and `eval/results/2026-05-13-183940/summary.json` (career_intent re-run with corrected golden field names).

Code at the eval commit: `eval/runner.py`, `eval/adapters/`, `eval/scorers/`, `eval/golden/*/cases.jsonl`.

---

## Bottom line

The eval works. It runs end-to-end in ~7 minutes with no API spend, and on its first real run it surfaced **two genuine, decision-relevant findings** about Gemma's behavior on FutureProof's most important stats:

1. **Score-3 floor** — Gemma will not commit to "this is bad" (score ≤ 2) on negative cases. We are softening exactly where we said we wouldn't.
2. **RES regression-to-mean** — Gemma collapses every AI-exposure score to 6–8, undercutting the stat that the hackathon's "AI 4 Good" framing depends on most.

Both findings would have been invisible from spot-checking. Both are now testable, attributable to specific cases, and improve-or-don't-improve under any prompt change. **That's what the eval is for.**
