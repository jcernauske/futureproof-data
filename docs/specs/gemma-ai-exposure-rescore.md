# Spec: gemma-ai-exposure-rescore (BONUS / NON-CRITICAL-PATH)

**Status:** BACKLOG
**Zone:** Gold (replaces consumable.ai_exposure data, same schema)
**Primary Agent:** @primary-agent
**Created:** 2026-04-09
**Priority:** Bonus — ship if time allows after core pipeline + frontend are complete

---

## Problem Statement

Replace Karpathy's Gemini Flash AI exposure scores with Gemma 4-generated scores, using our own governed O*NET task-level data as input rather than scraped BLS Markdown pages. This produces higher-quality, more granular AI exposure assessments while demonstrating Gemma doing real analytical work in the pipeline — a strong signal for the Technical Depth judging criterion (30pts).

Karpathy scored 342 occupations by feeding BLS job descriptions into Gemini Flash with a rubric. We can do better: we have O*NET task-level data (798 occupations with detailed work activity breakdowns) already in Gold. Gemma can evaluate AI exposure at the **task level** and aggregate up — producing a more defensible, more granular score with richer rationale.

This is NOT on the critical path. The hackathon ships fine with Karpathy's scores. This is additive — it improves score quality and strengthens the technical story.

## Why This Matters for the Hackathon

- **Technical Depth:** "We didn't just use someone else's LLM scores. We used Gemma to re-score every occupation using task-level O*NET data from our governed pipeline." That's a line that lands in the writeup AND the video.
- **Gemma showcase:** This is Gemma doing analytical reasoning over structured data, not just chat. It demonstrates the model as a data enrichment engine — exactly what "Gemma 4 Good" judges want to see.
- **Score quality:** Task-level scoring is more defensible than job-description-level scoring. "AI can automate data aggregation (task) but not client relationship management (task)" is more useful than "Financial Analyst scores 8/10."
- **Coverage:** O*NET has 798 occupations vs. Karpathy's 342. Gemma re-scoring covers 2.3x more occupations, filling gaps in the pentagon.

## Approach

### Input

For each occupation in `consumable.onet_work_profiles`:
- `bls_soc_code` — occupation identifier
- `occupation_title` — occupation name
- `top_5_activities` — JSON: top 5 work activities with importance scores
- `top_human_activities` — JSON: activities with highest human-edge signal
- `activity_summary` — text summary of all work activities
- `context_summary` — text summary of work context (hours, stress, physical demands)

Optionally enrich with `consumable.occupation_profiles`:
- `median_annual_wage` — salary context
- `education_level_name` — education requirement
- `growth_category` — BLS growth outlook

### Gemma Scoring Rubric

Prompt Gemma with each occupation's task data and a structured rubric (adapted from Karpathy's, enhanced with task-level granularity):

```
Given the following occupation data:

Occupation: {occupation_title} (SOC: {soc_code})
Top Work Activities: {top_5_activities}
Human-Edge Activities: {top_human_activities}
Work Context: {context_summary}
Education: {education_level_name}
Median Wage: {median_annual_wage}

Score this occupation's AI exposure on a 0-10 scale.

Consider:
- Which specific tasks can current AI perform or substantially assist with?
- Which tasks require physical presence, manual skill, or real-time human judgment?
- What proportion of the work is digital/screen-based vs. physical/interpersonal?
- How much would AI-augmented productivity reduce headcount demand?

Respond with ONLY a JSON object:
{"exposure": <0-10>, "rationale": "<2-3 sentences citing specific tasks>", "task_breakdown": {"automatable": ["task1", "task2"], "human_essential": ["task3", "task4"]}}
```

### Execution

- **Batch job:** Run Gemma against all 798 O*NET occupations via Ollama
- **Estimated time:** ~798 calls × ~5-10 sec each = ~1-2 hours on a local GPU
- **Output:** JSON file with scores, rationales, and task breakdowns per SOC code
- **Ingest through Brightsmith:** Output feeds back into the pipeline as a new Bronze source, processed through Silver → Gold using the same schema as `consumable.ai_exposure`
- **A/B validation:** Compare Gemma scores vs. Karpathy scores for the 342 overlapping occupations. Report correlation, mean difference, and notable divergences. This becomes a section in the Kaggle writeup.

### Gold Table Update

`consumable.ai_exposure` gets re-promoted with Gemma scores replacing Karpathy scores. Schema is identical — `exposure_score`, `stat_res`, `boss_ai_score`, `rationale`. Add:

| Field | Type | Notes |
|-------|------|-------|
| task_breakdown_automatable | string | JSON array of automatable tasks (new — Gemma provides this, Karpathy didn't) |
| task_breakdown_human | string | JSON array of human-essential tasks (new) |
| scoring_model | string | "gemma-4" (vs. "gemini-flash" for Karpathy) — provenance field |

The `task_breakdown` fields are display data for the frontend — they power the "Which tasks AI is already eating" and "What the human edge looks like" sections from the PRD. Currently those are Gemma-generated at query time. With this spec, they're pre-computed and governed.

### Backfill

Same as the Karpathy spec — re-promote `program_career_paths` and `career_branches` with the new scores. Coverage jumps from ~342 to ~798 occupations.

## Deliverables

- [ ] Gemma scoring prompt (tuned, tested on 10-20 occupations, reviewed)
- [ ] Batch scoring script (runs via Ollama locally)
- [ ] Bronze ingest of Gemma output
- [ ] Silver + Gold promotion (same schema as Karpathy pipeline)
- [ ] A/B comparison report: Gemma vs. Karpathy (for Kaggle writeup)
- [ ] Re-promoted engine tables with expanded coverage
- [ ] Kaggle writeup section: "From Karpathy to Gemma — re-scoring with task-level data"

## Estimated Effort

| Step | Estimate |
|------|----------|
| Prompt engineering + validation | 2-3 hours |
| Batch scoring run | 1-2 hours (mostly waiting) |
| Pipeline ingest (Bronze → Gold) | 2-3 hours |
| A/B comparison report | 1 hour |
| Engine re-promote + backfill | 1 hour |
| **Total** | **~8-12 hours** |

## When to Trigger

Only after ALL of the following are complete:
1. Karpathy pipeline is through Gold (pentagon is 5/5 with Karpathy scores)
2. Frontend is functional (all 8 screens working)
3. Gemma agent integration is working end-to-end
4. Video storyboard is drafted

If those are done and there's time before May 18, this is the highest-value bonus work. If not, Karpathy scores ship and this becomes Week 1 post-hackathon.

## Hackathon Story

**Before:** "We used Karpathy's open-source AI exposure scores as our starting point — 342 occupations scored by Gemini Flash reading BLS job descriptions."

**After:** "Then we used Gemma 4 to re-score every occupation using task-level O*NET data from our governed pipeline. Gemma evaluates which specific tasks are automatable vs. human-essential — not just the job description, but the actual work. Coverage doubled from 342 to 798 occupations. Here's how Gemma's scores compare to Karpathy's."

That's a before/after that judges notice.

---

*— End of Spec —*
