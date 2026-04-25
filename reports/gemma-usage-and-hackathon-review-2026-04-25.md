# Gemma Usage and Hackathon Review

Date: 2026-04-25

## Sources Reviewed

- Kaggle competition page and local rule captures:
  - `docs/hackathon_rules.txt`
  - `docs/rules2.txt`
  - Competition URL: https://www.kaggle.com/competitions/gemma-4-good-hackathon
- Kaggle official announcement post: https://www.linkedin.com/posts/kaggle_now-available-on-kaggle-gemma-4-in-partnership-activity-7445505784228073472-QYnt
- Google Gemma 4 launch post: https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/

## Contest Rules and Submission Requirements

The project is eligible for the Gemma 4 Good Hackathon if the final Kaggle Writeup is submitted by May 18, 2026 at 11:59 PM UTC. The required submission package is:

- A Kaggle Writeup, 1,500 words max, with selected track.
- Public video, 3 minutes or less, preferably YouTube, visible without login.
- Public code repository or Kaggle Notebook, visible without login or paywall.
- Live demo URL or demo files, visible without login or paywall.
- Media gallery with a required cover image.

Judging weights:

- Impact and Vision: 40 points.
- Video Pitch and Storytelling: 30 points.
- Technical Depth and Execution: 30 points.

Tracks aligned to this project:

- Main Track: broad overall prize fit.
- Digital Equity and Inclusivity: strongest impact fit if the story centers high-school students, public data, explainability, and low-cost/local deployment.
- Future of Education: also strong, especially if positioned as decision support for students and counselors.
- Safety and Trust: credible secondary angle due to receipts, deterministic data products, fallback behavior, audit logs, and AI-estimated caveats.
- Ollama Special Technology Track: strong fit because the code supports `INFERENCE_BACKEND=ollama` and defaults local runtime to `gemma4:e4b`.

Rules to watch:

- Team size max is 5.
- One final submitted Writeup per team.
- Winning submission/source-code license obligation is CC-BY 4.0/open source, with reproducibility details.
- External data/tools are allowed if reasonably accessible and low/minimal cost; public data sources and Ollama/OpenRouter should be documented explicitly.
- Public repo must clearly show Gemma 4 implementation. This report should be linked or summarized in the writeup.

## Gemma 4 Features to Showcase

From Google's launch post, Gemma 4's highest-value features for this app are:

- Advanced reasoning: multi-step planning and logic.
- Agentic workflows: native function calling, structured JSON output, and system instructions.
- Local-first deployment: open weights, Apache 2.0 license, Ollama support, and hardware-flexible model sizes.
- Efficient model range: E2B/E4B for edge and mobile; 26B MoE for lower-latency high quality; 31B Dense for highest quality.
- Long context: 128K on edge models and up to 256K on larger models.
- Multimodal capability: image/video across the family and native audio input on E2B/E4B.
- Multilingual reach: 140+ languages.

Best competitive story for FutureProof:

FutureProof is not a chatbot. It is an agentic, data-grounded career decision system where Gemma 4 resolves messy student intent, calls tools against governed public data, explains tradeoffs in plain language, and can run locally via Ollama for schools with privacy, budget, or connectivity constraints.

## Gemma Runtime Architecture

Primary implementation: `backend/app/services/gemma_client.py`.

- Backend switch: `INFERENCE_BACKEND=ollama|openrouter`.
- Default cloud model: `google/gemma-4-26b-a4b-it`.
- Default local model: `gemma4:e4b`.
- Ollama path uses native `/api/chat` with `think: false` because the OpenAI-compatible Ollama endpoint does not reliably disable Gemma 4 thinking mode.
- Async calls share a module-level semaphore controlled by `GEMMA_MAX_CONCURRENCY`.
- Every call is appended to `logs/gemma.jsonl` unless `GEMMA_LOG_DISABLED=1`.
- The client supports:
  - single-turn generation,
  - multi-turn chat,
  - streaming generation,
  - one-shot tool calling,
  - multi-turn tool-calling loops with tool-result dispatch.

This is the most important code to show judges. It proves Ollama/local mode and OpenRouter/cloud mode share the same application path.

## Product Surfaces Using Gemma

### 1. Free-text Major Resolution

Files:

- `backend/app/services/intent.py`
- `backend/app/services/set_your_course.py`
- frontend surfaces in `frontend/src/screens/SetYourCourseScreen.tsx`, `frontend/src/components/school/MajorInput.tsx`, and `frontend/src/hooks/useSetYourCourse.ts`

What Gemma does:

