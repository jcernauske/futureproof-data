# Feature: Three-Signal AI Exposure Composite (S4)

## Claude Code Prompt

```
Read the spec at docs/specs/three-signal-ai-exposure-composite.md in its entirety.

Execute the following workflow:

1. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (system architecture, data flow, Brightsmith integration)
   - Invoke @fp-data-reviewer to review data quality implications — especially the Anthropic observed exposure ingest and the composite formula
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
   - Generate report to reports/three-signal-ai-exposure-composite-YYYY-MM-DD.md
   
   **CRITICAL: Update the PRD**
   - Open `docs/futureproof_hackathon_prd_v8.md`
   - Find the Stretch Specs table in the "Spec Backlog" section
   - Change S4 `three-signal-ai-exposure-composite` status from "⬜ Not started" to "✅ Complete"
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
| Created | 2026-04-14 |
| Author | Jeff + Claude Desktop |
| Spec Version | 2.0 |
| Last Updated | 2026-04-16 |
| Blocked By | `gemma-ai-exposure-rescore` (S1 — Gemma task-level scoring must run first) |
| Related Specs | `raw-ingest-karpathy-ai-exposure`, `gemma-ai-exposure-rescore` (S1), `gold-futureproof-engine`, `gold-futureproof-engine-addendum-cip-fix` |
| Priority | Bonus — ships if time allows after core frontend + S1 |

---

## §1 Feature Description

### Overview

Replace the single-source RES stat (Karpathy 0–10 score) with a **three-signal composite** that blends:
1. **Theoretical AI capability** — Gemma task-level scores from S1
2. **Observed AI adoption** — Anthropic Economic Index real-world usage data
3. **Velocity** — How fast AI is closing the gap (observed/theoretical ratio)

This produces a RES stat that answers three questions simultaneously:
- How much of this job *could* AI do? (theoretical ceiling)
- How much of this job *is* AI doing right now? (current reality)
- How fast is AI closing the gap? (adoption trajectory)

### Problem Statement

Even Gemma's task-level scores (from S1) remain *theoretical* — they estimate what AI *could* do, not what it *is* doing.

Anthropic published empirical data (March 2026) measuring which occupation tasks are actually being performed by AI, based on millions of real Claude conversations. This is the only public dataset that measures observed AI adoption by occupation:
- Computer programmers: 74.5% observed exposure
- Customer service reps: 70.1%
- Data entry keyers: 67.1%
- 30% of occupations: near-zero exposure

The gap between theoretical capability and observed adoption is itself a signal — it indicates how quickly AI is actually arriving in that occupation.

A student choosing between two careers that both score 7/10 on theoretical exposure could see very different risk profiles:
- Career A: 70% observed (AI is already here)
- Career B: 15% observed (theoretical risk, slow adoption)

That distinction matters for career planning.

### Hackathon Writeup Value

This is a standout Technical Depth story:

> "We didn't just use someone else's AI scores. We built a three-signal composite: Gemma evaluates which tasks AI *could* automate from O*NET data, Anthropic's Economic Index measures which tasks AI *is* automating from real-world usage, and the ratio between them reveals how fast AI is arriving in each career. Students see theoretical risk, current reality, and velocity — not just a single number."

### Success Criteria

- [ ] Anthropic observed exposure data extracted and ingested into `raw.anthropic_observed_exposure`
- [ ] Silver base table `base.anthropic_observed_exposure` produced with normalized SOC codes
- [ ] `consumable.ai_exposure` updated with three signals + composite score + velocity metric
- [ ] Composite RES formula produces a 1–10 integer score
- [ ] `consumable.program_career_paths` re-promoted with composite `stat_res` and `boss_ai_score`
- [ ] `consumable.career_branches` re-promoted with composite `stat_res` delta
- [ ] Fight AI boss narrative prompt updated to reference observed vs. theoretical exposure
- [ ] DQ rules written and passing at each zone
- [ ] A/B comparison: composite vs. Karpathy-only vs. Gemma-only for 50 representative occupations
- [ ] Coverage report: how many SOC codes have all three signals, two, or one (with fallback behavior documented)

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Three-signal weighted composite | Anthropic = current snapshot, Gemma = theoretical ceiling, velocity = trajectory. All three are independently useful and non-redundant. | Replace Karpathy with Anthropic alone (loses theoretical vs. observed distinction) |
| 2 | Velocity = observed / theoretical (cross-sectional ratio) | Anthropic has few time-series data points; ratio naturally captures "how much of theoretical ceiling has been realized" | Time-series delta (insufficient data points) |
| 3 | Weights: 40% theoretical, 35% observed, 25% velocity | Theoretical gets highest weight because it represents *eventual* risk (students planning 10+ years out). Observed is empirical. Velocity is a modifier. | Equal weights (doesn't reflect planning horizon), Majority observed (bad for long-term planning) |
| 4 | Graceful degradation for missing signals | Not all SOC codes have all three signals. Fall back to Gemma-only → Karpathy-only → null. Provenance tracks which signals contributed. | Require all three (reduces coverage) |
| 5 | Manual Anthropic data extraction | Published in research reports, not as API/CSV. One-time manual extraction is appropriate. | Build a scraper (fragile, unnecessary) |
| 6 | Velocity in narrative, not as sixth stat | Adding a stat would break the pentagon. Velocity is most useful as narrative context ("AI is arriving fast" vs. "wave hasn't hit yet"). | New stat (breaks pentagon), Ignore velocity (wastes signal) |

### Constraints

- Anthropic's observed exposure data is published at SOC major group level (22 groups) AND individual occupation level (top ~50). Coverage is incomplete for all 832 SOC codes. Fallback behavior is critical.
- Composite weights are initial estimates. A/B comparison will validate whether they produce reasonable orderings.
- This spec depends on S1 completing first. Without Gemma scores, degrades to two-signal (Karpathy + Anthropic) or Karpathy-only.

---

## §3 UI/UX Design

> Backend-only spec. No new UI screens.

**Downstream frontend impact:** The composite changes the *value* of `stat_res` and `boss_ai_score` but NOT the API shape. Pentagon renders the same 1–10 integer. Receipts endpoint gains provenance fields.

**Fight AI boss narrative enhancement:** Gemma prompt gains observed/theoretical/velocity context:

```
Observed AI Exposure: {observed_pct}% of tasks already performed by AI
Theoretical AI Exposure: {theoretical_score}/10
Velocity: {velocity_label} (AI is arriving {velocity_narrative} in this field)
```

This enables narratives like:
- "Financial analysts face serious AI pressure — not just in theory. AI is already handling 65% of tasks, and adoption is accelerating."
- "Construction managers have high theoretical exposure on paper, but only 8% of tasks are currently AI-assisted. The wave hasn't arrived yet — but it's on the horizon."

---

## §4 Technical Specification

### Architecture Overview

```
Signal 1: Gemma task-level scores (from S1)
  ↓ already in consumable.ai_exposure as exposure_score + task_breakdown
  
