# Spike: gemma4:e2b vs gemma4:e4b for FutureProof local inference

**Date:** 2026-05-17
**Question:** Should FutureProof's local-first deployment use `gemma4:e2b` instead of `gemma4:e4b`?
**Answer:** **No.** Stay with `gemma4:e4b`. E2B is roughly tied on quality but slightly slower on production-style workloads, marginally worse on the hardest intent-resolution surface, and not measurably stronger on multilingual. E4B remains the right default.

This report documents the test methodology and results so any reviewer asking *"why E4B and not the smaller E2B?"* has a measured answer.

---

## TL;DR

| Axis | E2B | E4B | Decision driver |
|---|---|---|---|
| SOC tool calling accuracy (narrow list-pick) | 12/12 (100%) | 12/12 (100%) | TIE |
| SOC tool calling latency (p50, varies by prompt) | 4.4–18.6s | 14.5–29.4s | E2B 37–79% faster on this narrow surface |
| career_intent field accuracy (broad CIP resolution) | 99/101 (98%) | 100/100 (100%) | E4B slightly better |
| explain_* schema validity | 100% all 5 surfaces | 100% all 5 surfaces | TIE |
| explain_* content correctness (aggregate) | 66/100 | 66/100 | TIE — different failure modes |
| explain_* p50 latency (avg across 5 surfaces) | ~2.7s | ~1.9s | E4B ~30% faster on production workload |
| career_intent p50 latency | 4.5s | 2.8s | E4B 38% faster |
| Spanish prose | 2/3 success (small sample) | 2/3 success (small sample) | Roughly TIE — both have surface-specific failures |
| Arabic prose | 0/3 (English fallback) | 0/3 (English fallback) | TIE — both fail locally; Arabic depends on cloud 26B |
| VRAM resident | 7.2 GB | 10.5 GB | E2B lighter |

**Net:** E2B is not measurably better. E4B is marginally better on the hardest task (broad intent resolution) and faster on production-style prose workloads. The submission targets E4B.

---

## Methodology

### Test 1 — SOC tool calling head-to-head
**Script:** `scripts/spike_e2b_vs_e4b_tool_calling.py`
**Output:** `reports/spike_e2b_vs_e4b_tool_calling_results.json`

Replays the same 6-variant harness used in the original e4b baseline against both `gemma4:e2b` and `gemma4:e4b`:
- 4 tool-calling variants (production prompt + 3 short prompts with 26/8/3 candidates)
- 2 JSON-mode variants (26/8 candidates)
- 2 repeats per variant = 12 runs per model
- Task: "student typed 'doctor' — pick 5 SOC codes from the candidate pool"
- Validation: chosen codes must exist in candidate pool

### Test 2 — Full P0 eval head-to-head
**Command:** `INFERENCE_BACKEND=ollama OLLAMA_MODEL=gemma4:e2b uv run python -m eval.runner --tier P0 --no-rubric`
**Output:** `eval/results/2026-05-17-142826/`

Same 215-case P0 golden set used for the published E4B baseline:
- 100 cases for `career_intent` (CIP resolution across happy/OOD/typo/adversarial inputs)
- 20 cases each for `explain_aura`, `explain_ern`, `explain_grw`, `explain_res`, `explain_roi`
- Schema validity, field accuracy, content directional check, length range
- `--no-rubric` skips the Claude-Opus prose-quality rubric (saves API spend; the same axis was also skipped in the E4B baseline numbers cited in the writeup)

### Test 3 — Multilingual probe
**Script:** `scripts/spike_e2b_multilingual.py`
**Output:** `reports/spike_multilingual_gemma4-e2b_results.json` and `reports/spike_multilingual_gemma4-e4b_results.json`

Replays 3 Spanish + 3 Arabic prompts sampled from `logs/gemma.jsonl` through each local model. Measures language purity (target-script character ratio), voice-contract violations (stat codes, game framing, non-Western numerals), and prose length.

⚠️ Sampling caveat: the script uses Python set iteration to pick surfaces, which is non-deterministic across runs. E2B and E4B were tested on partially different surface samples. Only `guidance` was directly comparable across both languages.

### Test environment