- Maps student input like "pre-med", "business", "deaf ed", or "marketing" to a real CIP program.
- Emits structured JSON: matched CIP, title, confidence, parent CIP, alternatives, reasoning.
- Uses deterministic seed plus `temperature=0` for stable demo behavior.
- Provides streamed prose-first resolution in Set Your Course, then a machine-readable JSON tail.
- Runs a separate audit prompt to catch joke/adversarial or implausible mappings.

Guardrails:

- Candidate CIPs come from school programs plus national crosswalk data.
- Backend sanitizes alternatives, promotes accidental 4-digit CIP family output to a leaf when possible, validates format, and falls back on failure.
- UI exposes confidence and alternatives rather than silently forcing a match.

### 2. "Not What I Expected" Tool-Calling Debug Flow

Files:

- `backend/app/services/set_your_course.py`
- `backend/app/services/gemma_client.py`
- `backend/app/services/mcp_client.py`
- `src/mcp_server/futureproof_server.py`

What Gemma does:

- Classifies the student's clarification into a debug bucket.
- Decides whether to call `get_career_paths`.
- Uses a real tool-calling loop, dispatches to the MCP server, reads the tool result, and produces student-facing reasoning.
- Can update the resolution or confirm a narrower focus after tool verification.

This is the strongest native-function-calling showcase in the repo.

### 3. SOC Universe Expansion

File: `backend/app/services/soc_expansion.py`

What Gemma does:

- When the CIP-SOC crosswalk misses careers implied by student intent, Gemma chooses up to 5 SOCs from a prefiltered candidate pool using the `expand_socs` tool schema.
- Example: biology + pre-med can add physician-oriented SOCs if the base crosswalk misses them.

Guardrails:

- Candidate pool is built from `consumable.occupation_profiles`.
- Gemma may only pick SOCs from the pool.
- Output is filtered against valid SOC format and candidate membership.
- Failure returns the original SOC list unchanged.

### 4. Career Tiering

File: `backend/app/services/career_tiering.py`

What Gemma does:

- Groups matched careers into Common, Less Common, and Stretch tiers.
- Incorporates school, program, regional labor market, education level, and student intent keywords.

Guardrails:

- Gemma can only place SOCs from the provided list.
- Parser drops unknown SOCs and catches unplaced SOCs into Stretch.
- For small lists or failed output, deterministic fallback shows all careers.

### 5. Gemma's Take and Ask Gemma Chat

File: `backend/app/services/guidance.py`

What Gemma does:

- Generates the headline personalized narrative from school, major, career, stats, boss results, and branches.
- Powers freeform Ask Gemma chat with the full build context loaded.

Guardrails:

- Prompt forbids stat-code leakage, game framing, score fractions, and invented numbers.
- Fallback narrative exists when Gemma is unreachable.

### 6. Boss Fight Narratives and Reroll Commentary

File: `backend/app/services/boss_fights.py`

What Gemma does:

- Writes each fight narrative after deterministic Python scoring.
- Writes reroll commentary after the student equips skills.
- Writes final wrap-up after all skills for a challenge are used.

Guardrails:

- Scoring is deterministic; Gemma only interprets.
- Unknown/no-data results skip Gemma entirely and use static copy.
- Transport failures fall back to deterministic narratives.

### 7. Personalized Skill Pool

File: `backend/app/services/skill_pool.py`

What Gemma does:

- Generates a build-specific skill pool for losing/drawn fights.
- Each skill carries machine-readable stat deltas and rationale.

Guardrails:

- Fallback pool fills missing/failed generation.
- Parser normalizes output into `AppliedSkill` structures.

### 8. Skill Recommendations

File: `backend/app/services/skill_recs.py`

What Gemma does:

- Produces 3-5 concrete in-school actions.
- Emits a machine-readable stat impact (`ERN`, `ROI`, `RES`, `GRW`, `HMN`) plus plain-language rationale.

Guardrails:

- Parser clamps excessive positive deltas.
- Deterministic fallback recommendations exist.

### 9. Next Steps Checklist

File: `backend/app/services/next_steps.py`

What Gemma does:

- Generates a four-section action checklist after the gauntlet.
- Drops game framing and turns data into counselor, recruiter, self-verification, and parent-conversation prompts.

Guardrails:

- Prompt requires concrete references to the student's data.
- Fallback checklist exists.

### 10. Career Pick Q&A Chips

Files:

- `backend/app/services/career_pick_qna.py`
- `backend/app/routers/career_pick.py`
- UI in `frontend/src/components/CareerLineageSheet.tsx`, `frontend/src/components/AskGemmaChipRow.tsx`, and `frontend/src/components/AskGemmaResponseCard.tsx`

