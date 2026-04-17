# Feature: Gemma AI Exposure Re-scoring (S1)

> **⚠️ DEPRECATED — 2026-04-16.** This v3 spec did not pass architecture or data review. Both `@fp-architect` and `@fp-data-reviewer` returned `CHANGES REQUESTED`. See §5 for full findings. Do not implement from this file. A v4 revision must address the consolidated residuals below before workflow execution resumes.
>
> **Residuals to fix in v4 (13 items, all mechanical, ~2 hours of spec work):**
>
> *Will-break-on-first-run:*
> 1. Wrong Ollama model tag — `gemma2:27b` should be `gemma4:26b-a4b` (per `docs/specs/cloud-gemma-deployment.md`); read from `.env` and record resolved tag per row.
> 2. `data/gemma_cache/` is gitignored (`.gitignore` line 2 = `data/`); move committed artifact to `governance/fixtures/gemma_ai_exposure_scores.jsonl`.
> 3. `blend_scores` returns rows missing `record_id` and `promoted_at` (required Iceberg fields); call `add_record_ids(blended, promoted_at=now_utc())`.
> 4. Prompt double-encodes `top_5_activities` / `top_human_activities` — Gold stores them as JSON strings; `json.loads` first.
> 5. MCP `_JSON_STRUCT_FIELDS` not extended for new `task_breakdown_*` columns — task-breakdown surface ships as escaped strings instead of arrays (silently breaks the "Gemma shows its work" feature end-to-end).
> 6. No Ollama `format="json"` and no retry loop — ~5–10% silent JSON parse failures expected.
>
> *Governance / contract gaps:*
>
> 7. DQ rule path wrong — repo convention is `governance/dq-rules/*.json` (not `dq/rules/*.py`); need 3 files (raw, silver, updated gold).
> 8. File Changes misses updates to existing `governance/data-contracts/consumable-ai-exposure.yaml` and `governance/data-contracts/mcp-ai-exposure.yaml`.
> 9. Re-promotion order not stated in §4 prose — must say `ai_exposure_transformer.py` runs before `futureproof_engine.py`.
>
> *Validation / auditability gaps:*
>
> 10. A/B gates missing std-dev floor (≥1.5), bucket coverage (≥10% in each of 0-3, 4-6, 7-10), outlier list (`|Δ|≥4` table), and `len(deltas) >= 10` guard on Gate 4 category bias.
> 11. Silver DQ missing 6 rules: row count (≥780), error rate (≤3%), rationale length (50-800), duplicate-SOC, single-model-tag-per-batch, task-breakdown non-empty.
> 12. `category="Unknown"` blankets ~456 Gemma-only rows — derive from SOC 2018 major group (first 2 digits) instead; this also restores Gate 4's meaning.
> 13. `model_tag` captured per row by scorer but not persisted to Gold schema — add as 14th column, required, populated for both Gemma and Karpathy rows.
>
> Additional v4 considerations: A/B gates should be fail-closed (block Gold promote on `overall_pass=False` unless explicitly overridden); AI-estimated disclaimer should attach to career-card RES tooltip (not only Fight AI drill-down) since RES is rendered earlier in the funnel; explicit statement that `karpathy_rows` is pre-deduped by SOC via Silver's `_dedup_by_soc_code`.

---

## Claude Code Prompt

```
This is the v3 revision of the S1 spec, addressing all 12 issues from architecture + data reviewer feedback.

Read the spec at docs/specs/gemma-ai-exposure-rescore.md (v3) in its entirety. This version fixes:
- Filename conventions (*_transformer.py not *_promoter.py)
- Correct O*NET column names (primary_title, not occupation_title)
- Exact stat formulas from shipped code (MIN/MAX, not 10-x)
- Schema preservation (category, record_id, promoted_at kept)
- MCP field extension
- Resumable/deterministic batch config
- Blending truth table with union semantics
- A/B validation gates with numerical thresholds
- Distribution collapse DQ rules
- AI-estimated disclaimer for Fight AI

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (Gemma prompt design, batch execution, pipeline integration)
   - Invoke @fp-data-reviewer to review data quality implications — especially the A/B validation gates and blending truth table
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

## Status: DEPRECATED

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
| DEPRECATED | Superseded — do not implement |

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-09 |
| Author | Jeff + Claude Desktop |
| Spec Version | 3.0 (DEPRECATED) |
| Last Updated | 2026-04-16 |
| Deprecated | 2026-04-16 — failed both @fp-architect and @fp-data-reviewer; superseded by forthcoming v4 |
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

### Success Criteria

- [ ] Gemma scoring prompt tuned and tested on 10-20 occupations
- [ ] Batch scoring script runs against all 798 O*NET occupations via Ollama (deterministic config)
- [ ] Bronze ingest of Gemma output (`raw.gemma_ai_exposure`)
- [ ] Silver promotion with SOC normalization (`base.gemma_ai_exposure`)
- [ ] Gold promotion into `consumable.ai_exposure` (preserving existing schema + adding new fields)
- [ ] A/B comparison report passes all validation gates (see §4)
- [ ] Blending truth table implemented per spec (Gemma preferred, Karpathy fallback, full union coverage)
- [ ] MCP `AI_EXPOSURE_RESPONSE_FIELDS` extended for new columns
- [ ] Engine tables (`program_career_paths`, `career_branches`) re-promoted with blended scores
- [ ] Coverage report: 798 occupations scored (vs. 342 baseline)
- [ ] Distribution check: no mode collapse (no single score > 40% of population)
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
| 4 | Batch via Ollama locally with deterministic config | Ollama provides consistent, reproducible inference. Pin model tag + temperature=0 for reproducibility. | Cloud API — cost, rate limits. Real-time scoring — too slow for 798 occupations. |
| 5 | Blend Gemma + Karpathy (not replace) | Full union coverage: use Gemma where available (798), fall back to Karpathy for any gaps. Preserves backward compatibility. | Replace entirely — would reduce coverage if Gemma fails on any occupation. |
| 6 | A/B comparison with numerical gates | Validates that Gemma scores are reasonable via correlation, MAD, category bias checks. Automated go/no-go decision. | Skip comparison — loses validation story. Manual review only — not reproducible. |
| 7 | Extend existing schema, don't drop fields | `category`, `record_id`, `promoted_at` are required by existing consumers. Add new fields (`task_breakdown_*`, `scoring_model`, `karpathy_score`) without breaking compatibility. | Drop `category` — would break MCP responses and downstream consumers. |

### Constraints

- Gemma must run locally via Ollama (hackathon requirement: runs on school hardware)
- Batch time budget: ~2 hours max for full scoring run
- Must preserve existing `consumable.ai_exposure` schema for backward compatibility
- Must use existing formula conventions: `stat_res = MIN(11 - exposure_score, 10)`, `boss_ai_score = MAX(exposure_score, 1)`
- Task breakdown fields are new — frontend may need minor updates to display them

---

## §3 UI/UX Design

### Backend-Only with MCP Extension

No new UI screens. The API shape for `stat_res` and `boss_ai_score` is unchanged. The MCP `get_ai_exposure` tool gains additional fields in its response:

**Updated `AI_EXPOSURE_RESPONSE_FIELDS` (in `futureproof_server.py`):**
```python
AI_EXPOSURE_RESPONSE_FIELDS = [
    # Existing (preserved)
    "soc_code",
    "occupation_title",
    "exposure_score",
    "stat_res",
    "boss_ai_score",
    "rationale",
    "category",
    # New (added by this spec)
    "task_breakdown_automatable",
    "task_breakdown_human",
    "scoring_model",
    "karpathy_score",  # preserved for comparison/receipts
]
```

### Receipts Update

Update `backend/app/services/receipts.py` to surface the scoring model:

```python
# Before (line ~100):
f"RES {_stat(stats.res)}/10 ← "
f"Karpathy AI exposure + O*NET task analysis (SOC {career.soc_code})"