Signal 2: Anthropic observed exposure (NEW — this spec)
  ↓ raw.anthropic_observed_exposure → base.anthropic_observed_exposure
  
Signal 3: Velocity (COMPUTED — this spec)
  ↓ = observed / theoretical

All three → composite formula → stat_res (1–10) + boss_ai_score (1–10)
  ↓ re-promote consumable.program_career_paths + consumable.career_branches
```

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `data/raw/anthropic_cache/observed_exposure.json` | Create | Manually extracted Anthropic data |
| `src/raw/anthropic_observed_exposure_ingestor.py` | Create | Bronze ingestor |
| `src/silver/anthropic_observed_exposure_promoter.py` | Create | Silver promoter — SOC normalization + join validation |
| `src/gold/ai_exposure_composite_promoter.py` | Create | Gold promoter — three-signal composite formula |
| `src/gold/futureproof_engine_promoter.py` | Modify | Re-promote with composite `stat_res` and `boss_ai_score` |
| `backend/services/stats.py` | Modify | Receipts include signal breakdown |
| `backend/services/boss_fight.py` | Modify | Fight AI prompt includes observed/theoretical/velocity |
| `dq/rules/anthropic_observed_exposure_rules.py` | Create | DQ rules for Bronze + Silver |
| `dq/rules/ai_exposure_composite_rules.py` | Create | DQ rules for composite Gold |
| `data_contracts/ai_exposure_composite.yaml` | Create | Data contract for updated `consumable.ai_exposure` |

### Source Data: Anthropic Observed Exposure

**Source:** Anthropic's "Labor Market Impacts of AI" (March 2026) and "Anthropic Economic Index" reports.

**Publication URLs:**
- https://www.anthropic.com/research/labor-market-impacts
- https://www.anthropic.com/research/anthropic-economic-index-january-2026-report

**What to extract:**

1. **Per-occupation observed exposure %** — Top occupations with specific percentages:
   - Computer Programmers: 74.5%
   - Customer Service Reps: 70.1%
   - Data Entry Keyers: 67.1%
   - Medical Record Specialists: 66.7%
   - Market Research Analysts: 64.8%
   - Sales Reps: 62.8%
   - (~30-50 individual occupations total)

2. **Per-SOC-major-group observed exposure %** — 22 occupation groups:
   - Computer & Math: 35.8%
   - Office & Admin: 34.3%
   - Business & Finance: 28.4%
   - Sales: 26.9%
   - Legal: 20.4%
   - Arts & Media: 19.2%
   - Education & Library: 18.2%

3. **Per-SOC-major-group theoretical capability %** — 22 occupation groups:
   - Computer & Math: 94.3%
   - Business & Finance: 94.3%
   - Management: 91.3%
   - Office & Admin: 90%
   - Legal: 89%
   - Architecture & Engineering: 84.8%
   - Arts & Media: 83.7%

**JSON structure:**

```json
{
  "source": "Anthropic Labor Market Impacts of AI, March 2026",
  "source_url": "https://www.anthropic.com/research/labor-market-impacts",
  "extraction_date": "2026-04-XX",
  "extraction_notes": "Manually extracted from published figures/tables.",
  "occupations": [
    {
      "occupation_title": "Computer Programmers",
      "soc_code": "15-1251",
      "observed_exposure_pct": 74.5,
      "source_detail": "Figure X / Table Y"
    }
  ],
  "major_groups": [
    {
      "group_name": "Computer and Mathematical Occupations",
      "soc_major_group": "15-0000",
      "observed_exposure_pct": 35.8,
      "theoretical_capability_pct": 94.3,
      "source_detail": "Figure X"
    }
  ]
}
```

**Coverage strategy:**
- Occupations with specific per-occupation %: use directly
- Occupations without specific value but in known major group: use major group % as fallback, flag as `resolution = "major_group_fallback"`
- Occupations with neither: `observed_exposure_pct = null`, composite falls back to Gemma-only or Karpathy-only

### Data Model Changes

#### Raw Table: `raw.anthropic_observed_exposure`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| occupation_title | string | yes | As published by Anthropic |
| soc_code | string | no | May need manual resolution |
| soc_major_group | string | no | XX-0000 format |
| observed_exposure_pct | double | yes | 0–100 |
| theoretical_capability_pct | double | no | Available at major group level |
| resolution | string | yes | "direct" or "major_group" |
| source_detail | string | yes | Which figure/table |

**Expected rows:** ~70-100 (50-80 occupations + 22 major groups)

#### Silver Table: `base.anthropic_observed_exposure`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| soc_code | string | yes | Normalized XX-XXXX format |
| occupation_title | string | yes | Canonical title from our data |
| observed_exposure_pct | double | yes | 0–100 |
| theoretical_capability_pct | double | no | May be null |
| resolution | string | yes | "direct", "major_group_fallback", "title_fuzzy_match" |
| match_confidence | string | yes | "exact", "high", "moderate" |

#### Updated Gold Table: `consumable.ai_exposure`

New fields added to existing schema:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| observed_exposure_pct | double | no | From Anthropic |
| theoretical_capability_pct | double | no | From Anthropic major group |
| velocity_ratio | double | no | observed / (theoretical × 10), range 0.0–1.0 |
| velocity_label | string | no | "rapid" (>0.5), "moderate" (0.25–0.5), "slow" (0.1–0.25), "nascent" (<0.1) |
| composite_score | double | no | Raw weighted composite before rounding |
| composite_signals | string | no | JSON: which signals contributed |
| composite_method | string | no | "three_signal", "two_signal_no_anthropic", "gemma_only", "karpathy_only" |
| gemma_exposure_score | integer | no | Raw Gemma score preserved separately |

### Composite Formula

```python
def compute_composite_res(
    gemma_score: float | None,        # 0-10, from S1
    karpathy_score: float | None,     # 0-10, baseline
    observed_pct: float | None,       # 0-100, from Anthropic
    theoretical_pct: float | None,    # 0-100, from Anthropic major group
) -> tuple[int | None, str]:
    """
    Returns (composite_exposure_score 0-10, method_used).
    Higher composite = higher AI exposure = LOWER resilience.
    stat_res = 10 - composite_exposure_score (inverted).
    """
    
    # Determine theoretical signal (prefer Gemma, fall back to Karpathy)
    theoretical = gemma_score if gemma_score is not None else karpathy_score
    if theoretical is None:
        return (None, "no_data")
    
    # Normalize observed to 0-10 scale
    observed_normalized = (observed_pct / 10.0) if observed_pct is not None else None
    
    # Compute velocity
    if observed_normalized is not None and theoretical > 0:
        velocity_ratio = observed_normalized / theoretical  # 0.0–1.0+
        velocity_normalized = min(velocity_ratio * 10, 10)  # scale to 0–10
    else:
        velocity_ratio = None
        velocity_normalized = None
    
    # Three-signal composite
    if observed_normalized is not None and velocity_normalized is not None:
        composite = (
            0.40 * theoretical +
            0.35 * observed_normalized +
            0.25 * velocity_normalized
        )
        method = "three_signal"
    
    # Two-signal fallback (no Anthropic)
    elif observed_normalized is None:
        composite = theoretical
        method = "gemma_only" if gemma_score is not None else "karpathy_only"
    
    # Edge case
    else:
        composite = 0.55 * theoretical + 0.45 * observed_normalized
        method = "two_signal_no_velocity"
    
    return (round(max(0, min(10, composite))), method)
