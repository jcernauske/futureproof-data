# FutureProof Kaggle Judge-Style Score

Date: 2026-05-04

Context: This scores the current repository state as a Gemma 4 Good Hackathon submission. Per request, the missing Kaggle write-up and demo video are not treated as gaps, though their future quality would affect the final judged result.

## Estimated Score

**Overall: 87 / 100**

This reads as a serious finalist-caliber submission, especially for the Future of Education, Digital Equity & Inclusivity, and Ollama tracks.

| Criterion | Score | Judge Read |
|---|---:|---|
| Impact and Vision | 36 / 40 | Strong, concrete education/equity problem. The local Ollama story makes the impact more credible: schools can run it without per-query cost or sending student context out. Slight deductions because there is no user validation, adoption evidence, or live school/counselor pilot yet. |
| Technical Depth and Execution | 27 / 30 | Very strong for a hackathon: governed data pipeline, deterministic scoring, Gemma intent resolution, MCP-style tools, receipts, Ollama/OpenRouter backend switch, tests, screenshots, and model-call logging. Deductions are mostly for complexity, local latency risk, and the fact that multimodal/fine-tuning are not used. |
| Video Pitch and Storytelling | 24 / 30 | The repo story is now strong: student-first, not infra-first. The README does the right thing. Since the missing video/write-up are ignored here, this score reflects story potential from current materials. A sharp 3-minute video could push this to 27-28 / 30. |

## Track Fit

| Track | Competitiveness |
|---|---|
| Future of Education | Best fit. This should be highly competitive if the demo lands clearly. |
| Digital Equity & Inclusivity | Strong, especially if the pitch centers first-generation/public-school access and local deployment. |
| Ollama Special Track | Very credible. The repo has a real local runtime story, not just a badge. |
| Main Track | Competitive, but harder because Main usually rewards broad, immediately legible impact plus exceptional demo clarity. |

## Strengths Judges Will Notice

- Gemma 4 is essential, not decorative.
- The product solves a real decision-support problem.
- Deterministic scoring plus Gemma explanation is a strong safety/trust design.
- Local Ollama deployment gives the project a distinctive good-for-schools angle: cost, privacy, offline/school-owned infrastructure.
- The repo now has a judge-facing README, quickstart, architecture, screenshots, limitations, and licensing notes.

## Main Risks

- The product is dense. A judge could miss the core value if the video tries to show too many features.
- Claims like "runs locally" need a very explicit Ollama proof moment.
- The local path may be slow; frame it as school-owned, private, fixed-cost infrastructure, not as the fastest demo path.
- The story should avoid sounding like "career RPG app" first. Lead with: students are making six-figure decisions using fragmented data.

## Bottom Line

This is not merely a good hackathon project. It has enough technical substance and social-good framing to place, especially in Future of Education or Ollama, if the submission materials make Gemma's role obvious in the first minute.