# After:
f"RES {_stat(stats.res)}/10 ← "
f"Gemma task-level AI exposure (SOC {career.soc_code})"
# OR when karpathy fallback:
f"RES {_stat(stats.res)}/10 ← "
f"Karpathy AI exposure (SOC {career.soc_code})"
```

The receipts should indicate `scoring_model` so users know the provenance.

### Fight AI Detail — AI-Estimated Disclaimer

When `scoring_model = "gemma-4"`, the Fight AI boss detail view should include a brief disclaimer: "AI exposure estimated by Gemma 4 using O*NET task data." This surfaces that we're using our own LLM scoring rather than an external authoritative source.

**Implementation:** Add `scoring_model` to the `CareerOutcome` Pydantic model and thread it through `boss_fights.py` narrative generation.

---

## §4 Technical Specification

### Architecture Overview

```
Input: consumable.onet_work_profiles (798 occupations with task data)
         ↓
Gemma 4 via Ollama (batch scoring, deterministic config, resumable)
         ↓
Output: JSON file with scores + rationales + task breakdowns
         ↓
Bronze: raw.gemma_ai_exposure (new table)
         ↓
Silver: base.gemma_ai_exposure (SOC normalization, validation)
         ↓
Gold: consumable.ai_exposure (extends existing schema, blends Gemma + Karpathy)
         ↓