```

**Example computations:**

| Occupation | Gemma | Observed % | Velocity | Composite | Method | Interpretation |
|-----------|-------|-----------|----------|-----------|--------|---------------|
| Computer Programmer | 9 | 74.5% | 0.83 | 9 | three_signal | AI is here |
| Financial Analyst | 8 | 64.8% | 0.81 | 8 | three_signal | High all signals |
| Construction Manager | 5 | 8.0% | 0.16 | 4 | three_signal | Wave hasn't hit |
| Plumber | 2 | 1.0% | 0.05 | 2 | three_signal | Low across board |
| Niche occupation | 6 | null | null | 6 | gemma_only | No Anthropic data |

### Fight AI Boss Narrative Enhancement

```python
FIGHT_AI_PROMPT_ADDITION = """
## AI Exposure Context
- Theoretical AI capability: {theoretical_score}/10 — what AI *could* do
- Observed AI adoption: {observed_pct}% — what AI *is* doing now
- Adoption velocity: {velocity_label} — how fast AI is arriving
- Composite: {composite_score}/10

If observed >40%: emphasize AI is already reshaping this work today.
If observed low but theoretical high: "wave is building but hasn't hit yet."
If velocity rapid: warn gap is closing fast.
If velocity slow/nascent: note runway — time to prepare.
"""
```

### Receipts Enhancement

```python
class ResStatReceipt(BaseModel):
    stat_res: int
    composite_exposure_score: int
    composite_method: str
    gemma_theoretical_score: int | None
    karpathy_score: int | None
    anthropic_observed_pct: float | None
    velocity_ratio: float | None
    velocity_label: str | None
    task_breakdown_automatable: list[str] | None
    task_breakdown_human: list[str] | None
    source_note: str
