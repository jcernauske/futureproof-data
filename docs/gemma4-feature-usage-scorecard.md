# Gemma 4 Feature Usage Scorecard

Date: 2026-04-30

Related docs:

- `docs/hackathon_rules.txt`
- `docs/rules2.txt`
- `docs/gemma4-features-hackathon-report.md`

## Overall Score

FutureProof is using Gemma 4 in a high-leverage way: **8.5 / 10**.

The project’s strongest use of Gemma 4 is **agentic, grounded reasoning**, not generic chat. That is the right center of gravity for the Gemma 4 Good Hackathon because the stored rules reward real-world impact, functional technology, and innovative use of Gemma 4’s unique capabilities.

## Feature-by-Feature Scorecard

| Gemma 4 Feature | Score | Assessment |
|---|---:|---|
| Advanced reasoning | **9 / 10** | Strong. Major intent resolution, career tiering, SOC expansion, boss/skill reasoning, and Ask Gemma all require interpretation over structured data. |
| Function calling / tools | **9 / 10** | Strongest technical story. `gemma_client`, `ask_gemma`, `set_your_course`, and MCP-style data tools show real agentic workflows. |
| Structured JSON / system prompting | **8.5 / 10** | Strong. Prompts demand structured tails, tool args, validated outputs, fallbacks, and language constraints. |
| Local-first / Ollama | **7.5 / 10** | Implemented well in code via `INFERENCE_BACKEND=ollama`, default `gemma4:e4b`, and native Ollama `think:false`. Needs judge-visible README/video proof. |
| Long context | **7 / 10** | Credible but under-shown. Ask Gemma loads rich build context, but the submission should frame this as context headroom, not huge-prompt usage. |
| Multilingual / inclusivity | **8.5 / 10** | Strong. The app has an English/Spanish language selector, localized frontend strings, localized profile names, persisted locale state, and backend Gemma prompts that generate student-facing prose in Spanish while preserving canonical data values. Not a 10 because it supports Spanish rather than broad 140-language coverage, and judges still need to see it demonstrated. |
| Multimodal | **2 / 10** | Mostly unused. Do not pitch FutureProof as a multimodal entry unless a real multimodal feature ships. |
| Fine-tuning / domain adaptation | **2 / 10** | Not central. That is acceptable. The project’s strength is agentic retrieval and grounded tool use, not model training. |
| Safety / trust / grounding | **8.5 / 10** | Strong. Deterministic scoring, public data, receipts, schemas, fallbacks, and logs make this more trustworthy than a freeform counselor bot. |

## High-Leverage Usage Verdict

The project’s Gemma usage is high-leverage because Gemma is doing work that deterministic code cannot handle cleanly:

- translating messy student intent into official program and career structures
- deciding when to call tools
- interpreting grounded outputs for a student
- generating concrete skill and action recommendations from build context
- supporting local/private deployment through Ollama

That is much stronger than wrapping a chatbot around a dataset.

## Strongest Gemma 4 Alignment

### 0. Student-facing multilingual access

FutureProof has a real Spanish-language product surface, not just a future plan:

- `frontend/src/i18n/strings.ts` carries English and Spanish strings for the core app flow.
- `frontend/src/screens/ProfileScreen.tsx` exposes an English / Español segmented language control.
- `frontend/src/store/profileStore.ts` persists locale state across the student session.
- `backend/app/services/locale.py` threads Spanish instructions into Gemma prompts and fallback copy.
- Gemma-generated surfaces such as guidance, boss narratives, skill recommendations, Ask Gemma, career-pick Q&A, and next steps receive the selected locale.

This materially strengthens the **Digital Equity & Inclusivity** track. The best claim is that FutureProof can translate the student-facing app experience and Gemma-generated guidance into Spanish while preserving official school names, occupation titles, source acronyms, dollar amounts, percentages, and machine-readable JSON fields.

### 1. Agentic reasoning over governed data