Re-promote: consumable.program_career_paths, consumable.career_branches
```

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `scripts/gemma_ai_exposure_scorer.py` | Create | Batch scoring script — resumable, deterministic config |
| `data/gemma_cache/ai_exposure_scores.json` | Create | Output from batch scoring (outside .gitignore) |
| `src/raw/gemma_ai_exposure_ingestor.py` | Create | Bronze ingestor for Gemma output |
| `src/silver/gemma_ai_exposure_transformer.py` | Create | Silver transformer — SOC normalization, join validation |
| `src/gold/ai_exposure_transformer.py` | Modify | Blend Gemma + Karpathy, add new fields, preserve existing |
| `src/gold/futureproof_engine.py` | Modify | Use blended `consumable.ai_exposure` |
| `src/mcp_server/futureproof_server.py` | Modify | Extend `AI_EXPOSURE_RESPONSE_FIELDS` |
| `backend/app/services/receipts.py` | Modify | Surface `scoring_model` in RES receipt |
| `backend/app/models/career.py` | Modify | Add `scoring_model` to `CareerOutcome` |
| `dq/rules/gemma_ai_exposure_rules.py` | Create | DQ rules for Bronze + Silver + distribution checks |
| `governance/data-contracts/raw-gemma-ai-exposure.yaml` | Create | Data contract for Gemma Bronze |
| `governance/data-contracts/base-gemma-ai-exposure.yaml` | Create | Data contract for Gemma Silver |
| `reports/gemma_vs_karpathy_comparison.md` | Create | A/B comparison report with pass/fail gates |

### Gemma Scoring Prompt

**IMPORTANT:** Use the actual column names from `consumable.onet_work_profiles`:
- `primary_title` (not `occupation_title`)
- `top_5_activities` (JSON array of `{activity, importance}`)
- `top_human_activities` (JSON array of `{activity, importance}`)
- No `context_summary` column exists — use `burnout_drivers` + `time_pressure` + `work_hours` instead

```python
GEMMA_AI_EXPOSURE_PROMPT = """
Given the following occupation data:

Occupation: {primary_title} (SOC: {bls_soc_code})
Top Work Activities: {top_5_activities}
Human-Edge Activities: {top_human_activities}
Burnout Factors: Time Pressure={time_pressure}/5, Work Hours={work_hours}/3
Education Typical: {education_level_name}
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

### Batch Scoring Script (Resumable, Deterministic)

```python
# scripts/gemma_ai_exposure_scorer.py

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import ollama

# Deterministic config — pinned model, temperature=0
OLLAMA_MODEL = "gemma2:27b"  # Pin exact model tag
OLLAMA_OPTIONS = {"temperature": 0.0, "seed": 42}

OUTPUT_PATH = Path("data/gemma_cache/ai_exposure_scores.json")
CHECKPOINT_PATH = Path("data/gemma_cache/ai_exposure_checkpoint.json")

def load_checkpoint() -> set[str]:
    """Load already-scored SOC codes for resumability."""
    if CHECKPOINT_PATH.exists():
        data = json.loads(CHECKPOINT_PATH.read_text())
        return set(data.get("completed_socs", []))
    return set()

def save_checkpoint(completed_socs: set[str], results: list[dict]) -> None:
    """Save checkpoint for resume."""
    CHECKPOINT_PATH.write_text(json.dumps({
        "completed_socs": list(completed_socs),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }))
    OUTPUT_PATH.write_text(json.dumps(results, indent=2))

def score_occupation(onet: dict, occupation: dict) -> dict:
    """Score a single occupation via Gemma with deterministic config."""
    prompt = GEMMA_AI_EXPOSURE_PROMPT.format(
        primary_title=onet.get("primary_title", "Unknown"),
        bls_soc_code=onet["bls_soc_code"],
        top_5_activities=json.dumps(onet.get("top_5_activities", [])),
        top_human_activities=json.dumps(onet.get("top_human_activities", [])),
        time_pressure=onet.get("time_pressure", "N/A"),
        work_hours=onet.get("work_hours", "N/A"),
        education_level_name=occupation.get("education_level_name", "Unknown"),
        median_annual_wage=occupation.get("median_annual_wage", 0),
    )
    
    response = ollama.generate(
        model=OLLAMA_MODEL,
        prompt=prompt,
        options=OLLAMA_OPTIONS,
    )
    
    raw_text = response.get("response", "").strip()
    
    try:
        # Strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        result = json.loads(raw_text)
        return {
            "soc_code": onet["bls_soc_code"],
            "primary_title": onet.get("primary_title"),
            "exposure_score": int(result["exposure"]),
            "rationale": result["rationale"],
            "task_breakdown_automatable": json.dumps(result["task_breakdown"]["automatable"]),
            "task_breakdown_human": json.dumps(result["task_breakdown"]["human_essential"]),
            "scoring_model": "gemma-4",
            "model_tag": OLLAMA_MODEL,
            "scored_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
        }
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        return {
            "soc_code": onet["bls_soc_code"],
            "primary_title": onet.get("primary_title"),
            "error": f"Parse failed: {e}",
            "raw_response": raw_text[:500],
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }

def run_batch():
    """Score all occupations with checkpointing."""
    # Load data from Gold tables
    onet_profiles = _load_onet_profiles()  # 798 rows
    occupation_profiles = _load_occupation_profiles()  # For education/wage
    
    completed = load_checkpoint()
    results = []
    
    # Resume from checkpoint
    if OUTPUT_PATH.exists():
        results = json.loads(OUTPUT_PATH.read_text())
    
    for onet in onet_profiles:
        soc = onet["bls_soc_code"]
        if soc in completed:
            continue
        
        occupation = occupation_profiles.get(soc, {})
        print(f"Scoring {soc}: {onet.get('primary_title', 'Unknown')}...")
        
        result = score_occupation(onet, occupation)
        results.append(result)
        completed.add(soc)
        
        # Checkpoint every 10 occupations
        if len(completed) % 10 == 0:
            save_checkpoint(completed, results)
        
        time.sleep(0.5)  # Rate limiting
    
    save_checkpoint(completed, results)
    print(f"Complete: {len(results)} occupations scored")
```

### Gold Table Schema — Preserving Existing Fields

**CRITICAL:** The existing `consumable.ai_exposure` schema has these required fields that MUST be preserved:

```python
# From ai_exposure_transformer.py lines 28-36:
def get_gold_schema() -> Schema:
    return Schema(
        NestedField(1, "record_id", StringType(), required=True),
        NestedField(2, "soc_code", StringType(), required=True),
        NestedField(3, "occupation_title", StringType(), required=True),
        NestedField(4, "exposure_score", IntegerType(), required=True),
        NestedField(5, "stat_res", IntegerType(), required=True),
        NestedField(6, "boss_ai_score", IntegerType(), required=True),
        NestedField(7, "rationale", StringType(), required=True),
        NestedField(8, "category", StringType(), required=True),  # KEEP
        NestedField(9, "promoted_at", TimestampType(), required=True),  # KEEP
        # NEW fields (append, don't replace):
        NestedField(10, "task_breakdown_automatable", StringType(), required=False),
        NestedField(11, "task_breakdown_human", StringType(), required=False),
        NestedField(12, "scoring_model", StringType(), required=True),  # "gemma-4" or "gemini-flash"
        NestedField(13, "karpathy_score", IntegerType(), required=False),  # preserved for comparison
    )
```

### Stat Formula — Match Existing Code

Use the EXACT formulas from `ai_exposure_transformer.py`:

```python
def compute_stat_res(exposure_score: int) -> int:
    """AI Resilience stat (1-10). Higher exposure = lower resilience.
    Formula: MIN(11 - exposure_score, 10)
    """
    return min(11 - exposure_score, 10)

def compute_boss_ai_score(exposure_score: int) -> int:
    """Fight AI boss strength (1-10). Higher exposure = harder fight.
    Formula: MAX(exposure_score, 1)
    """
    return max(exposure_score, 1)
```

### Blending Truth Table — Gemma Preferred, Karpathy Fallback

The Gold transformer must implement this blending logic:

| Gemma Score | Karpathy Score | Result | `scoring_model` | `karpathy_score` |
|-------------|----------------|--------|-----------------|------------------|
| Present | Present | Use Gemma | "gemma-4" | Karpathy value |
| Present | Missing | Use Gemma | "gemma-4" | NULL |
| Missing | Present | Use Karpathy | "gemini-flash" | Karpathy value |
| Missing | Missing | Exclude row | — | — |

**Coverage expectation:**
- Gemma: 798 occupations (O*NET coverage)
- Karpathy: 342 occupations (with `bls_match=true`)
- Overlap: ~300 occupations
- Union: ~840 occupations (798 Gemma + ~42 Karpathy-only)

```python
def blend_scores(gemma_rows: dict[str, dict], karpathy_rows: dict[str, dict]) -> list[dict]:
    """Blend Gemma + Karpathy with Gemma preferred."""
    all_socs = set(gemma_rows.keys()) | set(karpathy_rows.keys())
    blended = []
    
    for soc in all_socs:
        gemma = gemma_rows.get(soc)
        karpathy = karpathy_rows.get(soc)
        
        if gemma and gemma.get("exposure_score") is not None:
            # Gemma preferred
            row = {
                "soc_code": soc,
                "occupation_title": gemma["primary_title"],
                "exposure_score": gemma["exposure_score"],
                "stat_res": compute_stat_res(gemma["exposure_score"]),
                "boss_ai_score": compute_boss_ai_score(gemma["exposure_score"]),
                "rationale": gemma["rationale"],
                "category": karpathy["category"] if karpathy else "Unknown",
                "task_breakdown_automatable": gemma.get("task_breakdown_automatable"),
                "task_breakdown_human": gemma.get("task_breakdown_human"),
                "scoring_model": "gemma-4",
                "karpathy_score": karpathy["exposure_score"] if karpathy else None,
            }
        elif karpathy:
            # Karpathy fallback
            row = {
                "soc_code": soc,
                "occupation_title": karpathy["occupation_title"],
                "exposure_score": karpathy["exposure_score"],
                "stat_res": compute_stat_res(karpathy["exposure_score"]),
                "boss_ai_score": compute_boss_ai_score(karpathy["exposure_score"]),
                "rationale": karpathy["rationale"],
                "category": karpathy["category"],
                "task_breakdown_automatable": None,
                "task_breakdown_human": None,
                "scoring_model": "gemini-flash",
                "karpathy_score": karpathy["exposure_score"],
            }
        else:
            continue  # No data — exclude
        
        blended.append(row)
    
    return blended
```

### A/B Validation Gates (Numerical)

The comparison report MUST include these automated gates:

```python
# reports/gemma_vs_karpathy_comparison.py

def validate_ab_comparison(gemma_scores: dict, karpathy_scores: dict) -> dict:
    """Run A/B validation with numerical gates. Returns pass/fail status."""
    
    # Overlap set (both Gemma and Karpathy have scores)
    overlap = set(gemma_scores.keys()) & set(karpathy_scores.keys())
    
    # Extract paired scores
    gemma_vals = [gemma_scores[soc] for soc in overlap]
    karpathy_vals = [karpathy_scores[soc] for soc in overlap]
    
    # Gate 1: Pearson correlation >= 0.6
    correlation = pearsonr(gemma_vals, karpathy_vals)[0]
    gate1_pass = correlation >= 0.6
    
    # Gate 2: Mean absolute difference <= 2.0 points
    mad = sum(abs(g - k) for g, k in zip(gemma_vals, karpathy_vals)) / len(overlap)
    gate2_pass = mad <= 2.0
    
    # Gate 3: Mean signed delta between -1.0 and +1.0 (no systematic bias)
    mean_delta = sum(g - k for g, k in zip(gemma_vals, karpathy_vals)) / len(overlap)
    gate3_pass = -1.0 <= mean_delta <= 1.0
    
    # Gate 4: No category has mean delta > 2.0 (category-level bias check)
    category_deltas = defaultdict(list)
    for soc in overlap:
        cat = karpathy_scores[soc].get("category", "Unknown")
        delta = gemma_scores[soc] - karpathy_scores[soc]["exposure_score"]
        category_deltas[cat].append(delta)
    
    category_means = {cat: sum(d)/len(d) for cat, d in category_deltas.items()}
    gate4_pass = all(abs(m) <= 2.0 for m in category_means.values())
    
    # Gate 5: Distribution check — no mode collapse (no score > 40% of population)
    from collections import Counter
    score_counts = Counter(gemma_vals)
    max_pct = max(score_counts.values()) / len(gemma_vals) * 100
    gate5_pass = max_pct <= 40.0
    
    all_pass = all([gate1_pass, gate2_pass, gate3_pass, gate4_pass, gate5_pass])
    
    return {
        "overall_pass": all_pass,
        "gates": {
            "correlation": {"value": correlation, "threshold": 0.6, "pass": gate1_pass},
            "mean_absolute_diff": {"value": mad, "threshold": 2.0, "pass": gate2_pass},
            "mean_signed_delta": {"value": mean_delta, "threshold_range": [-1.0, 1.0], "pass": gate3_pass},
            "category_bias": {"max_category_delta": max(abs(m) for m in category_means.values()), "threshold": 2.0, "pass": gate4_pass},
            "distribution_collapse": {"max_score_pct": max_pct, "threshold": 40.0, "pass": gate5_pass},
        },
        "overlap_count": len(overlap),
        "gemma_coverage": len(gemma_scores),
        "karpathy_coverage": len(karpathy_scores),
    }
```

### Silver DQ Rules — Distribution Checks

```python
# dq/rules/gemma_ai_exposure_rules.py

def check_distribution_collapse(rows: list[dict]) -> dict:
    """DQ rule: No single score should exceed 40% of population."""
    from collections import Counter
    
    scores = [r["exposure_score"] for r in rows if r.get("exposure_score") is not None]
    if not scores:
        return {"pass": False, "message": "No scores to validate"}
    
    counts = Counter(scores)
    max_score = counts.most_common(1)[0]
    max_pct = max_score[1] / len(scores) * 100
    
    if max_pct > 40.0:
        return {
            "pass": False,
            "message": f"Mode collapse detected: score {max_score[0]} has {max_pct:.1f}% of population (threshold: 40%)",
            "mode_score": max_score[0],
            "mode_pct": max_pct,
        }
    
    return {
        "pass": True,
        "message": f"Distribution OK: max score concentration {max_pct:.1f}%",
        "mode_score": max_score[0],
        "mode_pct": max_pct,
    }

def check_score_range(rows: list[dict]) -> dict:
    """DQ rule: All scores must be integers 0-10."""
    invalid = [
        r["soc_code"] for r in rows
        if r.get("exposure_score") is None
        or not isinstance(r["exposure_score"], int)
        or r["exposure_score"] < 0
        or r["exposure_score"] > 10
    ]
    
    if invalid:
        return {
            "pass": False,
            "message": f"Invalid scores for {len(invalid)} SOCs: {invalid[:5]}...",
            "invalid_count": len(invalid),
        }
    
    return {"pass": True, "message": "All scores in valid range 0-10"}

def check_task_breakdown_structure(rows: list[dict]) -> dict:
    """DQ rule: Task breakdowns must be valid JSON arrays with strings."""
    invalid = []
    
    for r in rows:
        for field in ["task_breakdown_automatable", "task_breakdown_human"]:
            val = r.get(field)
            if val is None:
                continue  # Optional field
            try:
                parsed = json.loads(val) if isinstance(val, str) else val
                if not isinstance(parsed, list):
                    invalid.append((r["soc_code"], field, "not a list"))
                elif not all(isinstance(t, str) for t in parsed):
                    invalid.append((r["soc_code"], field, "contains non-strings"))
            except json.JSONDecodeError:
                invalid.append((r["soc_code"], field, "invalid JSON"))
    
    if invalid:
        return {
            "pass": False,
            "message": f"Invalid task breakdowns: {invalid[:5]}...",
            "invalid_count": len(invalid),
        }
    
    return {"pass": True, "message": "All task breakdowns valid"}
```

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `tests/test_stats.py` | `test_stat_res_computation` | Medium | New scoring_model field, blended scores |
| `tests/test_boss_fight.py` | `test_boss_ai_score` | Medium | Blended scores may differ |
| `tests/test_gold_ai_exposure.py` | `test_ai_exposure_schema` | High | New fields added |
| `tests/test_mcp_server.py` | `test_get_ai_exposure` | High | Response shape changes |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `test_ai_exposure_schema` | Add assertions for new fields | New fields added |
| `test_get_ai_exposure` | Update expected response fields | MCP response extended |
| `test_stat_res_computation` | Update fixtures if scores change | Blended scores may differ |
| `test_boss_ai_score` | Update fixtures if scores change | Same reason |

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `tests/test_gemma_scorer.py` | `test_prompt_produces_valid_json` | Gemma response parses to expected schema |
| P0 | `tests/test_gemma_scorer.py` | `test_exposure_score_range` | Score is integer 0-10 |
| P0 | `tests/test_gemma_scorer.py` | `test_task_breakdown_structure` | Both arrays are non-empty, contain strings |
| P0 | `tests/test_gemma_scorer.py` | `test_deterministic_config` | Same input → same output (temperature=0) |
| P0 | `tests/test_ai_exposure_blending.py` | `test_gemma_preferred_over_karpathy` | When both present, Gemma used |
| P0 | `tests/test_ai_exposure_blending.py` | `test_karpathy_fallback` | When Gemma missing, Karpathy used |
| P0 | `tests/test_ai_exposure_blending.py` | `test_union_coverage` | Output has Gemma ∪ Karpathy SOCs |
| P0 | `tests/test_ai_exposure_blending.py` | `test_category_preserved` | `category` field always present |
| P1 | `tests/test_gemma_scorer.py` | `test_resumability` | Checkpoint saves/restores correctly |
| P1 | `tests/test_ab_validation.py` | `test_correlation_gate` | Gate passes/fails at threshold |
| P1 | `tests/test_ab_validation.py` | `test_mad_gate` | Gate passes/fails at threshold |
| P1 | `tests/test_ab_validation.py` | `test_distribution_collapse_gate` | Gate catches mode collapse |
| P1 | `tests/test_gemma_ai_exposure_dq.py` | `test_distribution_collapse_rule` | DQ rule catches >40% mode |
| P2 | `tests/test_receipts.py` | `test_res_receipt_shows_scoring_model` | Receipt reflects Gemma vs Karpathy |

#### Test Data Requirements

- Fixture file: `tests/fixtures/gemma_ai_exposure_sample.json` — 10 representative occupations with pre-computed Gemma scores
- Fixture file: `tests/fixtures/onet_sample.json` — Matching O*NET profiles for the 10 fixtures
- Mock: Ollama response mock for unit tests (avoid live Gemma calls in CI)
- Fixture file: `tests/fixtures/karpathy_sample.json` — Matching Karpathy scores for blending tests

---

## §5 Architecture Review

### @fp-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-16 (v3 re-review)

#### System Context
Re-review of v3 against the 9 v2 conditions. Five conditions fully resolved, four partially or not resolved. The architecture intent is sound; the remaining gaps are mechanical — wrong model tag, wrong gitignore claim, wrong DQ path, missing MCP JSON-struct extension, missing record_id/promoted_at in the blender, and missing re-promotion order statement. None are conceptual blockers, but they will all break the build or silently drop data on first implementation.

#### Condition-by-Condition Verification

| # | Condition | v3 Status | Evidence |
|---|-----------|-----------|----------|
| 1 | Rename `*_promoter.py` -> `*_transformer.py`; modify existing Gold files | **FIXED** | File Changes table correctly says "Modify" on `src/gold/ai_exposure_transformer.py` and `src/gold/futureproof_engine.py`; Silver file is `src/silver/gemma_ai_exposure_transformer.py`. |
| 2 | O*NET field names (`primary_title`, real columns) | **MOSTLY FIXED** | Prompt now uses `primary_title`, `time_pressure`, `work_hours`, `burnout_drivers` — all exist in `consumable.onet_work_profiles` schema (see `src/gold/onet_work_profiles.py` lines 111, 123-125). **Residual:** `score_occupation` passes `json.dumps(onet.get("top_5_activities", []))` but Gold stores `top_5_activities` as a JSON **string** (`json.dumps(top5)` at line 215 of `onet_work_profiles.py`). The spec must `json.loads` first, else the prompt receives escape-nested JSON (`"[{\\"activity\\": ...}]"`). Same for `top_human_activities`. |
| 3 | Preserve 9 existing Gold fields + append 4 new | **FIXED** | §4 Gold schema shows all 9 existing (`record_id`, `soc_code`, `occupation_title`, `exposure_score`, `stat_res`, `boss_ai_score`, `rationale`, `category`, `promoted_at`) plus 4 new. Matches shipped `get_gold_schema()`. |
| 4 | Stat formulas match shipped code | **FIXED** | §4 shows `min(11 - exposure_score, 10)` and `max(exposure_score, 1)` — identical to `compute_stat_res` / `compute_boss_ai_score` in shipped `ai_exposure_transformer.py` lines 59, 68. |
| 5 | MCP server extension | **PARTIALLY FIXED** | File Changes lists `src/mcp_server/futureproof_server.py` Modify; §3 shows the extended `AI_EXPOSURE_RESPONSE_FIELDS`. **Residual:** spec does NOT extend `_JSON_STRUCT_FIELDS` (currently `top_5_activities`, `top_human_activities`, `burnout_drivers` at lines 21-25 of `futureproof_server.py`). The new `task_breakdown_automatable` and `task_breakdown_human` are stored as JSON-encoded strings in Iceberg (per the batch script at lines 354-355 of v3). Without adding both to `_JSON_STRUCT_FIELDS`, Gemma/the backend receives raw JSON strings instead of native Python arrays — the `_decode_json_struct_fields` centralization is bypassed. |
| 6 | Batch script resumable/deterministic | **PARTIALLY FIXED** | Checkpoint file present (good). `temperature=0.0, seed=42` present (good). **Residuals:** (a) `OLLAMA_MODEL = "gemma2:27b"` — this is the wrong model for the project. Per `docs/specs/cloud-gemma-deployment.md` line 151, the local Ollama config is `"model": "gemma4:26b-a4b"`. The spec pins a model the project doesn't ship with. (b) No `format="json"` on the `ollama.generate` call — Ollama's native JSON mode is the correct tool and avoids the markdown-fence stripping hack at lines 344-347. (c) No retry loop on JSON failures — the script writes the error row and moves on, never retries. v2 asked for "retry up to 3 times before marking errored." (d) Still writes one big JSON file (`OUTPUT_PATH.write_text(json.dumps(results, indent=2))` at line 319) — v2 asked for JSONL per-row writes so a mid-batch kill doesn't lose all progress; the current code rewrites the full file every 10 rows, which is checkpointed but fragile. (e) `time.sleep(0.5)` between calls is unchanged — fine for local Ollama. |
| 7 | Cache path outside `.gitignore` | **NOT FIXED** | Spec claims `data/gemma_cache/` is "outside .gitignore". **This is wrong.** `.gitignore` line 2 is `data/` (wholesale). Everything under `data/` is ignored, including `data/gemma_cache/`. A fresh clone cannot rebuild Gold without re-running the 1.5-hour Ollama batch — the reproducibility story collapses. **Fix:** move the committed artifact to `governance/fixtures/gemma_ai_exposure_scores.jsonl` (outside gitignore, where auditable artifacts live), and keep `data/gemma_cache/` as the working local cache only. OR add `!data/gemma_cache/` as an exception in `.gitignore`. |
| 8 | Blending truth table + grain/dedup | **MOSTLY FIXED** | 4-cell table (Gemma x Karpathy) present and coherent. `scoring_model` and `karpathy_score` values explicit per cell. Union semantics clear. **Residuals:** (a) `blend_scores` in §4 returns rows missing `record_id` and `promoted_at` — these are required fields on the Gold schema (NestedField 1 and 9). The function must call `compute_grain_id(row, ['soc_code'], prefix='aie')` and stamp `promoted_at` before promote. (b) Karpathy Silver can have multiple rows per SOC (see `_dedup_by_soc_code` in `src/silver/karpathy_ai_exposure_transformer.py` lines 285-318 — dedup by highest `num_jobs_2024`). Spec treats `karpathy_rows` as `dict[str, dict]` (one-per-SOC) but does not state where that dedup happens. State: "karpathy input is pre-deduped by `_dedup_by_soc_code`; the Gold blender assumes one row per SOC from each Silver source." (c) "Gemma error" rows (from the batch script `error` field) — §4 doesn't state whether these are filtered before blending or fall through to Karpathy fallback. Make it explicit: `error != null` should be treated as "Gemma missing". |
| 9 | DQ rule location and full contract list | **NOT FIXED** | Spec says `dq/rules/gemma_ai_exposure_rules.py`. Repo convention is `governance/dq-rules/` and rules are **JSON files** (e.g., `governance/dq-rules/gold-ai-exposure.json`, `silver-base-karpathy-ai-exposure.json`), not Python modules. Either (a) adopt the JSON convention and create `governance/dq-rules/raw-gemma-ai-exposure.json`, `silver-base-gemma-ai-exposure.json`, and update `gold-ai-exposure.json` for the new blended output; or (b) if Python-based rules are a new pattern, justify it. Also File Changes lists only `raw-gemma-ai-exposure.yaml` and `base-gemma-ai-exposure.yaml`. **Missing:** the updated `governance/data-contracts/consumable-ai-exposure.yaml` (this file exists today and must be updated for the 4 new columns). Also missing: updated `governance/data-contracts/mcp-ai-exposure.yaml` (this file also exists today and describes the MCP surface — needs the 4 new response fields). |
| 10 | Re-promotion order explicit | **NOT FIXED** | No explicit statement in §4 that `src/gold/ai_exposure_transformer.py` must run before `src/gold/futureproof_engine.py`. The architecture overview diagram shows the order pictorially but §4 prose does not say it. Implementer will discover this by breaking the build. Add one line: "Run order: (1) `src/gold/ai_exposure_transformer.py`, (2) `src/gold/futureproof_engine.py` — the engine reads blended `consumable.ai_exposure` via `ai_by_soc`." |

#### Data Flow Analysis

The v3 data flow is coherent:
```
consumable.onet_work_profiles  + consumable.occupation_profiles
    -> scripts/gemma_ai_exposure_scorer.py (Ollama, deterministic, checkpointed)
    -> data/gemma_cache/ai_exposure_scores.json (BUT: gitignored, see #7)
    -> raw.gemma_ai_exposure (Bronze)
    -> base.gemma_ai_exposure (Silver, SOC normalize + join validate)
    -> consumable.ai_exposure (Gold blend: Gemma preferred, Karpathy fallback)
    -> consumable.program_career_paths + career_branches (re-promoted by futureproof_engine)
    -> MCP get_ai_exposure (extended response; BUT: _JSON_STRUCT_FIELDS missing task_breakdown_*, see #5)
```

#### Contract Review

- **Gold schema:** 13 columns correctly specified. Backward-compatible.
- **MCP `AI_EXPOSURE_RESPONSE_FIELDS`:** correctly extended with 4 new fields.
- **MCP `_JSON_STRUCT_FIELDS`:** not extended — see #5 residual.
- **Pydantic `CareerOutcome.scoring_model`:** §3 says this is added to `backend/app/models/career.py`. Confirm in code review that `CareerOutcome` is the right model (vs. `CareerPath` or `CareerPathEntry` in the same file — implementer must pick the correct one).
- **Data contracts:** `consumable-ai-exposure.yaml` and `mcp-ai-exposure.yaml` both exist today and both need updating; File Changes misses both.

#### Findings

##### Sound
- Filename conventions aligned with repo (`*_transformer.py`).
- Schema preservation + stat formulas now exactly match shipped code.
- Blending truth table is explicit and union-semantic.
- Checkpointing and determinism (seed + temperature=0) are correct.
- AI-estimated disclaimer added to §3 — closes the provenance gap the data reviewer flagged.

##### Concerns

- **Wrong Ollama model tag.** `gemma2:27b` is not this project's model. Per `docs/specs/cloud-gemma-deployment.md`, local is `gemma4:26b-a4b`, cloud is `google/gemma-4-26b-a4b-it`. **Impact:** batch script will fail on `ollama pull gemma2:27b` or silently run against a different model than everything else in the stack. **Recommendation:** pin `OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:26b-a4b")`. Record the resolved tag on every row for audit.

- **Cache path gitignore claim is wrong.** `.gitignore` line 2 is `data/`. Everything under `data/` is untracked. **Impact:** the "committed for reproducibility" story fails. **Recommendation:** move the persisted artifact to `governance/fixtures/gemma_ai_exposure_scores.jsonl` and reserve `data/gemma_cache/` for the local working cache only. Update File Changes.

- **Missing `_JSON_STRUCT_FIELDS` extension.** The new `task_breakdown_automatable` / `task_breakdown_human` fields are stored as JSON-encoded strings (per batch script lines 354-355 and Gold schema `StringType()`), but are not added to the MCP decoder list. **Impact:** callers receive JSON strings instead of native arrays; frontend/Gemma cannot consume them without ad-hoc parsing. **Recommendation:** extend `_JSON_STRUCT_FIELDS` to include both new fields.

- **DQ rule path wrong.** Spec says `dq/rules/*.py`. Repo uses `governance/dq-rules/*.json`. **Impact:** rules land in wrong location and wrong format; CI will not discover them. **Recommendation:** create `governance/dq-rules/raw-gemma-ai-exposure.json`, `governance/dq-rules/silver-base-gemma-ai-exposure.json`, and update `governance/dq-rules/gold-ai-exposure.json` for the new blended output. Match the existing JSON schema used in neighboring rule files.

- **Missing data-contract updates.** File Changes lists only the 2 new raw/silver contracts. The existing `governance/data-contracts/consumable-ai-exposure.yaml` needs the 4 new columns appended, and `governance/data-contracts/mcp-ai-exposure.yaml` needs the 4 new response fields appended. **Impact:** contracts drift from reality; `bs:stamp` verification fails. **Recommendation:** add both files to File Changes as Modify.

- **Blender output missing `record_id` and `promoted_at`.** `blend_scores` in §4 returns dicts without these two required fields. The downstream `promote()` call requires both. **Impact:** Iceberg insert fails on required-field violation. **Recommendation:** after `blend_scores` returns, call `add_record_ids(blended, promoted_at=now_utc())` using the existing helper in `ai_exposure_transformer.py` lines 108-116.

- **Task-activity JSON escape bug in prompt.** `json.dumps(onet.get("top_5_activities", []))` double-encodes because the Gold field is already a JSON string. **Impact:** prompt contains `"[{\\"activity\\": ...}]"` — parseable but noisy and wastes tokens. **Recommendation:** `top5 = json.loads(onet["top_5_activities"]) if onet.get("top_5_activities") else []` before `json.dumps`. Same for `top_human_activities`.

- **No Ollama `format="json"`.** The batch script relies on prompt discipline and markdown-fence stripping to get JSON. Ollama supports native JSON mode via `format="json"` in `ollama.generate`. **Impact:** parse failures will occur on ~5-10% of rows; without retry (also missing), those rows drop to `error`. **Recommendation:** add `format="json"` to the options + implement a `MAX_RETRIES=3` loop inside `score_occupation`.

- **Re-promotion order prose.** Not stated. **Impact:** implementer may run `futureproof_engine` first and cache stale `ai_by_soc`. **Recommendation:** add one sentence to §4 after the architecture diagram.

- **Karpathy Silver dedup assumption.** `blend_scores` receives `karpathy_rows: dict[str, dict]`, implying one-row-per-SOC. The Silver table currently dedups via `_dedup_by_soc_code` (highest `num_jobs_2024` wins), but the spec doesn't state this is the source of `karpathy_rows`. **Impact:** if someone reads raw Silver without dedup, blending is non-deterministic. **Recommendation:** add "karpathy_rows is pre-deduped by soc_code in the Silver reader" to §4.

##### Blockers
None. All residuals are mechanical and fixable in under an hour.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUESTED
- [ ] REJECTED

#### Conditions (must fix before implementation)
1. Pin the correct Ollama model tag: `gemma4:26b-a4b` (match `docs/specs/cloud-gemma-deployment.md`). Read from `.env` when possible. Record the resolved tag per row.
2. Move the persisted Gemma cache out of `data/` (gitignored) to `governance/fixtures/gemma_ai_exposure_scores.jsonl`. Update File Changes. Switch to JSONL per-row append for mid-run crash safety.
3. Extend `_JSON_STRUCT_FIELDS` in `futureproof_server.py` to include `task_breakdown_automatable` and `task_breakdown_human`. Call this out in §3 and in File Changes.
4. Fix DQ rule path: use `governance/dq-rules/*.json` (matching existing rule files, e.g., `gold-ai-exposure.json`), not `dq/rules/*.py`. Create 2 new and update 1 existing JSON rule file.
5. Add to File Changes: Modify `governance/data-contracts/consumable-ai-exposure.yaml` (new columns) and Modify `governance/data-contracts/mcp-ai-exposure.yaml` (new response fields).
6. Have `blend_scores` call `add_record_ids(blended, promoted_at=now_utc())` — or inline `record_id`/`promoted_at` — before handing rows to `promote()`.
7. `json.loads` the JSON-string fields (`top_5_activities`, `top_human_activities`) before re-serializing into the prompt; add `format="json"` to `ollama.generate` and a 3-retry loop inside `score_occupation`.
8. State re-promotion order in §4 prose: `ai_exposure_transformer.py` first, then `futureproof_engine.py`.
9. State that `karpathy_rows` in `blend_scores` is pre-deduped by SOC via the Silver reader (matching `_dedup_by_soc_code` behavior).

### @fp-data-reviewer Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-16 (v3 re-review)

#### Re-review Context
This is a re-review of v3 against the seven "Significant" data concerns raised on v2 (stat formulas, reproducibility, A/B gates, distribution DQ, category preservation, provenance disclaimer, fallback coverage). Source-of-truth traced to: `src/gold/ai_exposure_transformer.py` (shipped formulas), `src/silver/karpathy_ai_exposure_transformer.py` (Silver grain + `bls_match` semantics + `_dedup_by_soc_code`), `src/gold/onet_work_profiles.py` (O*NET column names), `src/mcp_server/futureproof_server.py` (MCP field list and JSON decode set).

#### v2 Concern Resolution Matrix

| # | v2 Concern | v3 Resolution | Verified Against | Status |
|---|-----------|---------------|------------------|--------|
| 1 | Formula divergence (v2 spec said `10 - exposure_score`) | v3 §4 now states `MIN(11 - exposure_score, 10)` and `MAX(exposure_score, 1)` and includes `compute_stat_res` / `compute_boss_ai_score` helpers verbatim | `src/gold/ai_exposure_transformer.py:51-68` — byte-identical | **Resolved** |
| 2 | Reproducibility (temperature, model tag, per-row lineage) | v3 pins `temperature=0.0, seed=42` in `OLLAMA_OPTIONS` and records `model_tag` per row in scorer output | v3 §4 `scripts/gemma_ai_exposure_scorer.py` block | **Resolved at scorer** — but `model_tag` does NOT land on the Gold schema (see D1) |
| 3 | A/B validation gates | v3 §4 defines 5 numerical gates (r≥0.6, MAD≤2.0, mean Δ∈[-1,1], category bias ≤2.0, mode ≤40%) | `validate_ab_comparison` code block | **Partially resolved** — gates present; std-dev floor, bucket coverage, and outlier list from v2 are still missing (see A1) |
| 4 | Distribution DQ rules | v3 §4 adds `check_distribution_collapse` (≤40% mode), `check_score_range` (0-10 integer), `check_task_breakdown_structure` (JSON list of strings) | v3 §4 code block | **Partially resolved** — mode-collapse in, 6 of 8 v2-requested rules still missing (see D2) |
| 5 | `category` preservation | v3 blender sets `category = karpathy["category"] if karpathy else "Unknown"` (line 484); Gold schema keeps `category` required | v3 §4 `blend_scores` + Gold schema | **Partially resolved** — escape hatch exists, but "Unknown" becomes the majority bucket for the ~456 Gemma-only SOCs (see C1) |
| 6 | Provenance disclaimer | v3 §3 adds Fight AI disclaimer "AI exposure estimated by Gemma 4 using O*NET task data" when `scoring_model="gemma-4"`; receipts surface `scoring_model` | v3 §3 | **Resolved for Fight AI** — career-card RES tooltip still silent (see P1) |
| 7 | Fallback coverage edge case | v3 §4 truth table is explicit (4 cells, Gemma preferred, Karpathy fallback, union semantics). Coverage documented as 798 Gemma + ~42 Karpathy-only = ~840 | v3 §4 blending truth table | **Resolved** — blender code matches table; union semantics correct |

Five of seven v2 concerns are materially resolved. Two (A/B gates, DQ rules) were only partially addressed, and additional residuals surface against v3's actual text (below).

---

#### Data Quality Sound

- **Formulas match shipped code exactly.** v3's `compute_stat_res` and `compute_boss_ai_score` are byte-identical to `ai_exposure_transformer.py:51-68`. The "no stat below 1" invariant holds: `stat_res` caps at 10 for `exposure_score=0` and floors at 1 for `exposure_score=10`; `boss_ai_score` floors at 1 via `MAX`. No regression.
- **Blending truth table matches blender code.** All 4 cells of §4 table agree with `blend_scores`: Gemma+Karpathy → Gemma with Karpathy `category` carried + `karpathy_score` preserved; Gemma-only → Gemma with `category="Unknown"` + `karpathy_score=NULL`; Karpathy-only → Karpathy with `scoring_model="gemini-flash"`; missing+missing → excluded. Union semantics correctly implemented via `set(gemma_rows) | set(karpathy_rows)`.
- **Karpathy-only rows correctly carry NULL task_breakdowns** (v3 lines 500-501). The `task_breakdown_*` fields are genuinely Gemma-only; not a UI surprise.
- **Gold schema preservation is explicit.** v3 §4 keeps `record_id`, `category`, `promoted_at` as required (per v2 blocker). New fields marked optional where appropriate; `scoring_model` required. Backward-compatible.
- **Scorer determinism.** `temperature=0.0`, `seed=42`, pinned `OLLAMA_MODEL`, per-row `model_tag` and `scored_at` — the reproducibility floor is in place at the scorer layer.
- **O*NET column names corrected.** v3 uses `primary_title` (not `occupation_title`), drops the phantom `context_summary`, synthesizes from `time_pressure` / `work_hours` instead. Verified against `src/gold/onet_work_profiles.py:105-143` — all referenced fields exist.

---

#### Data Concerns (Significant)

##### A1. A/B Gate Thresholds Are Defensible But Incomplete

The 5 gates are reasonable for a 0-10 integer scale, with two caveats:

- **Gate 1 (r ≥ 0.6):** Defensible. For a 0-10 integer scale with ~300 overlap points, r ≥ 0.6 is low-moderate — consistent with "Gemma should agree directionally with Karpathy but may legitimately disagree on specific rungs." Do NOT tighten; a higher threshold punishes Gemma for improving on Karpathy.
- **Gate 2 (MAD ≤ 2.0):** Defensible. 2 points on a 0-10 scale = 20% average disagreement. Combined with Gate 1, catches both systematic drift and high-variance rescoring.
- **Gate 3 (mean Δ ∈ [-1, 1]):** Defensible. Catches systematic skew (Gemma always-higher) without punishing random noise.
- **Gate 4 (category bias ≤ 2.0):** Defensible for the stated purpose. **Watch:** small-N categories can have a large mean Δ by chance. **Fix:** gate only categories with `len(deltas) >= 10`; smaller categories are reported but not blocking.
- **Gate 5 (mode ≤ 40%):** Defensible. Mode-collapse guardrail.

**Still missing from v2 request:**

- **Std-dev floor (`std_dev(exposure_score) >= 1.5`):** v2 asked; v3 silent. Mode can be ≤40% while the distribution is still compressed (e.g., 35/30/25% on three adjacent integers passes mode but has std ~0.8). **Fix:** add `gate6_pass = statistics.stdev(gemma_vals) >= 1.5`.
- **Bucket coverage (`≥10%` each of 0-3, 4-6, 7-10):** v2 asked; v3 silent. Catches bimodal collapse (Gemma scores everything as 2 or 8, nothing mid-range). **Fix:** three-bucket histogram check with 10% floor per bucket.
- **Outlier list (`|Gemma - Karpathy| ≥ 4`):** v2 required a human-reviewable table of large divergences in the comparison report. v3 gates aggregate stats but does not require the outlier list. **Fix:** `reports/gemma_vs_karpathy_comparison.md` must include a table of all SOCs where `|Δ| >= 4` with Gemma rationale + Karpathy rationale side-by-side. This is the one mechanism that catches "Gemma is systematically wrong on a specific, correctable occupation" which correlation/MAD will never surface.

**Risk:** As-spec'd, Gemma can ship a 4-6 compressed distribution with no individual-occupation audit trail. Student sees a RES stat that is indistinguishable across half the workforce; we have no evidence of which specific Gemma decisions were wrong.

##### A2. A/B Gates Are "Fail-Open" Unless Explicit

v3 §4 returns `overall_pass: False` but does not say what happens next. Does a failing gate block the Gold promote? Ship with a warning? Revert to Karpathy-only? **Fix:** add one sentence to §4: "If `overall_pass=False`, the Gold promote is blocked; operator must either (a) revise the prompt and re-run the batch, or (b) explicitly override with a documented rationale in §6." Otherwise the gates are decorative.

##### D1. Reproducibility Does Not Reach Gold Schema

Scorer records `model_tag` per row; Bronze/Silver presumably carry it forward. **Gold schema does not include `model_tag`.** The 13 columns are: existing 9 + `task_breakdown_automatable`, `task_breakdown_human`, `scoring_model`, `karpathy_score`. `scoring_model` tells you "gemma-4" vs "gemini-flash" but not the specific Ollama tag (e.g., `gemma4:26b-a4b@sha256:...`). If Gemma scores drift when someone re-pulls the image, we cannot prove which rows came from which tag.

**Fix:** Add `model_tag` (StringType, required=True) to the Gold schema → 14 columns. For Karpathy rows, set to `"karpathy-gemini-flash@2024-04"` (or whatever the Karpathy batch encodes). Cheap audit column; satisfies the "auditable pipeline" claim in v3 §1.

**Risk without fix:** Hackathon writeup claims reproducibility; judges ask "which Gemma version?"; we cannot answer at the row level.

##### D2. DQ Rules Still Light Relative to v2 Request

v3 adds 3 DQ rules. v2 requested 8. Score: 3/8.

| Rule | v2 Requested | v3 Status | Fix |
|------|--------------|-----------|-----|
| Coverage (`row_count >= 780`) | Yes | Missing | Add `check_row_count` at Silver with ≥780 threshold (≤2.3% failure tolerance on 798) |
| Null/error rate (`error non-null ≤ 3%`) | Yes | Missing | Add `check_error_rate` at Silver |
| Std-dev floor (`std_dev >= 1.5`) | Yes | Missing | Add to `check_distribution_collapse` |
| Bucket coverage (`≥10%` each of 0-3, 4-6, 7-10) | Yes | Missing | Add `check_bucket_coverage` |
| Rationale length (50-800 chars) | Yes | Missing | Add `check_rationale_length` at Silver |
| Task breakdown non-empty (≥1 per list) | Partial (structure-only) | Structure only | Extend `check_task_breakdown_structure` to fail on empty lists |
| No duplicate SOCs | Yes | Missing | Add `check_no_duplicate_socs` at Silver |
| `model_tag` lineage (single tag per batch) | Yes | Missing | Add `check_single_model_tag` at Silver |

**Fix:** expand DQ rules with the 6 missing checks. All trivially implementable; each catches a specific, observed failure mode. (Note: @fp-architect also flagged that the file path should be `governance/dq-rules/*.json`, not `dq/rules/*.py`.)

**Risk:** without these, a Gemma batch that scores 500/798 occupations successfully (63% coverage), or produces 300 identical rationales, or leaves 40% of task_breakdowns empty, passes v3's DQ and promotes to Gold. No automated signal.

##### C1. `category = "Unknown"` Is a Silent Quality Regression for 456 Rows

v3 line 484: `"category": karpathy["category"] if karpathy else "Unknown"`. Since Karpathy covers 342 SOCs and Gemma covers 798, **approximately 456 Gemma-only SOCs will get `category="Unknown"`** — the majority of the blended table. The `category` field drives:

- MCP response grouping ("Healthcare Practitioners", "Computer and Mathematical", etc.)
- Receipt readability
- **A/B Gate 4 (category bias)** — which would now have "Unknown" as its largest bucket, hollowing out that gate for 54% of rows.

**Fix:** Derive `category` from the SOC 2018 major group (first 2 digits of SOC) for Gemma-only rows. Mapping is static (SOC prefix → label), already used in BLS OOH Silver output. Pseudocode:

```python
category = karpathy["category"] if karpathy else SOC_MAJOR_GROUP_LABELS.get(soc[:2], "Unknown")
```

Fallback to "Unknown" only when the 2-digit prefix is unrecognized (should be zero for BLS-joined rows). This also restores Gate 4's meaning.

**Risk:** Category-level bias check (Gate 4) is useless in practice: "Unknown" becomes the dominant bucket and Silicon-Valley-engineer vs rural-farmer both bucket there.

##### P1. Provenance Disclaimer Scope Too Narrow

v3 §3 adds the "AI-estimated" disclaimer to Fight AI boss detail. Good — but the RES stat is surfaced earlier: on the career card pentagon tooltip (where the user first meets RES) and in the `/stats` receipts. The disclaimer should attach wherever RES is rendered when `scoring_model="gemma-4"`, not only on the Fight AI drill-down.

**Fix:** surface `scoring_model` on the `/stats` endpoint response; have the career-card RES tooltip append `"· AI-estimated"` when `scoring_model="gemma-4"`. Keep it short — a full sentence clutters the card. First impression is where trust is set; the Fight AI screen is too late.

##### S1. MCP JSON Decode Set Not Updated (Breaks End-to-End)

v3 §3 extends `AI_EXPOSURE_RESPONSE_FIELDS` to include `task_breakdown_automatable` and `task_breakdown_human`. But those fields are stored as **JSON strings** in Iceberg (per the scorer at v3 lines 354-355: `json.dumps(result["task_breakdown"]["automatable"])`). The MCP server decodes JSON-string columns via `_JSON_STRUCT_FIELDS` (currently `top_5_activities`, `top_human_activities`, `burnout_drivers` — verified at `src/mcp_server/futureproof_server.py:21-25`).

**v3 does not add the two new task_breakdown fields to `_JSON_STRUCT_FIELDS`.** Result: Gemma (the MCP consumer) receives literal escaped JSON strings instead of parsed arrays. The entire task-breakdown feature is broken end-to-end.

This was called out in the v2 architect review (condition 5) and is still flagged in v3's architect review. Re-stating here because it is also a data-integrity concern: the `task_breakdown_*` fields would be the only "Gemma shows its work" surface, and a missed decoder line silently nullifies it.

**Fix:** v3 §3 must also add `task_breakdown_automatable` and `task_breakdown_human` to `_JSON_STRUCT_FIELDS`. One-line change.

#### Data Concerns (Minor)

- **Coverage math.** v3 says "Overlap: ~300 occupations" and "Union: ~840". Karpathy has 342 Bronze rows; Silver expands with broad-SOC expansion and then dedups to one-per-SOC, yielding ~400-500 rows at Silver; Gold then filters to `bls_match=true`. Actual overlap depends on which Karpathy table the blender reads. **Fix:** v3 §4 should explicitly state that `karpathy_rows` comes from `base.karpathy_ai_exposure` filtered to `bls_match=true`, then expressed as `dict[soc_code, row]` (single row per SOC via Silver's `_dedup_by_soc_code`). Architect review already flagged this; restating because it affects the coverage and Gate 4 math.
- **Error-row handling between Bronze and blender.** v3 blender checks `gemma.get("exposure_score") is not None`, which handles error rows implicitly (they have no score). But the Bronze ingestor and Silver transformer are not described in v3 — are error rows promoted? If yes, `exposure_score` should be NULL (valid Iceberg optional) so the blender check works. **Fix:** one sentence in §4: "Bronze rows with `error != NULL` are promoted to Silver with `exposure_score = NULL`; Silver DQ fails the batch if >3% of rows are error rows (per D2 above)."
- **Resumability test coverage.** P1 test `test_resumability` exists. Good. Add P1 test `test_corrupted_checkpoint_does_not_crash_batch` — a truncated/malformed `checkpoint.json` should log and start fresh, not crash.

#### Disclaimer Check
- [x] AI-estimated values labeled on Fight AI — present in §3
- [ ] AI-estimated label on career-card RES tooltip — **Missing** (see P1)
- [x] Confidence propagation — N/A at this layer (crosswalk tier is upstream)
- [x] Required disclaimer strings specified for Fight AI
- [x] Missing-data state defined (blender excludes row → `stat_res=NULL` propagates → UI shows insufficient data per existing `futureproof_engine.py` semantics)

#### Data Integrity Blockers
None. All concerns are correctable without restructuring the v3 design. Formula correctness is solid. The blender truth table is solid. What remains is filling the DQ/auditability surface and the one-line MCP decoder fix that makes `task_breakdown_*` actually reach the consumer.

#### Conditions to Clear to APPROVED
1. **A/B gates:** add std-dev floor (≥1.5), bucket coverage (≥10% each of 0-3, 4-6, 7-10), and outlier list (`|Δ|≥4` as a markdown table in `gemma_vs_karpathy_comparison.md`). Gate 4 (category bias): guard with `len(deltas) >= 10` minimum sample.
2. **A/B fail policy:** one sentence in §4 stating `overall_pass=False` blocks Gold promote until resolved or explicitly overridden.
3. **Gold schema:** add `model_tag` (StringType, required=True) → 14 columns total. Populate from scorer on Gemma rows; constant string on Karpathy rows.
4. **DQ rules:** add the 6 missing rules (coverage count, error rate, std-dev, bucket coverage, rationale length, duplicate SOCs, single-model-tag). Extend `check_task_breakdown_structure` to fail on empty lists.
5. **Category derivation:** for Gemma-only rows, use SOC 2018 major-group labels (first 2 digits of SOC), not `"Unknown"`. Document the mapping source.
6. **MCP JSON decode:** v3 §3 must add `task_breakdown_automatable` and `task_breakdown_human` to `_JSON_STRUCT_FIELDS` in `futureproof_server.py`.
7. **Disclaimer scope:** surface `scoring_model` on `/stats` endpoint and append "· AI-estimated" to the career-card RES tooltip when `scoring_model="gemma-4"`.
8. **Karpathy source statement:** explicit sentence in §4 that the blender reads Karpathy from `base.karpathy_ai_exposure` filtered `bls_match=true`, pre-deduped by SOC.

Items 1, 3, 4, 6 are tight-loop code fixes. Items 2, 5, 7, 8 are documentation. None block a v4 turn-around — estimate under two hours of spec work.

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

### Reviewer Feedback Addressed

This v3 spec addresses all 12 issues from the architecture + data reviewer feedback:

| # | Issue | Resolution |
|---|-------|------------|
| 1 | Filenames use `*_promoter.py` | Changed to `*_transformer.py` per repo convention |
| 2 | Prompt reads wrong column names | Fixed: `primary_title`, removed `context_summary`, use actual O*NET columns |
| 3 | stat_res formula divergence | Fixed: use `MIN(11 - exposure_score, 10)` from shipped code |
| 4 | boss formula divergence | Fixed: use `MAX(exposure_score, 1)` from shipped code |
| 5 | Schema silently drops required fields | Fixed: preserve `category`, `record_id`, `promoted_at`; append new fields |
| 6 | MCP fields not extended | Fixed: added `AI_EXPOSURE_RESPONSE_FIELDS` extension spec |
| 7 | Batch script not resumable/deterministic | Fixed: checkpoint file, `temperature=0`, model tag pinning |
| 8 | Cache path in .gitignore | Fixed: use `data/gemma_cache/` (outside .gitignore) |
| 9 | Blending truth table missing | Fixed: full truth table with union semantics documented |
| 10 | A/B report has no numerical gates | Fixed: 5 automated gates with thresholds |
| 11 | Silver DQ missing distribution checks | Fixed: mode collapse rule (<40% max concentration) |
| 12 | §3 "no UI changes" claim wrong | Fixed: added AI-estimated disclaimer requirement for Fight AI |

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

### Estimated Effort

| Step | Estimate |
|------|----------|
| Prompt engineering + validation (10-20 occupations) | 2-3 hours |
| Batch scoring run (798 occupations, resumable) | 1-2 hours (mostly waiting) |
| Pipeline ingest (Bronze → Silver → Gold) | 2-3 hours |
| A/B comparison report with gates | 1-2 hours |
| MCP + receipts + model updates | 1 hour |
| Tests + DQ rules | 1-2 hours |
| **Total** | **9-14 hours** |

---

*— End of Spec —*