```

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `tests/test_stats.py` | `test_pentagon_computation` | Medium | `stat_res` values change |
| `tests/test_boss_fight.py` | `test_fight_ai_score` | Medium | `boss_ai_score` values change |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `test_pentagon_computation` | Update expected values | Composite formula differs |
| `test_fight_ai_score` | Update expected values | Same reason |

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `test_ai_exposure_composite.py` | `test_three_signal_composite` | Formula produces expected scores |
| P0 | `test_ai_exposure_composite.py` | `test_graceful_degradation_no_anthropic` | Falls back to Gemma-only |
| P0 | `test_ai_exposure_composite.py` | `test_graceful_degradation_no_gemma` | Falls back to Karpathy |
| P0 | `test_ai_exposure_composite.py` | `test_all_signals_null` | Returns (None, "no_data") |
| P1 | `test_ai_exposure_composite.py` | `test_velocity_computation` | Velocity + labels correct |
| P1 | `test_ai_exposure_composite.py` | `test_composite_clamping` | Clamps to 0–10 |
| P1 | `test_anthropic_ingest.py` | `test_raw_schema_validation` | JSON validates |
| P1 | `test_anthropic_ingest.py` | `test_soc_join_coverage` | >80% join to pipeline SOCs |
| P2 | `test_ai_exposure_composite.py` | `test_provenance_tracking` | Signals + method tracked |
| P2 | `test_boss_fight.py` | `test_fight_ai_prompt_includes_observed` | Prompt has new fields |

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING

### @fp-data-reviewer Review
**Status:** PENDING

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

---

## §10 Discussion

```
[YYYY-MM-DD HH:MM] @source-agent → @target-agent
Message content.
```

---

## §11 Final Notes

**Human Review:** PENDING

### Dependency Chain

```
raw-ingest-karpathy-ai-exposure (COMPLETE)
  ↓