FutureProof’s best technical story is that Gemma 4 does not answer from vibes. It operates inside a bounded system:

- public education and labor-market data
- MCP-style data tools
- validated arguments
- structured outputs
- deterministic score computation
- fallback paths when Gemma fails or returns unusable output

This maps directly to the hackathon’s Technical Depth & Execution criterion.

### 2. Function calling as product behavior

The tool-calling story is not an implementation detail; it is a product differentiator.

Best framing:

> FutureProof uses Gemma 4 to decide when the student’s question requires live data, call the right governed tool, and then translate the result into plain language.

Avoid framing this as:

> FutureProof has an AI chat assistant.

The first is specific to Gemma 4’s agentic capabilities. The second sounds generic.

### 3. Local-first access through Ollama

The repo has a credible Ollama story:

- `INFERENCE_BACKEND=ollama|openrouter`
- default local model: `gemma4:e4b`
- native Ollama `/api/chat` path for `think:false`
- shared application path for hosted and local inference

This supports both the Ollama special technology track and the Digital Equity & Inclusivity impact story.

The gap is packaging: judges need to see the Ollama path quickly in the README and video.

## Weaker or Unused Gemma 4 Features

### Multimodal

Gemma 4’s multimodal capabilities are mostly unused in this project. That is not fatal because the rules do not require every Gemma 4 feature, but the submission should not overclaim here.

Safe claim:

> FutureProof’s current submission focuses on text, tool use, and data-grounded reasoning. Gemma 4’s multimodal capabilities create a future path for transcripts, worksheets, course catalogs, and counselor documents.

Avoid:

> FutureProof is a multimodal Gemma 4 app.

### Fine-tuning

FutureProof does not appear to rely on fine-tuning or Unsloth. That is acceptable. The project should not chase this unless there is a clear, finished, reproducible fine-tuned model before submission.

The stronger choice is to lean into:

- agentic retrieval
- local deployment
- grounded public data
- structured reasoning

## Judge-Visible Gaps

The main risk is that the implementation is stronger than the way the repo currently presents it.

Priority gaps:

1. The public README should lead with the product and Gemma 4 implementation, not the data pipeline.
2. Add a visible “Gemma 4 Surfaces” table:
   - intent resolution
   - tool calling
   - career tiering
   - Ask Gemma
   - boss narratives
   - skill recommendations
   - next steps
   - Ollama local mode
3. Add an Ollama quickstart near the top of the README.
4. Add one architecture diagram:
   - frontend
   - FastAPI backend
   - Gemma client
   - Ollama / OpenRouter
   - governed MCP-style data tools
   - public data warehouse
5. In the video, show at least one tool-grounded Gemma moment and one local-Ollama proof moment.
6. In the video or screenshot gallery, show the Spanish toggle and one Spanish Gemma response. This is an easy Digital Equity proof point.

## Recommended Submission Claims

Use:

- “Agentic, data-grounded career decision support built on Gemma 4.”
- “Gemma 4 resolves messy student intent, uses structured tool calls against governed public data, and explains tradeoffs in plain language.”
- “The same inference abstraction supports hosted Gemma 4 and local Gemma 4 through Ollama.”
- “FutureProof keeps scores deterministic and uses Gemma for interpretation, routing, and coaching rather than ungrounded prediction.”

Avoid:

- “Fully autonomous counselor.”
- “Financial advice.”
- “Multimodal submission,” unless a real multimodal surface ships.
- “Runs on mobile,” unless a true mobile/on-device runtime is demonstrated.
- “Every in-app model call uses external MCP transport.” A more precise claim is that FutureProof exposes MCP-style governed tools and uses the same tool schemas inside the backend.

## Bottom Line

FutureProof has excellent use of Gemma 4’s agentic and local-first strengths. It is weak on multimodal and fine-tuning, but those are not necessary for this entry to be competitive.

The highest-leverage next step is not adding more Gemma features. It is making the existing Gemma usage obvious, reproducible, and judge-visible.