What Gemma does:

- Answers canned, high-value career-pick questions with full career context.
- Logs exactly one Gemma call per chip answer with call-site metadata.

Guardrails:

- Chip catalog constrains the question space.
- Fallback text is returned on transport failure.

### 11. MCP Fallback SOC Resolution

File: `src/mcp_server/futureproof_server.py`

What Gemma does:

- If deterministic crosswalk and CIP broadening fail, Gemma maps a CIP/program to likely SOC codes.
- Result is clearly marked `gemma_soc_resolution` and `ai_estimated`.

Guardrails:

- Validates SOC format.
- SOCs must exist in the local occupation profile table to be used.
- Response caveat explicitly warns that careers were identified by Gemma and may not reflect typical graduate outcomes.

### 12. Gemma AI Exposure Scoring Pipeline

Files:

- `scripts/gemma_ai_exposure_scorer.py`
- `src/raw/gemma_ai_exposure_ingestor.py`
- `src/silver/gemma_ai_exposure_transformer.py`
- `src/gold/ai_exposure_transformer.py`
- `domain/sources/gemma_ai_exposure.yaml`
- `governance/dq-rules/raw-gemma-ai-exposure.json`
- `governance/dq-rules/silver-base-gemma-ai-exposure.json`

What Gemma does:

- Scores every O*NET occupation for theoretical AI exposure on a 0-10 scale.
- Produces rationale plus task breakdowns for automatable vs human-essential work.
- Stamps `scoring_model` and `model_tag` for reproducibility.

Pipeline:

- Batch scorer calls Gemma 4 through OpenRouter or Ollama.
- Bronze ingests committed fixture scores, including error rows.
- Silver normalizes SOCs, filters failed rows, validates joinability.
- Gold blends Gemma 4 with Karpathy/Gemini Flash and Anthropic Economic Index signals, preferring Gemma when present.

This is the strongest "not just prompt engineering" technical-depth asset: Gemma is part of the governed data pipeline, not only runtime UX.

### 13. Frontend Attribution and Demo Surfaces

Key files:

- `frontend/src/components/ui/GemmaStar.tsx`
- `frontend/src/components/ui/GemmaSpinner.tsx`
- `frontend/src/components/ui/GemmaThinking.tsx`
- `frontend/src/components/GemmaTake.tsx`
- `frontend/src/components/landing/OllamaSection.tsx`
- `frontend/src/components/horizon/HorizonFooter.tsx`
- `frontend/src/components/menu/GemmaChat.tsx`
- `frontend/index.html`

What the UI does:

- Marks Gemma-authored or Gemma-in-progress content consistently.
- Shows local Ollama deployment as a product feature.
- Exposes "Built with Gemma 4" and hackathon positioning in public-facing surfaces.

## Tests and Evidence

Relevant test coverage exists for:

- Gemma client behavior and tool calling: `backend/tests/services/test_gemma_client.py`.
- Intent resolution: `backend/tests/services/test_intent.py`.
- Set Your Course streaming/tool path: `backend/tests/services/test_set_your_course.py`, `backend/tests/services/test_set_your_course_chip_tool_loop.py`.
- SOC expansion: `backend/tests/services/test_soc_expansion.py`.
- Guidance, skill recs, boss fights, career pick Q&A: corresponding service/router tests under `backend/tests/services/`.
- Gemma AI exposure Silver transformer: `tests/silver/test_gemma_ai_exposure_transformer.py`.

Spikes and evidence:

- `scripts/spike_gemma_tool_calling.py` tests tool-calling reliability on Ollama and OpenRouter.
- `scripts/spike_gemma_filter.py` documents query-time filtering feasibility.
- `reports/gemma-tool-calling-migration-strategy-2026-04-19.md`
- `reports/feature-soc-expansion-via-gemma-tools-2026-04-20.md`
- `reports/gemma-ai-exposure-rescore-2026-04-16.md`

## Code Review Findings

### High: Submission Story Underuses Multimodal and Multilingual

Gemma 4's official launch emphasizes multimodal input, audio on E2B/E4B, and 140+ languages. The app currently uses text-only Gemma calls. That is not a compliance issue, but it leaves competitive points on the table.

Recommended showcase addition:

- Add a small demo-only "Spanish parent explanation" or "read this screenshot/transcript" moment if feasible.
- If not feasible, frame the current entry around local inference, function calling, structured JSON, and governed data depth rather than claiming broad multimodal usage.

