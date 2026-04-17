# Feature: Gemma AI Exposure Re-scoring (S1)

## Claude Code Prompt

```
Read the spec at docs/specs/gemma-ai-exposure-rescore.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (Gemma prompt design, batch execution, pipeline integration)
   - Invoke @fp-data-reviewer to review data quality implications — especially the A/B validation vs Karpathy scores
   - Both write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 2
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

2. IMPLEMENTATION
   - Implement the spec as written in §4 (Technical Spec)
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly
   - DURING coding: Update any broken tests listed in "Authorized Test Modifications"
   - CRITICAL: If any test NOT in the "Authorized Test Modifications" list fails, STOP and escalate to human
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)
   - If still broken after 3 attempts: escalate to human via §10 Discussion

3. TESTING
   - Invoke @test-writer to review the full spec
   - @test-writer MUST review §4 Testing Impact Analysis
   - Implement all tests listed in "New Tests Required" by priority (P0 first)
   - Backend tests: pytest in backend/tests/
   - Run ALL tests to catch regressions
   - If still broken after 3 attempts: escalate to human via §10 Discussion

4. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests
   - Reviewer writes findings to §8 (Code Review)
   - If APPROVED: proceed to step 5
   - If CHANGES REQUIRED: route to originating agent via §10 Discussion
   - If BLOCKER: STOP, alert human

5. VERIFICATION
   - Invoke @fp-builder to run full build verification
   - Backend: ruff check, mypy, pytest
   - Log results to §9 (Verification)
   - If all green: mark status COMPLETE

6. COMPLETION
   - Update THIS SPEC's Status to COMPLETE
   - Check off all completed Success Criteria in §1
   - Generate report to reports/gemma-ai-exposure-rescore-YYYY-MM-DD.md
   
   **CRITICAL: Update the PRD**
   - Open `docs/futureproof_hackathon_prd_v8.md`
   - Find the Stretch Specs table in the "Spec Backlog" section
   - Change S1 `gemma-ai-exposure-rescore` status from "⬜ Not started" to "✅ Complete"
   - Save the PRD file
```

---

## Status: DRAFT

| Status | Meaning |
|--------|---------|
| DRAFT | Riffing / initial design |
| ARCH REVIEW | Awaiting @fp-architect approval |
| IMPLEMENTATION | Implementing |
| TESTING | @test-writer adding coverage |
| CODE REVIEW | @faang-staff-engineer reviewing |
| VERIFICATION | @fp-builder running full build |
| COMPLETE | Shipped |
| BLOCKED | Escalated to human |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-09 |
| Author | Jeff + Claude Desktop |
| Spec Version | 2.0 |
| Last Updated | 2026-04-16 |
| Blocked By | Core frontend complete (F1-F7), Karpathy pipeline through Gold |
| Related Specs | `raw-ingest-karpathy-ai-exposure` (baseline), `gold-onet-profiles` (input data), `three-signal-ai-exposure-composite` (S4, depends on this) |
| Priority | Bonus — ship if time allows after core frontend is complete |
| Estimated Effort | 8-12 hours |

---

## §1 Feature Description

### Overview

Replace Karpathy's Gemini Flash AI exposure scores with Gemma 4-generated scores, using our own governed O*NET task-level data as input rather than scraped BLS Markdown pages. This produces higher-quality, more granular AI exposure assessments while demonstrating Gemma doing real analytical work in the pipeline — a strong signal for the Technical Depth judging criterion (30pts).

### Problem Statement

Karpathy scored 342 occupations by feeding BLS job descriptions into Gemini Flash with a rubric. His own words: "saturday morning 2 hour vibe coded project." We can do better:

1. **Task-level granularity:** We have O*NET task-level data (798 occupations with detailed work activity breakdowns) already in Gold. Gemma can evaluate AI exposure at the **task level** and aggregate up — producing a more defensible, more granular score with richer rationale.

2. **Coverage:** O*NET has 798 occupations vs. Karpathy's 342. Gemma re-scoring covers 2.3× more occupations, filling gaps in the pentagon.

3. **Provenance:** Scores come from our governed pipeline with full lineage, not an external script.

4. **Hackathon story:** "We used Gemma to re-score every occupation using task-level O*NET data" is a line that lands in the writeup AND the video.

This is NOT on the critical path. The hackathon ships fine with Karpathy's scores. This is additive — it improves score quality and strengthens the technical story.

### Why This Matters for the Hackathon

- **Technical Depth (30pts):** Gemma doing analytical reasoning over structured data, not just chat. Demonstrates the model as a data enrichment engine — exactly what "Gemma 4 Good" judges want to see.
- **Score quality:** "AI can automate data aggregation (task) but not client relationship management (task)" is more useful than "Financial Analyst scores 8/10."
- **Task breakdown:** Gemma produces `automatable` and `human_essential` task lists — these power the "Which tasks AI is already eating" and "What the human edge looks like" sections in the PRD. Currently generated at query time; this spec pre-computes and governs them.

### Success Criteria