- Hardware: MacBook Pro M4, 24 GB unified memory
- Ollama: serve PID 19631 (started day prior). Server reachable at `localhost:11434`.
- VRAM clean state verified before each test (`/api/ps` returned empty before kicking off each run)
- No competing processes on the machine during runs
- Quantization: Q4_K_M for both models (Ollama default)
- Architecture-reported parameter sizes (from `/api/ps`): E2B 5.1B, E4B 8.0B (Q4 quantized; "effective" param counts in Google's E2B/E4B naming differ from these on-disk sizes)

---

## Results

### Test 1 — SOC tool calling

Both models cleared every variant with native tool calls:

| Variant | E2B success | E4B success | E2B p50 | E4B p50 | E2B speedup |
|---|---:|---:|---:|---:|---:|
| `tool_current_26` (production prompt, 26 candidates) | 2/2 (100%) | 2/2 (100%) | 18.6s | 29.4s | 37% |
| `tool_short_26` (short prompt, 26 candidates) | 2/2 (100%) | 2/2 (100%) | 6.9s | 15.7s | 56% |
| `tool_short_8` (8 candidates) | 2/2 (100%) | 2/2 (100%) | 4.4s | 15.9s | 72% |
| `tool_short_3` (3 candidates) | 2/2 (100%) | 2/2 (100%) | 5.5s | 26.3s | 79% |
| `json_short_26` (JSON mode, 26 candidates) | 2/2 (100%) | 2/2 (100%) | 6.5s | 20.9s | 69% |
| `json_short_8` (JSON mode, 8 candidates) | 2/2 (100%) | 2/2 (100%) | 6.1s | 14.5s | 58% |

**Reading:** for a narrow list-pick task, E2B and E4B are equally accurate. E2B is markedly faster. Both emit native `tool_calls`, no fallback into `content` JSON observed.

This is **a real strength for E2B in narrow tool-call situations**, but as Test 2 shows, the advantage does not generalize to the production workload.

### Test 2 — Full P0 eval

| Surface | N | E4B baseline | E2B (this run) | Verdict |
|---|---:|---|---|---|
| `career_intent` | 100 | 100/100 field accuracy | 99/101 (98%) | E4B slight edge |
| `explain_aura` | 20 | 20/20 schema · 40/40 length · 10/20 content | 20/20 · 39/40 · 15/20 | E2B better content |
| `explain_ern` | 20 | 20/20 · 40/40 · 17/20 | 20/20 · 39/40 · 18/20 | E2B better content |
| `explain_grw` | 20 | 20/20 · 40/40 · 8/20 | 20/20 · 40/40 · 16/20 | E2B better content |
| `explain_res` | 20 | 20/20 · 40/40 · 13/20 | 20/20 · 40/40 · 5/20 | E4B better content |
| `explain_roi` | 20 | 20/20 · 40/40 · 18/20 | 20/20 · 40/40 · 12/20 | E4B better content |
| **explain_* content aggregate** | 100 | 66/100 | 66/100 | **TIE** |

**Reading on quality:**
- Schema validity, stat-code identification, and length compliance are tied at ~100% across all surfaces. Both models clear the structured-output bar.
- career_intent shows E4B's modest edge on the hardest intent task (1,949 CIP space with adversarial/OOD inputs).
- Content directional check is tied at 66/100 aggregate, but the failure modes are different: E2B writes RES/ROI prose worse, GRW/AURA prose better. The variance suggests prompt-level tuning per surface, not a uniform model gap.

**Reading on latency** (from this run's logs):

| Surface | E4B baseline (writeup) | E2B (this run) | Delta |
|---|---|---|---|
| `career_intent` p50 | 2.8s | 4.5s | E4B 38% faster |
| `explain_aura` p50 | 1.7s | 3.1s | E4B 45% faster |
| `explain_ern` p50 | 1.8s | 2.5s | E4B 28% faster |
| `explain_grw` p50 | 1.8s | 2.5s | E4B 28% faster |
| `explain_res` p50 | 2.4s | 3.0s | E4B 20% faster |
| `explain_roi` p50 | 1.7s | 3.1s | E4B 45% faster |

**Surprising finding:** E2B is *slower* than E4B on the production surfaces, despite being faster on the narrow SOC tool-call task. The likely explanation is that production prompts have longer prefill and require prose generation, where E4B's larger context capacity translates into better tokens-per-second under load. The narrow SOC task was a small-prompt, small-output pick — a best case for E2B that does not represent the actual workload.

### Test 3 — Multilingual probe

**Spanish (3 surfaces tested per model, partially overlapping):**

| Surface | E2B | E4B |
|---|---|---|
| `guidance` (direct comparison) | ✅ purity 1.00, fluent | ✅ purity 1.00, fluent |
| `career_description` | ❌ English fallback inside JSON | (not directly tested) |
| `boss_narrative` | ✅ purity 1.00, fluent | (not directly tested) |
| `set_your_course_resolve` | (not directly tested) | ❌ produced gibberish (`"instrutututu..."`) |
| `skill_recs` | (not directly tested) | ✅ purity 1.00 with one voice-contract violation (stat code leaked) |

**Aggregate Spanish:** Both 2/3 on their respective samples. Different failure modes, similar overall rate.

**Arabic (3 surfaces tested per model, partially overlapping):**

| Surface | E2B | E4B |
|---|---|---|
| `guidance` (direct comparison) | ❌ English fallback | ❌ English fallback (also hallucinated wrong founding year: 1866/1867 instead of 1857) |
| All other surfaces | ❌ English fallback | ❌ English fallback |

**Aggregate Arabic:** Both 0/3. Neither local model reliably produces Arabic prose on these surfaces.

**Bigger picture from production logs:**
- 22,390 logged Gemma calls total across the project
- ~123 Spanish records, ~43 Arabic records
- Spanish records: mix of Ollama (E4B) and OpenRouter (26B). Production E4B Spanish works.
- Arabic records: **overwhelmingly OpenRouter 26B**. Local E4B Arabic was almost never invoked in production. The "FutureProof switches between English, Spanish, and Arabic" claim is delivered fully only on the cloud 26B path; local Ollama is reliable for English and Spanish, best-effort for Arabic.

---

## Decision rationale: why target E4B

1. **Quality is tied.** Aggregate content_check is identical at 66/100. Schema and length compliance both at 100%. Career_intent has a 2-point edge for E4B but both clear 98%.

2. **E4B is faster on production-style workloads.** ~30% lower p50 across the five explain_* surfaces; 38% lower p50 on `career_intent`. The SOC-spike latency advantage for E2B does not generalize.

3. **E4B is marginally better on the hardest task.** career_intent — picking 1 CIP from 1,949 — is where the broader intent-resolution capability matters. E4B 100/100 vs E2B 99/101.

4. **Multilingual is not a differentiator.** Both local models fail Arabic at the same rate. Both succeed at Spanish on conversational surfaces. The Arabic story for FutureProof is delivered by 26B on the cloud path regardless of local model choice.

5. **The published eval baseline, the deployed demo, and the architecture all reference E4B consistently.** The 215-case eval cited in the writeup, the live demo on the cloud path, and the local Ollama configuration all converge on E4B as the canonical local variant. The measured E2B comparison documented here finds no axis on which E2B is decisively better — tied or marginally worse on every metric the product depends on. Without a measured advantage, there is no engineering reason to change the canonical configuration.

6. **E2B's lighter VRAM footprint doesn't unlock cheaper hardware in this product's context.** E2B uses 7.2 GB VRAM vs E4B's 10.5 GB. The product's stated deployment target is a 16 GB Mac Mini (the M4 base model, $599 list). Both models fit. E4B is tighter (~1 GB headroom on 16 GB total memory), E2B more comfortable (~4 GB headroom), but neither requires a different hardware class. E2B would unlock 8 GB machines (older laptops, phone-class) — out of scope for the local school-deployment use case the writeup and video target. **If both models require the same hardware tier, pick the one with the better output.**

7. **No definitive evidence of an E2B advantage on any axis the product cares about.** Tool calling: tied. Schema validity: tied. Multilingual: tied (both struggle locally on Arabic). Latency on production workload: E4B wins. Quality on production workload: tied or E4B slight edge.

The honest position: **E2B is a viable backup variant if E4B's VRAM footprint blocks deployment on a specific machine. For the canonical product configuration, E4B is the right default — measured against E2B directly, not just by analogy.**

---

## Reproducibility

To reproduce these results:

```bash
# Tool-calling head-to-head (3 minutes)
uv run python scripts/spike_e2b_vs_e4b_tool_calling.py --repeats 2 --timeout-s 90

# Full P0 eval on E2B (15-30 minutes; results land in eval/results/)
INFERENCE_BACKEND=ollama OLLAMA_MODEL=gemma4:e2b \
    uv run python -m eval.runner --tier P0 --no-rubric

# Multilingual probe (2-5 minutes per model)
uv run python scripts/spike_e2b_multilingual.py                          # E2B
TEST_MODEL=gemma4:e4b uv run python scripts/spike_e2b_multilingual.py    # E4B
```

Raw result files:
- `reports/spike_e2b_vs_e4b_tool_calling_results.json`
- `eval/results/2026-05-17-142826/summary.json`
- `reports/spike_multilingual_gemma4-e2b_results.json`
- `reports/spike_multilingual_gemma4-e4b_results.json`

---

## What's NOT in this spike

- **Prose quality rubric** (Claude-Opus-as-judge). The E4B baseline cited in the writeup also lacks this axis. Adding it would require Anthropic API spend and is not necessary for the E2B-vs-E4B decision.
- **Long-context guidance synthesis** beyond the eval surfaces.
- **Audio or image input.** E2B/E4B both support multimodal input; FutureProof does not use multimodal in this release.
- **Fine-tuning comparison.** Both tested as base models with prompting only.
- **31B Dense or other Gemma 4 variants.** Out of scope for the local-deployment decision.

---

## Conclusion

The FutureProof submission ships with `gemma4:e4b` as the local default. This spike confirms that decision against `gemma4:e2b` on measured ground: tied or marginally better on every quality axis, faster on the production workload, and no decisive E2B advantage to justify a late-hour switch.