### High: CLI Spike Prompt Duplication Can Create Demo Drift

`backend/app/services/intent.py` previously stated its intent prompt was duplicated in `backend/cli.py`. That CLI has now been moved to `archive/spikes/cli/cli.py`, but the archived file still contains historical prompt code. If someone treats the archive as runnable product code, demos can show different mappings.

Context:

- The CLI existed as an early spike to prove the Gemma + public-data workflow could work.
- The canonical product is now the web/API path.
- The web implementation has evolved beyond the CLI and should be the only path shown to judges.

Recommendation:

- Treat `archive/spikes/cli/cli.py` as deprecated for hackathon purposes.
- Document the frontend/API path as authoritative in the README/writeup.
- Avoid showing CLI behavior in the demo video or judge instructions.
- Done: the CLI was moved under `archive/spikes/cli/` with a deprecation README and top-of-file note.

### High: Default Local Model Name Must Match Repro Docs

Runtime default is `gemma4:e4b`, while some docs/scripts refer to `gemma4:26b-a4b`. The landing page also claims `gemma4:e4b (4.1 GB download)`. Judges following repo setup need one clear path.

Recommendation:

- In the README/writeup, state exactly:
  - demo default: `INFERENCE_BACKEND=ollama`, `OLLAMA_MODEL=gemma4:e4b`;
  - higher-quality option: `OPENROUTER_MODEL=google/gemma-4-26b-a4b-it` or local `gemma4:26b-a4b` if hardware permits.

### Medium: Some Gemma Calls Lack `extra.call_site`

The client supports call-site logging, but not every generation call passes `extra`. The most important tool and streaming paths do, but narrative and recommendation paths are harder to audit by source from `logs/gemma.jsonl`.

Recommendation:

- Add `extra={"call_site": "..."}` to guidance, boss narrative, skill rec, skill pool, next steps, career tiering, and intent audit calls before final demo logs are generated.

### Medium: MCP Fallback SOC Resolution Is Clearly Labeled but Technically Risky

The fallback asks Gemma to produce likely SOCs when no crosswalk coverage exists. It validates format and local existence, but it is still AI-estimated career mapping.

Recommendation:

- In video/writeup, present this as "honest AI-estimated fallback with caveats" rather than primary data truth.
- Make sure UI shows the caveat in any demo path that triggers this fallback.

### Medium: JSON Parsing Is Defensive but Still Prompt-Format Dependent

Most structured Gemma calls parse JSON/text formats and fall back safely. Good for reliability, but judge-facing technical discussion should mention the parser/validation/fallback layer because it is a real engineering strength.

Recommendation:

- In the writeup, say Gemma never writes directly into the UI or data model without validation. It is parsed, clamped, checked against known CIPs/SOCs, and wrapped in deterministic fallbacks.

### Low: `docs/gemma4_model_options.md` Should Be Updated Against Current Runtime Defaults

This doc is useful for the submission narrative but should be checked for exact model tags, hardware claims, and source links before publishing.

## Best Video / Writeup Angles

Lead with:

1. A student types a messy major/career phrase.
2. Gemma streams a plain-English interpretation and returns validated structured JSON.
3. Student pushes back with "Not what I expected."
4. Gemma calls the career-path tool, grounds the answer in public data, and updates or explains the resolution.
5. The app shows deterministic stats and boss outcomes.
6. Gemma interprets the results in plain language and produces next steps.
7. Split-screen: same code running through Ollama locally.

Explicit phrases to use:

- "Gemma handles the ambiguous human language; governed public data handles the numbers."
- "Every model output is validated before it affects the product."
- "The same app can run locally via Ollama, so schools do not have to send student planning data to a hosted LLM."
- "This is an agentic workflow, not a chat wrapper: Gemma calls tools, reads results, and produces structured decisions."

Avoid:

- Overclaiming multimodal if no demo uses images/audio/video.
- Presenting Gemma-estimated SOCs as authoritative outcomes.
- Relying on generic career advice as the main demo moment.

## Pre-Submission Checklist

- Verify public repo has setup instructions for both OpenRouter and Ollama.
- Add a `GEMMA_USAGE.md` or link this report from README.
- Ensure `.env.example` lists `INFERENCE_BACKEND`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, and `GEMMA_MAX_CONCURRENCY`.
- Run backend tests for Gemma services.
- Capture a fresh `logs/gemma.jsonl` demo run and use it as writeup evidence, redacting secrets if any.
- Confirm all live-demo paths show data caveats for AI-estimated rows.
- Keep the Kaggle writeup under 1,500 words and make the video the primary story.
