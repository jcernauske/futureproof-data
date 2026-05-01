# Gemma 4 Feature Report for Hackathon Positioning

Date: 2026-04-30

Purpose: summarize Gemma 4 capabilities from current public sources and map them to the Gemma 4 Good Hackathon rules captured in `docs/hackathon_rules.txt` and `docs/rules2.txt`.

## Sources Reviewed

- Google DeepMind Gemma 4 page: https://deepmind.google/models/gemma/gemma-4/
- Google Keyword launch post, "Gemma 4: Byte for byte, the most capable open models": https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/
- Google AI for Developers Gemma 4 model card: https://ai.google.dev/gemma/docs/core/model_card_4
- Google AI for Developers Gemma overview: https://ai.google.dev/gemma/docs
- Google AI for Developers Ollama integration guide: https://ai.google.dev/gemma/docs/integrations/ollama
- Ollama Gemma 4 model page: https://ollama.com/library/gemma4

## Executive Summary

Gemma 4 is positioned by Google DeepMind as its most capable open model family, built from Gemini 3 research and optimized for intelligence per parameter. For the hackathon, the most relevant capabilities are not generic chat quality; they are local deployment, native function calling, structured outputs, long context, multimodal input, multilingual support, and fine-tuning or domain adaptation paths.

FutureProof already aligns with the strongest parts of that positioning. The project is an agentic, data-grounded education product where Gemma 4 maps messy student intent to real program and labor-market data, calls structured tools, explains risk tradeoffs, and can run locally through Ollama. That maps directly to the competition's emphasis on real-world impact, Future of Education, Digital Equity & Inclusivity, Safety & Trust, and the Ollama special technology track.

## Gemma 4 Capabilities That Matter for This Entry

### 1. Advanced reasoning and planning

Google describes Gemma 4 as purpose-built for advanced reasoning and agentic workflows. The launch post calls out multi-step planning, deep logic, math, instruction following, and coding improvements.

FutureProof relevance:

- Major intent resolution is a reasoning task, not a lookup. The model must infer that "pre-med" may map to Biology, or that a student asking for "deaf ed" is naming a sub-focus inside a broader Special Education program.
- Career tiering asks Gemma to judge plausibility across school, program, labor-market, and education signals.
- Ask Gemma uses loaded build context and tools to answer follow-up questions without inventing numbers.

Best writeup phrasing:

> FutureProof uses Gemma 4's reasoning ability to translate plain student language into governed education and labor-market decisions, then explain the consequences in student-readable terms.

### 2. Native function calling and structured JSON

Google's launch post explicitly names function calling, structured JSON output, and native system instructions as Gemma 4 features for autonomous agents. The model card also lists function calling as a core capability.

FutureProof relevance:

- `backend/app/services/gemma_client.py` implements tool-calling support and multi-turn tool loops.
- `backend/app/services/ask_gemma.py` allowlists governed data tools for questions beyond the loaded build.
- `backend/app/services/set_your_course.py` uses a tool-grounded "Not what I expected" debugging flow.
- The MCP server in `src/mcp_server/futureproof_server.py` exposes real career-data tools, including career paths, occupations, AI exposure, regional cost of living, and career branches.

Judging angle:

This should be shown as "Gemma calls tools against public data" rather than "Gemma chats about careers." The latter sounds generic; the former directly addresses the Technical Depth & Execution rubric.

### 3. Local-first deployment and Ollama support

The hackathon includes an Ollama special track for the best project that showcases Gemma 4 running locally via Ollama. Google AI's Ollama guide says Ollama can run Gemma on laptops or small devices with reduced compute through quantized GGUF models, and lists Gemma 4 tags for E2B, E4B, 26B, and 31B. Ollama's page lists Gemma 4 models with 128K context for E2B/E4B and 256K context for 26B/31B.

FutureProof relevance:

- The app already supports `INFERENCE_BACKEND=ollama|openrouter`.
- The default local model is `gemma4:e4b`.
- Local mode is important to the education/equity story: a school, counselor, or community program can run AI guidance without sending student inputs to a hosted LLM provider.

Best video moment:

Show one short split-screen or terminal proof that the same app path can run through Ollama locally. The claim should be precise: the cloud demo may use OpenRouter, but the codebase supports local Gemma 4 through Ollama.

### 4. Efficient model family across edge and workstation tiers

Google describes four model sizes: E2B, E4B, 26B A4B MoE, and 31B Dense. The smaller E models are built for mobile and edge efficiency; the larger models target consumer GPUs, workstations, and local-first AI servers. The model card lists E2B/E4B at 128K context, and 26B A4B/31B at 256K context.

FutureProof relevance:

- E4B via Ollama is a credible local demo target.
- 26B A4B is a good cloud/high-quality target because it has a sparse MoE design and activates a smaller subset of parameters during inference.
- The project can frame model choice as a deployment tradeoff: E4B for local school privacy, 26B/31B for higher-quality hosted demos.

Important caveat:

Do not claim the app is mobile-native or LiteRT-based unless that path is actually implemented. For this project, the honest special-track fit is Ollama, not LiteRT or Cactus.

### 5. Long context

Gemma 4 supports long context windows: 128K tokens on E2B/E4B and 256K tokens on 26B A4B/31B, according to Google AI's model card and Google DeepMind's model page.

FutureProof relevance:

- Ask Gemma can load a rich build context: school, program, selected career, stats, boss results, skills, branches, receipts, and comparison state.
- The writeup can explain that long context helps preserve full decision context during counseling-style follow-up, reducing the need to over-compress the student's situation.

Avoid overclaiming:

If the app currently sends compact context blocks rather than massive prompts, say "Gemma 4's long context gives headroom for richer build context" rather than implying the current demo consumes 128K or 256K prompts.