- [ ] Gemma scoring prompt tuned and tested on 10-20 occupations
- [ ] Batch scoring script runs against all 798 O*NET occupations via Ollama
- [ ] Bronze ingest of Gemma output (JSON → `raw.gemma_ai_exposure`)
- [ ] Silver promotion with SOC normalization (`base.gemma_ai_exposure`)
- [ ] Gold promotion into `consumable.ai_exposure` (same schema as Karpathy, + new fields)
- [ ] A/B comparison report: Gemma vs. Karpathy for 342 overlapping occupations
- [ ] Engine tables (`program_career_paths`, `career_branches`) re-promoted with Gemma scores
- [ ] Coverage report: 798 occupations scored (vs. 342 baseline)
- [ ] All DQ rules passing at each zone
- [ ] All tests passing

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Score at task level, not job-description level | O*NET provides detailed work activities per occupation. Evaluating "Can AI do this specific task?" is more defensible than "Can AI do this job overall?" | Job-description scoring (Karpathy's approach) — less granular, less defensible |
| 2 | Use O*NET `top_5_activities` + `top_human_activities` as primary input | These fields from `consumable.onet_work_profiles` capture the most important and most human-requiring tasks. Compact enough for a single prompt. | Full activity list — too long for context window. Summary only — loses task-level detail. |
| 3 | JSON-only response format | Structured output enables automated parsing and validation. No prose parsing required. | Prose response with regex extraction — fragile. |
| 4 | Batch via Ollama locally | Ollama provides consistent, reproducible inference. ~798 calls × 5-10 sec = 1-2 hours. Acceptable for a one-time batch. | Cloud API — cost, rate limits. Real-time scoring — too slow for 798 occupations. |
| 5 | Preserve Karpathy scores as fallback | If Gemma fails for an occupation, fall back to Karpathy. Belt and suspenders. | Require Gemma for all — would reduce coverage if any fail. |
| 6 | A/B comparison as a deliverable | Validates that Gemma scores are reasonable by comparing to Karpathy baseline. Becomes a section in the Kaggle writeup. | Skip comparison — loses validation story. |

### Constraints

- Gemma must run locally via Ollama (hackathon requirement: runs on school hardware)
- Batch time budget: ~2 hours max for full scoring run
- Must produce same schema as Karpathy pipeline for downstream compatibility
- Task breakdown fields are new — frontend may need minor updates to display them

---

## §3 UI/UX Design

> Backend-only spec. No new UI screens.

**Downstream frontend impact:** None required. The API shape for `stat_res` and `boss_ai_score` is unchanged. The receipts endpoint gains additional fields (`task_breakdown_automatable`, `task_breakdown_human`, `scoring_model`) but these are additive.

**Optional frontend enhancement (not in scope):** Display the task breakdown in the Fight AI boss detail view — "Tasks AI is automating: X, Y, Z. Tasks that need humans: A, B, C." This would be a separate spec if prioritized.

---

## §4 Technical Specification

### Architecture Overview

```
Input: consumable.onet_work_profiles (798 occupations with task data)
         ↓
Gemma 4 via Ollama (batch scoring, ~1-2 hours)
         ↓
Output: JSON file with scores + rationales + task breakdowns
         ↓
Bronze: raw.gemma_ai_exposure
         ↓
Silver: base.gemma_ai_exposure (SOC normalization, validation)
         ↓
Gold: consumable.ai_exposure (replaces Karpathy scores, same schema + new fields)
         ↓
Re-promote: consumable.program_career_paths, consumable.career_branches
```

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `scripts/gemma_ai_exposure_scorer.py` | Create | Batch scoring script — reads O*NET data, calls Ollama, writes JSON |
| `data/raw/gemma_cache/ai_exposure_scores.json` | Create | Output from batch scoring (committed for reproducibility) |
| `src/raw/gemma_ai_exposure_ingestor.py` | Create | Bronze ingestor for Gemma output |
| `src/silver/gemma_ai_exposure_promoter.py` | Create | Silver promoter — SOC normalization, join validation |
| `src/gold/ai_exposure_promoter.py` | Modify | Update to prefer Gemma scores over Karpathy, add new fields |
| `src/gold/futureproof_engine_promoter.py` | Modify | Re-promote with Gemma-based `stat_res` and `boss_ai_score` |
| `dq/rules/gemma_ai_exposure_rules.py` | Create | DQ rules for Bronze + Silver |
| `data_contracts/gemma_ai_exposure.yaml` | Create | Data contract for Gemma scores |
| `reports/gemma_vs_karpathy_comparison.md` | Create | A/B comparison report |

### Gemma Scoring Prompt

```python
GEMMA_AI_EXPOSURE_PROMPT = """
Given the following occupation data:

Occupation: {occupation_title} (SOC: {soc_code})
Top Work Activities: {top_5_activities}
Human-Edge Activities: {top_human_activities}
Work Context: {context_summary}
Education: {education_level_name}
Median Wage: ${median_annual_wage:,}

Score this occupation's AI exposure on a 0-10 scale.

Consider:
- Which specific tasks can current AI perform or substantially assist with?
- Which tasks require physical presence, manual skill, or real-time human judgment?
- What proportion of the work is digital/screen-based vs. physical/interpersonal?
- How much would AI-augmented productivity reduce headcount demand?

Respond with ONLY a JSON object, no other text:
{{"exposure": <0-10 integer>, "rationale": "<2-3 sentences citing specific tasks>", "task_breakdown": {{"automatable": ["task1", "task2"], "human_essential": ["task3", "task4"]}}}}
"""
```

### Batch Scoring Script

```python
# scripts/gemma_ai_exposure_scorer.py

import json
import time
from pathlib import Path
import ollama
from backend.app.services.onet import load_onet_profiles
from backend.app.services.occupation import load_occupation_profiles

OUTPUT_PATH = Path("data/raw/gemma_cache/ai_exposure_scores.json")

def score_occupation(profile: dict, onet: dict) -> dict:
    """Score a single occupation via Gemma."""
    prompt = GEMMA_AI_EXPOSURE_PROMPT.format(
        occupation_title=onet["occupation_title"],
        soc_code=onet["bls_soc_code"],
        top_5_activities=json.dumps(onet["top_5_activities"]),
        top_human_activities=json.dumps(onet["top_human_activities"]),
        context_summary=onet["context_summary"],
        education_level_name=profile.get("education_level_name", "Unknown"),
        median_annual_wage=profile.get("median_annual_wage", 0),
    )
    
    response = ollama.generate(model="gemma4", prompt=prompt)
    
    # Parse JSON response
    try:
        result = json.loads(response["response"].strip())
        result["soc_code"] = onet["bls_soc_code"]
        result["occupation_title"] = onet["occupation_title"]
        result["scoring_model"] = "gemma-4"
        result["scored_at"] = datetime.utcnow().isoformat()
        return result
    except json.JSONDecodeError:
        return {
            "soc_code": onet["bls_soc_code"],
            "occupation_title": onet["occupation_title"],
            "error": "JSON parse failed",
            "raw_response": response["response"][:500],
        }

def run_batch():
    """Score all occupations."""
    onet_profiles = load_onet_profiles()  # 798 occupations
    occupation_profiles = load_occupation_profiles()  # For education/wage enrichment
    
    results = []
    for onet in onet_profiles:
        soc = onet["bls_soc_code"]
        profile = occupation_profiles.get(soc, {})
        
        print(f"Scoring {soc}: {onet['occupation_title']}...")
        result = score_occupation(profile, onet)
        results.append(result)
        
        time.sleep(0.5)  # Rate limiting
    
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, indent=2))
    print(f"Wrote {len(results)} scores to {OUTPUT_PATH}")

if __name__ == "__main__":
    run_batch()
```

### Data Model Changes

#### Raw Table: `raw.gemma_ai_exposure`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| soc_code | string | yes | SOC code from O*NET |
| occupation_title | string | yes | Occupation title |
| exposure | integer | yes | 0-10 AI exposure score |
| rationale | string | yes | 2-3 sentence explanation citing tasks |
| task_breakdown_automatable | string | yes | JSON array of automatable tasks |
| task_breakdown_human | string | yes | JSON array of human-essential tasks |
| scoring_model | string | yes | "gemma-4" |
| scored_at | timestamp | yes | When the score was generated |
| error | string | no | Error message if scoring failed |

**Grain:** One row per occupation.
**Expected rows:** 798 (all O*NET occupations).

#### Silver Table: `base.gemma_ai_exposure`

Same fields as Raw, plus:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| soc_code_normalized | string | yes | Normalized to XX-XXXX format |
| join_valid | boolean | yes | True if SOC joins to `consumable.occupation_profiles` |

**DQ rules:**
- `exposure` must be integer 0-10
- `rationale` must be non-empty
- `task_breakdown_automatable` must be valid JSON array
- `task_breakdown_human` must be valid JSON array
- `soc_code_normalized` must match a known SOC code

#### Updated Gold Table: `consumable.ai_exposure`

Existing fields preserved. New/modified fields:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| exposure_score | integer | yes | Now from Gemma (was Karpathy) |
| stat_res | integer | yes | `10 - exposure_score` (inverted) |
| boss_ai_score | integer | yes | Same as `exposure_score` |
| rationale | string | yes | Gemma's task-level rationale |
| task_breakdown_automatable | string | no | **NEW:** JSON array of automatable tasks |
| task_breakdown_human | string | no | **NEW:** JSON array of human-essential tasks |
| scoring_model | string | yes | **NEW:** "gemma-4" (was "gemini-flash") |
| karpathy_score | integer | no | **NEW:** Preserved for comparison/fallback |

**Fallback logic:** If Gemma score is missing for an occupation, use `karpathy_score` for `exposure_score`.

### A/B Comparison Report

Generate `reports/gemma_vs_karpathy_comparison.md`:

```markdown
# Gemma vs. Karpathy AI Exposure Score Comparison

## Summary
- Overlapping occupations: 342
- Correlation coefficient: X.XX
- Mean absolute difference: X.X points
- Gemma higher: N occupations
- Karpathy higher: N occupations
- Exact match: N occupations

## Notable Divergences (>3 point difference)

| Occupation | Gemma | Karpathy | Δ | Notes |
|-----------|-------|----------|---|-------|
| ... | ... | ... | ... | ... |

## Coverage Improvement
- Karpathy: 342 occupations
- Gemma: 798 occupations
- New coverage: 456 occupations (+133%)

## Conclusion
[Analysis of whether Gemma scores are reasonable, any systematic biases, recommendation for production use]
```

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `tests/test_stats.py` | `test_stat_res_computation` | Medium | `stat_res` values will change for most occupations |
| `tests/test_boss_fight.py` | `test_boss_ai_score` | Medium | `boss_ai_score` values will change |
| `tests/test_gold_ai_exposure.py` | `test_ai_exposure_schema` | Low | New fields added |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `test_stat_res_computation` | Update expected values for test fixtures | Gemma scores differ from Karpathy |
| `test_boss_ai_score` | Update expected values for test fixtures | Same reason |
| `test_ai_exposure_schema` | Add assertions for new fields | New fields added |

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `tests/test_gemma_scorer.py` | `test_prompt_produces_valid_json` | Gemma response parses to expected schema |
| P0 | `tests/test_gemma_scorer.py` | `test_exposure_score_range` | Score is integer 0-10 |
| P0 | `tests/test_gemma_scorer.py` | `test_task_breakdown_structure` | Both arrays are non-empty, contain strings |
| P0 | `tests/test_gemma_ai_exposure_ingest.py` | `test_raw_to_silver_promotion` | SOC normalization works |
| P0 | `tests/test_gemma_ai_exposure_ingest.py` | `test_silver_to_gold_promotion` | Gold table updated correctly |
| P1 | `tests/test_gemma_scorer.py` | `test_error_handling` | Malformed Gemma response captured, not crashed |
| P1 | `tests/test_gemma_ai_exposure_ingest.py` | `test_fallback_to_karpathy` | Missing Gemma score uses Karpathy |
| P1 | `tests/test_gemma_ai_exposure_ingest.py` | `test_coverage_improvement` | 798 occupations in Gold (vs. 342 baseline) |
| P2 | `tests/test_ab_comparison.py` | `test_comparison_report_generated` | Report file exists with expected sections |

#### Test Data Requirements

- Fixture file: `tests/fixtures/gemma_ai_exposure_sample.json` — 10 representative occupations with pre-computed Gemma scores
- Fixture file: `tests/fixtures/onet_sample.json` — Matching O*NET profiles for the 10 fixtures
- Mock: Ollama response mock for unit tests (avoid live Gemma calls in CI)

---

## §5 Architecture Review

### @fp-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-16

#### System Context
Backend-only addition. Touches Bronze (new `raw.gemma_ai_exposure` Iceberg table), Silver (new `base.gemma_ai_exposure`), Gold (existing `consumable.ai_exposure` rewritten to prefer Gemma with Karpathy fallback), and downstream re-promotion of `consumable.program_career_paths` and `consumable.career_branches` via `src/gold/futureproof_engine.py`. No frontend contract change — `stat_res` / `boss_ai_score` keys preserved in the MCP `get_ai_exposure` response. New fields (`task_breakdown_automatable`, `task_breakdown_human`, `scoring_model`, `karpathy_score`) are additive and must be threaded through `AI_EXPOSURE_RESPONSE_FIELDS` if we want them surfaced.

#### Data Flow Analysis
```
consumable.onet_work_profiles (Gold, read-only)
  + consumable.occupation_profiles (Gold, read-only; edu + wage enrichment)
     -> scripts/gemma_ai_exposure_scorer.py  (Ollama batch, ~798 calls)
     -> data/raw/gemma_cache/ai_exposure_scores.json  (local cache)
     -> bronze.gemma_ai_exposure  (Iceberg)
     -> base.gemma_ai_exposure  (Silver, SOC normalize + join validate)
     -> consumable.ai_exposure  (Gold, prefer Gemma, fallback Karpathy)
     -> consumable.program_career_paths  (re-promote via futureproof_engine)
     -> consumable.career_branches  (re-promote via futureproof_engine)
     -> MCP get_ai_exposure  (unchanged signature, optional new fields)
```
Flow is coherent. The Gold step blends two Silver inputs (`base.karpathy_ai_exposure` + `base.gemma_ai_exposure`) into one consumable — this blending logic is under-specified and the biggest architectural gap.

#### Contract Review
- MCP `get_ai_exposure` schema: input unchanged (SOC only). Response shape preserved. New Gold fields must be added to `AI_EXPOSURE_RESPONSE_FIELDS` in `src/mcp_server/futureproof_server.py` (currently omits them) — otherwise the new `task_breakdown_*` / `scoring_model` / `karpathy_score` columns exist in Iceberg but never reach Gemma/the backend.
- `futureproof_engine.py` reads Gold `ai_exposure` rows and only looks up `stat_res` and `boss_ai_score` by `soc_code` — compatible, no change required.
- DuckDB side: no change needed. Gold Iceberg tables are surfaced to `data/futureproof.duckdb` through the same pipeline path already in use.

#### Findings

##### Sound
- **Zone discipline is correct.** Bronze is raw Gemma JSON, Silver does SOC normalization + BLS join check, Gold is contracted. Mirrors the Karpathy pipeline one-for-one.
- **Scoring at the task level** (vs. job-description level) is the right unit — `top_5_activities` + `top_human_activities` already exist in `consumable.onet_work_profiles` as JSON-encoded arrays, so prompt assembly is a `json.loads` away.
- **JSON-only response format** with stringified task arrays in Iceberg matches the existing pattern (`top_5_activities`, `top_human_activities`, `burnout_drivers` are all JSON-encoded strings in Gold — see `_JSON_STRUCT_FIELDS` in `futureproof_server.py`).
- **Fallback to Karpathy** when Gemma is missing preserves coverage (342 floor) and prevents regressions on the pentagon.
- **Ollama-local** honors the hackathon constraint; 798 × ~5s is within the ~2h budget.

##### Concerns

- **File naming breaks repo convention.** Spec names `src/silver/gemma_ai_exposure_promoter.py` and `src/gold/ai_exposure_promoter.py`, but this repo uses `*_transformer.py` at Silver and Gold (see `src/silver/karpathy_ai_exposure_transformer.py`, `src/gold/ai_exposure_transformer.py`). There is no `ai_exposure_promoter.py`. **Impact:** implementation will either duplicate modules or silently drift from the codebase. **Recommendation:** rename to `src/silver/gemma_ai_exposure_transformer.py` and modify the existing `src/gold/ai_exposure_transformer.py` (don't create a new file). Use the shared `brightsmith.infra.promote.promote` helper the existing transformers use.

- **O*NET field names in the prompt don't exist.** Spec's `score_occupation` reads `onet["occupation_title"]` and `onet["context_summary"]`. The actual `consumable.onet_work_profiles` exposes `primary_title` (not `occupation_title`) and has no `context_summary` column (see `TASK_BREAKDOWN_RESPONSE_FIELDS` in the MCP server and the schema in `src/gold/onet_work_profiles.py`). **Impact:** batch script crashes or silently inserts `None` into the prompt. **Recommendation:** use `primary_title`; drop `context_summary` or synthesize one from `time_pressure` + `work_hours` + `consequence_of_error` which do exist. Also note `top_5_activities` / `top_human_activities` arrive as JSON strings — call `json.loads` before `json.dumps` for deterministic prompt formatting.

- **Gold schema drops required fields and contradicts the existing contract.** Existing Gold schema (`src/gold/ai_exposure_transformer.py` get_gold_schema) has 9 columns including `record_id` (required), `category` (required), and `promoted_at` (required). Spec's §4 Data Model Changes shows only 9 new fields and omits `record_id`/`promoted_at`, and silently drops `category`. **Impact:** migration breaks the `governance/data-contracts/consumable-ai-exposure.yaml` contract; existing MCP response field `category` disappears; Iceberg schema evolution rejects required-field removal. **Recommendation:** the new Gold schema must be the existing 9 columns PLUS the 4 new ones (13 total), with `record_id` and `promoted_at` preserved and `category` carried forward from Karpathy when available. Explicitly state the stat_res formula as `min(11 - exposure_score, 10)` to match `compute_stat_res` — spec's description ("10 - exposure_score") silently changes a production formula.

- **Gold blending logic is under-specified.** Gold now has two Silver inputs: `base.karpathy_ai_exposure` and `base.gemma_ai_exposure`. Spec says "prefer Gemma, fallback Karpathy" but never defines (a) the join key (presumably `soc_code_normalized`), (b) what happens when Karpathy has a SOC Gemma doesn't, (c) what `scoring_model` is set to on the Karpathy-only rows ("karpathy"? "gemini-flash"?), (d) whether `karpathy_score` is populated on Gemma-primary rows or only on fallback rows, (e) what the grain is (still `soc_code`, but Karpathy Silver can have multiple rows per SOC due to broad expansion — see `_dedup_by_soc_code` in `karpathy_ai_exposure_transformer.py`). **Impact:** ambiguous merge = non-deterministic Gold. **Recommendation:** add a dedicated sub-section "Gold blending algorithm" with: keys, preference order, explicit field-by-field source matrix, handling of Gemma `error` rows, dedup rule. State that grain remains `soc_code` with `record_id = compute_grain_id(row, ['soc_code'], prefix='aie')`.

- **MCP response fields omit the new columns.** `AI_EXPOSURE_RESPONSE_FIELDS` in `futureproof_server.py` lists 7 fields. Spec adds `task_breakdown_automatable`, `task_breakdown_human`, `scoring_model`, `karpathy_score` but doesn't call out the MCP change. **Impact:** new Gold columns are unreachable from the backend/Gemma layer — the "Task breakdown" story in §1 (PRD Fight AI panel) won't work. **Recommendation:** File Changes table must include `src/mcp_server/futureproof_server.py` (add fields to `AI_EXPOSURE_RESPONSE_FIELDS`; add the two `task_breakdown_*` JSON-string fields to `_JSON_STRUCT_FIELDS` so they're decoded like `top_5_activities`). Tool description string should also be updated — currently says "Karpathy AI exposure score".

- **Batch script reproducibility is weak.** (a) No per-row checkpointing — a 1.5-hour run that dies at row 600 restarts from zero. (b) `ollama.generate(model="gemma4", ...)` pins no model tag; Ollama model names in this project are `gemma3:4b` / similar (see `.env` + `docs/specs/cloud-gemma-deployment.md`). (c) No `seed` / `temperature` / `num_predict` / `format="json"` — Ollama's native JSON mode is the right tool here and avoids the `try: json.loads` failure path. (d) No retry on `JSONDecodeError` before marking the row as errored. (e) `datetime.utcnow()` is not imported and is deprecated — use `datetime.now(tz=timezone.utc)`. **Impact:** ~5-10% of rows will fail silently on a cold run, cache is not resumable, run is not reproducible across machines. **Recommendation:** (1) read the model name from `.env` (`INFERENCE_BACKEND` aware); (2) write each row to `ai_exposure_scores.jsonl` as it completes (JSONL, not one big JSON); (3) use Ollama `format="json"` + `options={"temperature": 0.1, "seed": 42}`; (4) skip rows already in the cache on re-run (idempotency); (5) retry JSON failures up to 3 times before writing the `error` row.

- **Karpathy fallback path not implemented end-to-end.** Spec §4 says "If Gemma score is missing, use karpathy_score for exposure_score" but this logic lives only in a prose sentence. No place in §4 explicitly states: (a) whether Karpathy's 342 SOCs get promoted into Gold even when Gemma succeeds for them (needed for `karpathy_score` column = preserve for comparison), (b) what happens to the ~456 SOCs where Gemma succeeds but Karpathy has no row (`karpathy_score` = null, fine, but `stat_res` / `boss_ai_score` use Gemma — make it explicit), (c) what happens to the (likely rare) SOC where Gemma's `error` is set and Karpathy is also missing (currently Gold filters `bls_match=true`; the new blender must define "row is unusable, skip"). **Impact:** correctness regression — the pentagon could silently lose RES coverage on the 342 overlapping SOCs. **Recommendation:** add a truth table: (Gemma ok | Gemma error | Gemma missing) x (Karpathy ok | Karpathy missing) -> 6 cells, each with exposure_score source, rationale source, scoring_model value, and inclusion decision.

- **`data/raw/gemma_cache/` is not committable.** `data/` is in `.gitignore` (verified at repo root). Spec claims the cache is "committed for reproducibility". **Impact:** reproducibility story collapses — a fresh clone can't re-build Gold without rerunning the 1.5-hour Ollama batch. **Recommendation:** either (a) move the committed artifact to `governance/fixtures/gemma_ai_exposure_scores.jsonl` (outside gitignore) and keep `data/raw/gemma_cache/` as the working local cache (matches Karpathy's dual-location pattern), or (b) add an explicit gitignore exception (`!data/raw/gemma_cache/`). Pick (a) — governance is where auditable artifacts live in this repo.

- **Downstream re-promotion order not defined.** Spec modifies `futureproof_engine_promoter.py` (again wrong filename — it is `src/gold/futureproof_engine.py`) but doesn't state the re-promotion order. `futureproof_engine.transform` reads `consumable.ai_exposure`, so Gold ai_exposure must be re-promoted FIRST, then the engine FIRST computes `program_career_paths` THEN `career_branches` (they share the same `ai_by_soc` lookup; see lines 517+ of `futureproof_engine.py`). Spec should say "run `src/gold/ai_exposure_transformer.py` then `src/gold/futureproof_engine.py`" in §4 to make it executable.

- **DQ rules file path.** Spec says `dq/rules/gemma_ai_exposure_rules.py`. This repo's DQ rules live under `governance/dq/` (check existing layout) — verify before creating. Same for `data_contracts/gemma_ai_exposure.yaml`: repo convention is `governance/data-contracts/{zone}-{table-with-hyphens}.yaml` (e.g. `bronze-gemma-ai-exposure.yaml`, `silver-base-gemma-ai-exposure.yaml`, and an updated `consumable-ai-exposure.yaml`). File Changes table should list all three contracts, not one.

##### Blockers
None — none of the above are architecturally impossible. But the file-naming, Gold schema, and blending-algorithm concerns must be resolved before code is written or the implementation will diverge from the repo and break the existing contract.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions
1. Rename all `*_promoter.py` references to `*_transformer.py`; modify (don't recreate) `src/gold/ai_exposure_transformer.py` and `src/gold/futureproof_engine.py`.
2. Fix the prompt's O*NET field names (`primary_title`, not `occupation_title`; drop or synthesize `context_summary`); `json.loads` the task arrays before re-serializing into the prompt.
3. Specify the new Gold schema as existing 9 columns + 4 new (13 total), preserving `record_id`, `promoted_at`, `category`. Keep `stat_res = min(11 - exposure_score, 10)` exactly.
4. Add a "Gold blending algorithm" sub-section with the full truth table (Gemma x Karpathy) and explicit field-source matrix.
5. Add `src/mcp_server/futureproof_server.py` to File Changes: extend `AI_EXPOSURE_RESPONSE_FIELDS`, `_JSON_STRUCT_FIELDS`, and the `get_ai_exposure` tool description.
6. Rewrite the batch script section for resumability: JSONL per-row writes, cache-skip on re-run, Ollama `format="json"` + fixed seed/temperature, model name from `.env`, retry on JSON-decode failures, `datetime.now(tz=timezone.utc)`.
7. Move the committed cache out of `data/` (gitignored) to `governance/fixtures/` or add a gitignore exception.
8. List all three data-contract files in File Changes (`bronze-gemma-ai-exposure.yaml`, `silver-base-gemma-ai-exposure.yaml`, updated `consumable-ai-exposure.yaml`) under the correct `governance/data-contracts/` directory; verify `governance/dq/` is the right home for DQ rules before creating `dq/rules/...`.
9. State the re-promotion order explicitly in §4: ai_exposure Gold -> futureproof_engine Gold.

### @fp-data-reviewer Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-16

#### Data Sources Affected
- **O*NET** (`consumable.onet_work_profiles`, 798 occupations) — read-only input to the scorer (`top_5_activities`, `top_human_activities`, `context_summary`)
- **BLS OOH** (`consumable.occupation_profiles`, 832 rows) — read-only input (education, median wage)
- **Karpathy AI Exposure** (`consumable.ai_exposure`, 342 rows today) — replaced; Karpathy retained as fallback
- Downstream: `consumable.program_career_paths` (626,406 rows), `consumable.career_branches` (15,944 rows) — re-promoted
- Pipeline zones touched: Bronze (new), Silver (new), Gold (modified `ai_exposure`, re-promoted engine)

#### Crosswalk Impact
- No change to CIP→SOC crosswalk logic itself.
- Indirect impact: coverage grows from 342 → 798 SOC codes with an exposure score. Today, any CIP→SOC mapping to a SOC not in Karpathy's 342 returns `stat_res = NULL` / `boss_ai_score = NULL` (see `futureproof_engine.py:425,434` — plain dict lookup, no fallback). Post-Gemma, many of those nulls fill in, which is a net quality improvement.
- Risk: schools+majors currently showing a pentagon with `stat_res = NULL` will start showing a value. This is correct behavior but a visible change for existing fixtures.

#### Formula Verification — CRITICAL DIVERGENCE FROM SPEC
Spec §4 claims `stat_res = 10 - exposure_score` and `boss_ai_score = exposure_score`. The shipped code in `src/gold/ai_exposure_transformer.py:51-68` actually uses:

- `stat_res = MIN(11 - exposure_score, 10)` — yields 1-10 range, floors at 1 for exposure=10, caps at 10 for exposure=0 or 1
- `boss_ai_score = MAX(exposure_score, 1)` — floors at 1 so exposure=0 does not produce a 0 boss score

The spec formulas would produce `stat_res=0` for an occupation with `exposure_score=10` and `boss_ai_score=0` for `exposure_score=0`. Both violate the "no stat below 1" rule. The spec must adopt the existing floor/cap formulas verbatim, or the implementer will regress a correctness invariant.

#### A/B Comparison Methodology — Insufficient
The §4 report template is a skeleton. Required additions before this is a credible validation:
- **Correlation threshold:** Pearson r must be reported with a gate (e.g., r ≥ 0.6 acceptable, r < 0.4 rejects Gemma scores). Without a gate, "reasonable" is unfalsifiable.
- **Mean absolute difference threshold:** Gate MAD < 2.0 points (on a 0-10 scale); anything wider means Gemma and Karpathy disagree on half the scale.
- **Bias metrics:** Report mean signed difference. Non-zero mean indicates systematic skew (Gemma always-higher or always-lower). Gate: |mean signed Δ| < 1.0.
- **Category-level breakdown:** Correlation broken down by O*NET job family (healthcare, tech, trades, etc.) to catch domain-specific bias. Example watch: Gemma likely over-scores any occupation that mentions "data" or "analysis" because those tokens prime the exposure concept.
- **Stat_res distribution comparison:** Histogram overlay Gemma vs. Karpathy at the `stat_res` level (what the student actually sees). Divergence on the 5-stat output matters more than on the raw 0-10 exposure.
- **Outlier review:** Occupations where |Gemma - Karpathy| ≥ 4 must be human-reviewed (expect ~20-40 rows); the report must list them with rationales side-by-side.

#### Score Distribution Risks
- **Mode collapse (all 7s):** Gemma on structured data with a generic rubric tends to center-cluster. Mitigation: post-batch distribution check with DQ rule — reject if >40% of scores land on a single integer, or if std dev < 1.5.
- **Bimodal collapse:** Model anchors on "clearly automatable" vs. "clearly not" and skips mid-range. Mitigation: DQ rule that each bucket 0-3, 4-6, 7-10 contains ≥10% of occupations.
- **Integer-only rubric:** Spec enforces 0-10 integer. This gives only 11 buckets for 798 occupations — average 72 occupations per bucket. Consider allowing 0-10 with one decimal (0.0-10.0) to recover resolution. If kept integer, document that ordering ties are expected.
- **Prompt sensitivity:** The example rubric mentions "how much would AI-augmented productivity reduce headcount demand" — this is a different question than "how automatable are the tasks" and may produce systematically higher scores. Recommend prompt A/B (two wordings on a 50-occupation sample) before committing to the 798-run.
- **Temperature:** Spec does not specify Ollama `temperature`. Must be set to 0 or ≤0.1 for reproducibility; otherwise re-runs produce different scores and the batch is not auditable.

#### Fallback Correctness — Ambiguous
Spec §4 says "If Gemma score is missing for an occupation, use `karpathy_score` for `exposure_score`." Issues:
- The 798 O*NET SOCs are not a superset of Karpathy's 342 — there are Karpathy SOCs that do not appear in O*NET (Karpathy draws from BLS OOH, which has historically included SOCs outside O*NET's work-profile coverage). Spec must clarify: do we drop the Karpathy-only rows, keep them as Karpathy-scored in Gold, or union both sources? Recommend: union. Final coverage = 798 ∪ 342 = ~850, not 798.
- For the 456 new SOCs (O*NET-only, no Karpathy): if Gemma fails to score them, there is **no fallback**. Spec should state explicitly that these rows go to NULL (consistent with today's behavior for non-Karpathy SOCs) rather than defaulting to a median value. NULL is correct; do not invent a default.
- `scoring_model` must be per-row (`"gemma-4"` vs `"karpathy-gemini-flash"`) so downstream consumers and the UI can label provenance. Spec lists it but does not say it varies per-row.

#### DQ Rules (§4 Silver) — Insufficient
Listed rules are minimum schema validation. Missing (all P0):
- **Coverage rule:** `row_count >= 780` (allow ≤18 scoring failures / 2.3%). Hard-fail if lower.
- **Null rate rule:** Fail if `error` column is non-null for >3% of rows.
- **Distribution rule:** `std_dev(exposure_score) >= 1.5` AND `COUNT(DISTINCT exposure_score) >= 7` (catch mode collapse).
- **SOC join rule:** 100% of `soc_code_normalized` must join to `consumable.occupation_profiles` or `consumable.onet_work_profiles`. Spec says "must match a known SOC code" but does not define the reference set or the threshold.
- **Rationale quality:** `LENGTH(rationale) BETWEEN 50 AND 800` — catches one-word or truncated responses.
- **Task breakdown non-empty:** `json_array_length(task_breakdown_automatable) >= 1 AND json_array_length(task_breakdown_human) >= 1`. An empty array is a silent Gemma failure.
- **No duplicate SOCs:** `COUNT(*) = COUNT(DISTINCT soc_code_normalized)`.
- **Reproducibility:** Record `ollama_model_tag` (e.g., `gemma4:latest@sha256:...`) per row; DQ rule that all rows in a batch share the same tag.

#### Gold Schema Change — Backward Compatibility
Current `consumable.ai_exposure` schema (Iceberg, 9 columns, `ai_exposure_transformer.py:36-48`) has `record_id, soc_code, occupation_title, exposure_score, stat_res, boss_ai_score, rationale, category, promoted_at`. Spec adds `task_breakdown_automatable`, `task_breakdown_human`, `scoring_model`, `karpathy_score`. Issues:
- `category` (existing, required) is not preserved in the new pipeline — it comes from Karpathy's occupations.csv. Spec must specify: carry forward from Karpathy where available, else derive from O*NET job family, else "uncategorized". Dropping it silently breaks the Iceberg schema.
- Adding non-nullable fields to an existing Iceberg table requires backfill; spec should mark new fields `required=False` to avoid migration pain.
- `karpathy_score` as nullable integer is correct; add `karpathy_rationale` too so the UI can surface both perspectives if we want the "Gemma says X, Karpathy said Y" disclosure.

#### Disclaimer Check
- [ ] AI-estimated values labeled — **Gap:** Every score is now AI-estimated. The UI currently treats Karpathy scores as "observed" because they come from a governed table. Gemma scores are categorically AI-estimated and the distinction must be surfaced in the receipts endpoint and the Fight AI boss detail.
- [ ] Confidence scores propagated — **Gap:** No confidence field exists on `consumable.ai_exposure` today. Since Gemma produces a single score per occupation, confidence is implicit (prompt-driven). Recommend adding `confidence_tier` (1-4) driven by: presence of O*NET task data quality, whether rationale length is within band, and whether Gemma agreed with Karpathy within 2 points.
- [ ] Required disclaimer strings — **Gap:** Spec §3 says "no UI changes required." This is wrong. Replacing Karpathy (presented today as an external scored dataset) with Gemma (our own model output) changes the provenance story the student sees. Disclaimer required: "AI exposure scored by Gemma 4 using O*NET task data. Not observed; model-estimated."
- [ ] Missing data states — **Gap:** Spec does not say what happens to `stat_res` / `boss_ai_score` for occupations where both Gemma AND Karpathy fail. Answer should be: `NULL` → `bosses_available_count` decrements → UI shows "insufficient data" for Fight AI on that career. Confirm this path in `futureproof_engine.py` still works.

#### Data Concerns (Significant — Must Fix Before Implementation)
- **Formula correction:** Update §4 Data Model Changes to match shipped formulas exactly: `stat_res = MIN(11 - exposure_score, 10)`, `boss_ai_score = MAX(exposure_score, 1)`. Risk if shipped as spec'd: every occupation with `exposure_score=10` gets `stat_res=0` (floor violation).
- **Reproducibility:** Pin Ollama temperature=0 and record model tag per row. Risk: re-running the batch produces different scores, so the "governed pipeline" claim fails.
- **A/B validation gates:** Add numeric acceptance thresholds to the comparison report (correlation, MAD, mean signed Δ, category breakdown). Risk: report reads as "looks fine" without a falsifiable test.
- **Distribution DQ rules:** Add mode-collapse and bucket-coverage checks in Silver. Risk: Gemma ships an all-7s distribution and every occupation gets the same `stat_res`.
- **Category field:** Preserve `category` in Gold output. Risk: Iceberg schema breaks on required-field violation during promote.
- **Provenance disclaimer:** Update §3 to specify the AI-estimated disclaimer on Fight AI boss detail and career card tooltip. Risk: students trust a Gemma estimate as observed data.
- **Fallback coverage edge case:** Clarify union semantics for the 342 Karpathy SOCs that may not appear in O*NET's 798. Risk: silent coverage regression from 342 → smaller number if the intersection is taken.
- **Temperature / model-tag lineage:** Neither is in spec. Risk: not auditable, not reproducible, cannot be re-run deterministically for the hackathon demo.

#### Data Integrity Blockers
None. All issues above are significant-but-correctable; no fundamental crosswalk or pipeline failure.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

---

## §6 Implementation Log

**Status:** PENDING

### Files Modified
| File | Change Summary |
|------|---------------|

### Deviations from Spec
[Any divergence from §4 and why]

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §7 Test Coverage

**Status:** PENDING

### Tests Added

| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| pytest | | | | |

---

## §8 Reviews

**Status:** PENDING

### Code Review (@faang-staff-engineer)
**Status:** PENDING
#### Findings
[Filled in by reviewer]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUIRED
- [ ] BLOCKER

---

## §9 Verification

**Status:** PENDING

### Backend (@fp-builder)
| Check | Result |
|-------|--------|
| Lint (ruff) | |
| Type check (mypy) | |
| Tests (pytest) | |

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|

---

## §10 Discussion

```
[YYYY-MM-DD HH:MM] @source-agent → @target-agent
Message content.
```

---

## §11 Final Notes

**Human Review:** PENDING

### When to Trigger

Only after ALL of the following are complete:
1. Karpathy pipeline is through Gold (pentagon is 5/5 with Karpathy scores)
2. Frontend is functional (all 10 screens working — F1-F7 complete)
3. Gemma agent integration is working end-to-end
4. Video storyboard is drafted

If those are done and there's time before May 18, this is the highest-value bonus work. If not, Karpathy scores ship and this becomes Week 1 post-hackathon.

### Hackathon Story

**Before:** "We used Karpathy's open-source AI exposure scores as our starting point — 342 occupations scored by Gemini Flash reading BLS job descriptions."

**After:** "Then we used Gemma 4 to re-score every occupation using task-level O*NET data from our governed pipeline. Gemma evaluates which specific tasks are automatable vs. human-essential — not just the job description, but the actual work. Coverage doubled from 342 to 798 occupations. Here's how Gemma's scores compare to Karpathy's."

That's a before/after that judges notice.

### Estimated Effort

| Step | Estimate |
|------|----------|
| Prompt engineering + validation (10-20 occupations) | 2-3 hours |
| Batch scoring run (798 occupations) | 1-2 hours (mostly waiting) |
| Pipeline ingest (Bronze → Silver → Gold) | 2-3 hours |
| A/B comparison report | 1 hour |
| Engine re-promote + backfill | 1 hour |
| **Total** | **8-12 hours** |

### Dependency Chain

```
raw-ingest-karpathy-ai-exposure (COMPLETE — baseline)
  ↓
gold-onet-profiles (COMPLETE — input data)
  ↓
gemma-ai-exposure-rescore (THIS SPEC — S1)
  ↓
three-signal-ai-exposure-composite (S4 — depends on this)
```

S4 can run without S1 (degrades to Karpathy + Anthropic), but S1 makes the three-signal composite much stronger.

---

*— End of Spec —*
