# Gemma 4 Model Options for FutureProof

## Model Family

| Model | Total Params | Active Params | Type | Best For |
|---|---|---|---|---|
| **E2B** | ~2B | 2B | Dense (edge) | Mobile, IoT, Raspberry Pi. Audio + vision. Offline, near-zero latency. |
| **E4B** | ~4B | 4B | Dense (edge) | Laptops, tablets. Audio + vision. Local dev, moderate tasks. |
| **26B-A4B** | 26B | ~4B | MoE | Desktop with 16GB+ RAM. Near-31B quality at E4B-level speed. The sweet spot. |
| **31B** | 31B | 31B | Dense | Cloud/server. Maximum quality. Best benchmarks (AIME 89.2%, LiveCodeBench 80.0%). |

All models support: text, vision (images/video), 140 languages, native function calling, fine-tuning. The E2B/E4B models also support native audio input.

## FutureProof Deployment Strategy

### Live Demo (Kaggle-hosted or cloud GPU)
**Recommended: 26B-A4B (MoE)**
- Near-31B quality but only activates 4B params per token — fast and cheap
- Native function calling (critical for MCP tool-use architecture)
- Fits on a single GPU easily for Kaggle notebooks
- The 7 Gemma agent roles (stat calculator, boss fight engine, branch tree generator, etc.) all benefit from speed over raw ceiling
- **31B Dense** as fallback if quality on complex tasks (branch tree generation, multi-stat projection) isn't sufficient with 26B-A4B

### Ollama Track Demo (local)
**Recommended: E4B**
- Runs on any laptop — demonstrates the equity narrative ("any school can run this")
- Supports function calling for the MCP tool interface
- Shows the product works without cloud dependency

### Video Strategy
Show all three tiers to demonstrate full deployment spectrum:
- E4B on a laptop (equity / Ollama track)
- 26B-A4B on a desktop (power user)
- Cloud-hosted for the live demo (reliability)

This plays well for both the Ollama track ($10K) and the Digital Equity & Inclusivity narrative ($10K).

## Sources

- [Gemma 4 — Google DeepMind](https://deepmind.google/models/gemma/gemma-4/)
- [Gemma 4 on Kaggle](https://www.kaggle.com/models/google/gemma-4)
- [Gemma 4 Model Variants Explained](https://docs.bswen.com/blog/2026-04-03-gemma-4-model-variants-explained/)
- [Gemma 4 Blog Post](https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/)