### 6. Multimodal input

Google's sources describe Gemma 4 as multimodal. The model card says all models process text and image input, with audio supported on E2B and E4B; it also lists image understanding, video frame analysis, interleaved text-image input, and audio capabilities for E2B/E4B.

FutureProof relevance:

- Current app strength is not multimodal. Do not force this into the central pitch unless a real visual/audio feature ships.
- A modest future-facing line is safe: Gemma 4's multimodal stack could later support transcript, worksheet, course catalog, or counselor-document inputs.

Hackathon implication:

The absence of multimodal use is not fatal because the rules do not require every Gemma 4 capability. But if competing entries lean heavily on vision/audio, FutureProof must win on impact, tools, grounding, and local-first deployment.

### 7. Multilingual and inclusivity support

Google says Gemma 4 supports over 140 languages. The model card distinguishes broad pretraining across 140+ languages and out-of-the-box support for 35+ languages.

FutureProof relevance:

- This strengthens the Digital Equity & Inclusivity angle.
- If the app's locale support is demonstrable, it should be shown as a practical inclusion feature: career guidance can be delivered in the student's preferred language.
- If multilingual UI coverage is partial, frame it accurately as "Gemma-backed multilingual guidance support" rather than complete localization.

### 8. Safety, transparency, and responsible use

Google DeepMind's Gemma page emphasizes safety and security protocols. The general Gemma page also warns that LLM outputs can be inaccurate and should not be used as substitutes for professional advice in sensitive domains.

FutureProof relevance:

- FutureProof has a strong Safety & Trust story because deterministic public data drives the scores while Gemma explains, routes, and summarizes.
- Receipts, source attribution, tool schemas, validation, fallbacks, and JSONL logs are stronger than generic disclaimers.
- The app should still avoid presenting itself as financial advice. It is decision support using public data, not a counselor, lender, or financial advisor.

## Mapping to Hackathon Rules

The stored rules evaluate:

- Impact & Vision: 40 points
- Video Pitch & Storytelling: 30 points
- Technical Depth & Execution: 30 points

### Impact & Vision

FutureProof's best impact claim:

> Students make expensive, life-shaping education decisions using fragmented data and opaque taxonomies. FutureProof uses Gemma 4 to turn a student's plain-language goal into data-backed college and career tradeoffs they can understand.

Strongest tracks:

- Future of Education: direct fit.
- Digital Equity & Inclusivity: strong if the story emphasizes low-cost access, plain-language interfaces, multilingual support, and local deployment.
- Safety & Trust: credible if receipts, deterministic scoring, and source provenance are visible.
- Ollama: credible special-track fit if the video or repo clearly demonstrates local Gemma 4 via Ollama.

### Video Pitch & Storytelling

The video should make Gemma 4 visibly indispensable in three moments:

1. A student types a messy major/career phrase.
2. Gemma resolves the intent and calls/uses governed data instead of guessing.
3. The student receives a concrete, data-grounded tradeoff or action plan.

Avoid spending video time on generic architecture diagrams unless they clarify the above story quickly.

### Technical Depth & Execution

The writeup and README should foreground:

- Gemma 4 model choices: Ollama `gemma4:e4b` locally, OpenRouter `google/gemma-4-26b-a4b-it` or equivalent for hosted demo if used.
- Tool calling: which flows call tools, which data tools exist, and how arguments are validated.
- Grounding: deterministic public data, receipts, and fallback behavior.
- Local-first: exact setup commands for Ollama.
- Reproducibility: environment variables, backend/frontend startup, test commands, and seed/demo path.

## Recommended Claims for Submission

Use:

- "Agentic, data-grounded career decision support built on Gemma 4."
- "Gemma 4 resolves messy student intent, uses structured tool calls against governed public data, and explains the tradeoffs in plain language."
- "The same inference abstraction supports hosted Gemma 4 and local Gemma 4 through Ollama."
- "FutureProof keeps scores deterministic and uses Gemma for interpretation, routing, and coaching rather than ungrounded prediction."

Avoid:

- "Fully autonomous counselor."
- "Financial advice."
- "Every in-app model call uses external MCP transport." The more precise claim is that FutureProof exposes MCP-style governed tools and uses the same tool schemas inside the backend.
- "Multimodal submission" unless a real multimodal surface ships.
- "Runs on mobile" unless a mobile/on-device runtime is actually demonstrated.

## Gaps to Close Before Submission

1. Public README should lead with the product and Gemma 4 implementation, not the data pipeline.
2. Add an Ollama quickstart near the top of the README.
3. Add a short architecture diagram showing: frontend -> backend -> Gemma client -> Ollama/OpenRouter -> MCP/governed data tools.
4. In the Kaggle writeup, explicitly map each Gemma 4 feature used to a product surface.
5. In the video, show at least one tool-grounded Gemma moment and one local-Ollama proof moment.
6. Keep multimodal as future work unless implemented.

## Source Notes

- Google DeepMind Gemma 4 page: model sizes, agentic workflows, multimodal reasoning, 140-language support, efficient architecture, benchmark table, E2B/E4B offline edge positioning, 26B/31B local-first workstation positioning, safety, and download/integration surfaces.
- Google Keyword launch post: launch framing, Apache 2.0 accessibility, four model sizes, reasoning, function calling, structured JSON, native system instructions, coding, vision/audio, long context, and 140+ languages.
- Google AI model card: detailed model architecture, context windows, modalities, model variants, core capabilities, thinking mode, function calling, coding, image/video/audio support, benchmark table, and best-practice notes.
- Google AI Ollama guide: local setup, quantized low-compute runtime rationale, model tags, and text/image generation examples.
- Ollama model page: available tags, practical local model sizes, context windows, input modality listing, and Ollama-specific usage examples.