gemma-ai-exposure-rescore (S1 — must run first)
  ↓
three-signal-ai-exposure-composite (THIS SPEC — S4)
```

If S1 hasn't run, this spec still works — degrades to two-signal (Karpathy + Anthropic) or Karpathy-only.

### Weight Tuning

40/35/25 weights are a hypothesis. A/B comparison validates:
1. Reasonable ordering? (Plumbers < teachers < analysts < programmers)
2. Any surprising composites?
3. Does velocity add signal or noise?

Weight tuning is a 30-minute adjustment if needed.

### Data Freshness

Anthropic publishes ~quarterly. Manual extraction means re-running requires human to extract new numbers. For hackathon, single snapshot is sufficient.

### Kaggle Writeup Section

> **Three-Signal AI Exposure Composite.** Most AI career tools use a single exposure score — typically an LLM reading job descriptions and guessing. FutureProof uses three independent signals. First, Gemma 4 evaluates AI exposure at the task level using O*NET work activity data from our governed pipeline, producing a theoretical ceiling. Second, we incorporate Anthropic's Economic Index — empirical data measuring which occupation tasks are actually being performed by AI today, based on millions of real conversations. Third, we compute a velocity metric: the ratio of observed adoption to theoretical capability, revealing how fast AI is arriving in each career. A computer programmer scores 9/10 theoretical and 74.5% observed — AI is already here. A construction manager scores 5/10 theoretical but only 8% observed — the wave is building slowly. Students see all three dimensions, not just a single number, because career planning requires understanding not just *if* AI will arrive but *when*.

---

*— End of Spec —*
