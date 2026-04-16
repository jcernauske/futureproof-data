# Spec: three-signal-ai-exposure-composite

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
```

---

## Status: DRAFT

## Metadata

| Field | Value |
|-------|-------|
| Created | 2026-04-14 |
| Author | Jeff + Claude Desktop |
| Spec Version | 1.0 |
| Last Updated | 2026-04-14 |
| Blocked By | `gemma-ai-exposure-rescore` (Gemma task-level scoring must run first) |
| Related Specs | `raw-ingest-karpathy-ai-exposure`, `gemma-ai-exposure-rescore`, `gold-futureproof-engine`, `gold-futureproof-engine-addendum-cip-fix` |
| Priority | Bonus — ships if time allows after core frontend + `gemma-ai-exposure-rescore` |

---

## §1 Feature Description

### Overview

Replace the single-source RES stat (Karpathy 0–10 score) with a three-signal composite that blends theoretical AI capability, empirically observed AI adoption, and the velocity at which the gap is closing. The three signals are: (1) Gemma task-level scores from `gemma-ai-exposure-rescore`, (2) Anthropic Economic Index observed exposure percentages from real Claude usage data, and (3) a computed velocity metric derived from the gap between theoretical and observed exposure.

### Problem Statement

RES currently depends on Karpathy's scores — LLM-generated estimates from a self-described "saturday morning 2 hour vibe coded project." The `gemma-ai-exposure-rescore` spec improves on this by scoring at the task level with Gemma. But even Gemma's scores remain *theoretical* — they estimate what AI *could* do, not what it *is* doing.

Anthropic published empirical data (March 2026) measuring which occupation tasks are actually being performed by AI, based on millions of real Claude conversations. This is the only public dataset that measures observed AI adoption by occupation. Computer programmers lead at 74.5% observed exposure; 30% of occupations have near-zero exposure. The gap between theoretical capability and observed adoption is itself a signal — it indicates how quickly AI is actually arriving in that occupation.

A three-signal composite produces a RES stat that answers three questions simultaneously:
1. **How much of this job *could* AI do?** (Gemma task-level scores — theoretical ceiling)
2. **How much of this job *is* AI doing right now?** (Anthropic observed exposure — current reality)
3. **How fast is AI closing the gap?** (Velocity — the adoption rate as a fraction of theoretical capability)

This is strictly better than any single signal for a career guidance product. A student choosing between two careers that both score 7/10 on theoretical exposure could see very different risk profiles: one at 70% observed (AI is already here) vs. one at 15% observed (theoretical risk, slow adoption). That distinction matters for career planning.

### Hackathon Writeup Value

This is a standout Technical Depth story:

> "We didn't just use someone else's AI scores. We built a three-signal composite: Gemma evaluates which tasks AI *could* automate from O*NET data, Anthropic's Economic Index measures which tasks AI *is* automating from real-world usage, and the ratio between them reveals how fast AI is arriving in each career. Students see theoretical risk, current reality, and velocity — not just a single number."

The "observed vs. theoretical" distinction also feeds the boss fight narrative for Fight AI. A career losing to AI *right now* hits different than one with high theoretical risk but low adoption.

### Success Criteria

- [ ] Anthropic observed exposure data ingested into `raw.anthropic_observed_exposure`
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
| 1 | Three-signal weighted composite rather than replacing Karpathy with Anthropic alone | Anthropic measures current adoption (snapshot), Gemma measures theoretical ceiling (potential), velocity captures the trajectory. All three are independently useful and non-redundant. | Option 2 (replace Karpathy with Anthropic) — simpler but loses theoretical vs. observed distinction. Option 1 (simple blend) — loses the velocity dimension. |
| 2 | Velocity = observed / theoretical, not observed delta over time | Anthropic has only published a few data points over time; cross-sectional ratio is more robust than a noisy time-series delta. Ratio naturally captures "how much of the theoretical ceiling has been realized." | Time-series delta from successive Anthropic reports — insufficient data points, would require re-ingesting each quarterly update. |
| 3 | Composite formula weights: 40% Gemma theoretical, 35% Anthropic observed, 25% velocity | Theoretical gets highest weight because it represents the *eventual* risk, which matters most for career planning (students are planning 10+ years out). Observed gets strong weight because it's empirical. Velocity is a modifier, not a primary signal. | Equal weights — doesn't reflect the planning horizon difference. Majority observed — biases toward current state, bad for career planning. |
| 4 | Graceful degradation when signals are missing | Not all SOC codes will have all three signals. If Anthropic data is missing: fall back to Gemma-only. If Gemma is missing: fall back to Karpathy. If all are missing: RES = null (existing behavior). Provenance field tracks which signals contributed. | Require all three — would reduce coverage. Impute missing values — introduces synthetic data without clear basis. |
| 5 | Anthropic data ingested as a manual Bronze source (CSV/JSON extracted from research publication), not scraped live | Anthropic publishes this in research reports, not as a downloadable dataset or API. Manual extraction is appropriate for a one-time ingest. | Build a scraper — fragile, unnecessary for a single data snapshot. Wait for API — doesn't exist. |
| 6 | Velocity surfaces in Fight AI narrative, not as a separate stat | Adding a sixth stat would break the pentagon. Velocity is most useful as narrative context ("AI is arriving fast in this career" vs. "AI could do this work but hasn't yet"). | New stat — breaks pentagon, adds UI complexity. Ignore velocity — wastes a valuable signal. |

### Constraints

- Anthropic's observed exposure data is published at the SOC major group level (22 groups) AND at the individual occupation level (top occupations listed). The per-occupation coverage may not be complete for all 832 SOC codes in our pipeline. Fallback behavior is critical.
- Composite formula weights are initial estimates. The A/B comparison deliverable will validate whether the weights produce reasonable orderings. Weights may need tuning.
- This spec depends on `gemma-ai-exposure-rescore` completing first. Without Gemma task-level scores, signal 1 falls back to Karpathy and the composite degrades to a two-signal blend.

---

## §3 UI/UX Design

> Backend-only spec. No new UI screens.

**Downstream frontend impact:** The composite changes the *value* of `stat_res` and `boss_ai_score` in existing API responses but does NOT change the API shape. The pentagon renders the same 1–10 integer. The receipts endpoint gains additional provenance fields (which signals contributed, individual signal values).

**Fight AI boss narrative enhancement:** The Gemma prompt for boss fight narratives (Surface #5 in PRD v8) gains additional context fields:

```
Observed AI Exposure: {observed_pct}% of tasks already performed by AI
Theoretical AI Exposure: {theoretical_score}/10
Velocity: {velocity_label} (AI is arriving {velocity_narrative} in this field)
```

This lets Gemma write narratives like: "Financial analysts face serious AI pressure — not just in theory. AI is already handling 65% of tasks in this field, and adoption is accelerating." vs. "Construction managers have high theoretical exposure on paper, but only 8% of tasks are currently AI-assisted. The wave hasn't arrived yet — but it's on the horizon."

---

## §4 Technical Specification

### Architecture Overview

This spec adds one new data source (Anthropic observed exposure), extends the existing `consumable.ai_exposure` Gold table, and updates the composite formula that feeds `stat_res` and `boss_ai_score` in the engine tables. It sits on top of `gemma-ai-exposure-rescore` — that spec produces signal 1, this spec produces the composite.

```
Signal 1: Gemma task-level scores (gemma-ai-exposure-rescore spec)
  ↓ already in consumable.ai_exposure as exposure_score + task_breakdown
Signal 2: Anthropic observed exposure (NEW — this spec)
  ↓ raw.anthropic_observed_exposure → base.anthropic_observed_exposure
Signal 3: Velocity (COMPUTED — this spec)
  ↓ = signal 2 / signal 1 (observed / theoretical)

All three → composite formula → stat_res (1–10) + boss_ai_score (1–10)
  ↓ re-promote consumable.program_career_paths + consumable.career_branches
```

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `data/raw/anthropic_cache/observed_exposure.json` | Create | Manually extracted Anthropic data (see Source Data section) |
| `src/raw/anthropic_observed_exposure_ingestor.py` | Create | Bronze ingestor for Anthropic data |
| `src/silver/anthropic_observed_exposure_promoter.py` | Create | Silver promoter — SOC normalization + join validation |
| `src/gold/ai_exposure_composite_promoter.py` | Create | Gold promoter — three-signal composite formula |
| `src/gold/futureproof_engine_promoter.py` | Modify | Update re-promote to use composite `stat_res` and `boss_ai_score` |
| `backend/services/stats.py` | Modify | Update receipts to include signal breakdown |
| `backend/services/boss_fight.py` | Modify | Pass observed/theoretical/velocity to Fight AI narrative prompt |
| `dq/rules/anthropic_observed_exposure_rules.py` | Create | DQ rules for Anthropic Bronze + Silver |
| `dq/rules/ai_exposure_composite_rules.py` | Create | DQ rules for composite Gold table |
| `data_contracts/ai_exposure_composite.yaml` | Create | Data contract for updated `consumable.ai_exposure` |

### Source Data: Anthropic Observed Exposure

**Source:** Anthropic's "Labor Market Impacts of AI" (March 2026) and "Anthropic Economic Index" reports.

**Publication URLs:**
- https://www.anthropic.com/research/labor-market-impacts
- https://www.anthropic.com/research/anthropic-economic-index-january-2026-report

**What to extract:**

1. **Per-occupation observed exposure %** — Top occupations listed in the research with specific percentages (e.g., Computer Programmers 74.5%, Customer Service Reps 70.1%, Data Entry Keyers 67.1%, Medical Record Specialists 66.7%, Market Research Analysts 64.8%, Sales Reps 62.8%). The research names ~30-50 individual occupations with specific percentages.

2. **Per-SOC-major-group observed exposure %** — 22 occupation groups with aggregate percentages (e.g., Computer & Math 35.8%, Office & Admin 34.3%, Business & Finance 28.4%, Sales 26.9%, Legal 20.4%, Arts & Media 19.2%, Education & Library 18.2%).

3. **Per-SOC-major-group theoretical capability %** — 22 occupation groups with theoretical AI coverage (e.g., Computer & Math 94.3%, Business & Finance 94.3%, Management 91.3%, Office & Admin 90%, Legal 89%, Architecture & Engineering 84.8%, Arts & Media 83.7%).

**Extraction approach:** Manual extraction from the published figures and tables into `data/raw/anthropic_cache/observed_exposure.json`. This is a one-time manual step. The data is published in research reports (with figures and tables), not as a downloadable CSV.

**JSON structure:**

```json
{
  "source": "Anthropic Labor Market Impacts of AI, March 2026",
  "source_url": "https://www.anthropic.com/research/labor-market-impacts",
  "extraction_date": "2026-04-XX",
  "extraction_notes": "Manually extracted from published figures and tables. Values rounded to nearest 0.1%.",
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

- Occupations with a specific per-occupation percentage: use that value directly.
- Occupations without a specific value but within a known major group: use the major group percentage as a fallback, flagged as `resolution = "major_group_fallback"`.
- Occupations with neither: `observed_exposure_pct = null`, composite falls back to Gemma-only or Karpathy-only.

### Data Model Changes

#### Raw Table: `raw.anthropic_observed_exposure`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| occupation_title | string | yes | As published by Anthropic |
| soc_code | string | no | SOC code — may need manual resolution for some occupations |
| soc_major_group | string | no | SOC major group (XX-0000) |
| observed_exposure_pct | double | yes | 0–100 percentage of tasks observed being performed by AI |
| theoretical_capability_pct | double | no | 0–100 theoretical AI coverage (available at major group level) |
| resolution | string | yes | "direct" (per-occupation) or "major_group" (group-level fallback) |
| source_detail | string | yes | Which figure/table in the publication |

**Grain:** One row per occupation or major group entry.
**Expected rows:** ~50-80 (individual occupations) + 22 (major groups) = ~70-100 rows.

#### Silver Table: `base.anthropic_observed_exposure`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| soc_code | string | yes | Normalized to XX-XXXX format. Must match pipeline SOC codes. |
| occupation_title | string | yes | Canonical title from our `consumable.occupation_profiles` |
| observed_exposure_pct | double | yes | 0–100 |
| theoretical_capability_pct | double | no | 0–100 (may be null for occupations where only observed is published) |
| resolution | string | yes | "direct", "major_group_fallback", or "title_fuzzy_match" |
| match_confidence | string | yes | "exact", "high", "moderate" — SOC join confidence |

**Join validation:** Every row must join to an existing SOC code in `consumable.occupation_profiles` or `consumable.onet_work_profiles`. Rows that don't match are flagged and logged but not discarded — they may indicate occupations we should add.

#### Updated Gold Table: `consumable.ai_exposure`

Extends the schema from `gemma-ai-exposure-rescore`. All existing fields are preserved. New fields added:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| observed_exposure_pct | double | no | From Anthropic. Null if no Anthropic data for this SOC. |
| theoretical_capability_pct | double | no | From Anthropic major group data. Null if unavailable. |
| velocity_ratio | double | no | `observed_exposure_pct / (theoretical_score_normalized * 10)`. Range 0.0–1.0. Null if either input is null. |
| velocity_label | string | no | "rapid" (>0.5), "moderate" (0.25–0.5), "slow" (0.1–0.25), "nascent" (<0.1). Null if velocity_ratio is null. |
| composite_score | double | no | Raw weighted composite before rounding. Retained for receipts/provenance. |
| composite_signals | string | no | JSON: which signals contributed. e.g., `{"gemma": true, "anthropic": true, "velocity": true}` |
| composite_method | string | no | "three_signal", "two_signal_no_anthropic", "gemma_only", "karpathy_only" — provenance |

**Existing fields retained from `gemma-ai-exposure-rescore`:**
- `exposure_score` — now the composite score (1–10 integer), not the raw Gemma score
- `stat_res` — derived from composite `exposure_score` (inverted: high exposure = low resilience)
- `boss_ai_score` — derived from composite `exposure_score`
- `rationale` — Gemma's task-level rationale (unchanged)
- `task_breakdown_automatable` — Gemma's automatable tasks (unchanged)
- `task_breakdown_human` — Gemma's human-essential tasks (unchanged)
- `scoring_model` — updated to "composite_v1" (was "gemma-4")
- `gemma_exposure_score` — **NEW rename**: the raw Gemma 0–10 score, preserved separately from the composite

### Composite Formula

```python
def compute_composite_res(
    gemma_score: float | None,        # 0-10, from gemma-ai-exposure-rescore
    karpathy_score: float | None,     # 0-10, from raw-ingest-karpathy-ai-exposure
    observed_pct: float | None,       # 0-100, from Anthropic
    theoretical_pct: float | None,    # 0-100, from Anthropic (major group level)
) -> tuple[int | None, str]:
    """
    Returns (composite_exposure_score 0-10, method_used).
    
    Higher composite = higher AI exposure = LOWER resilience.
    stat_res = 10 - composite_exposure_score (inverted for pentagon).
    """
    
    # Determine theoretical signal (prefer Gemma, fall back to Karpathy)
    theoretical = gemma_score if gemma_score is not None else karpathy_score
    if theoretical is None:
        return (None, "no_data")
    
    # Normalize observed to 0-10 scale for blending
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
    
    # Two-signal fallback (no Anthropic data)
    elif observed_normalized is None:
        composite = theoretical  # Gemma or Karpathy score as-is
        method = "gemma_only" if gemma_score is not None else "karpathy_only"
    
    # Edge case: observed but no velocity (shouldn't happen, but defensive)
    else:
        composite = (
            0.55 * theoretical +
            0.45 * observed_normalized
        )
        method = "two_signal_no_velocity"
    
    # Clamp and round
    composite_clamped = max(0, min(10, composite))
    return (round(composite_clamped), method)
```

**Key properties of this formula:**

- A job with high theoretical AND high observed scores concentrates at the high end (very exposed). A job with high theoretical but low observed gets moderated downward — the risk is real but hasn't materialized.
- Velocity acts as an amplifier: if observed is catching up to theoretical quickly (ratio > 0.5), the composite skews higher than either signal alone. If observed is far below theoretical (ratio < 0.1), the composite pulls toward the theoretical floor.
- Graceful degradation: missing Anthropic data doesn't break the score, it just reduces to the prior single-signal behavior.

**Example computations:**

| Occupation | Gemma | Observed % | Velocity | Composite | Method | Interpretation |
|-----------|-------|-----------|----------|-----------|--------|---------------|
| Computer Programmer | 9 | 74.5% | 0.83 | 9 | three_signal | High on all signals. AI is here. |
| Financial Analyst | 8 | 64.8% | 0.81 | 8 | three_signal | High theoretical, high observed, fast velocity. |
| Construction Manager | 5 | 8.0% | 0.16 | 4 | three_signal | Moderate theoretical, low observed. Wave hasn't hit. |
| Plumber | 2 | 1.0% | 0.05 | 2 | three_signal | Low across the board. Physical work. |
| Niche occupation X | 6 | null | null | 6 | gemma_only | No Anthropic data. Falls back to Gemma. |

### Fight AI Boss Narrative Enhancement

Update the Gemma prompt template in `backend/services/boss_fight.py` for the Fight AI boss:

```python
FIGHT_AI_PROMPT_ADDITION = """
## AI Exposure Context (use this for your narrative)
- Theoretical AI capability: {theoretical_score}/10 — what AI *could* do in this career
- Observed AI adoption: {observed_pct}% of tasks — what AI *is* doing right now
- Adoption velocity: {velocity_label} — how fast AI is arriving
- Composite AI exposure: {composite_score}/10

If observed adoption is high (>40%): emphasize that AI is already reshaping this work today.
If observed is low but theoretical is high: frame as "the wave is building but hasn't hit yet."
If velocity is rapid: warn that the gap is closing fast.
If velocity is slow/nascent: note the runway — there's time to prepare.
"""
```

### Receipts Enhancement

Update `backend/services/stats.py` receipts to include signal breakdown:

```python
class ResStatReceipt(BaseModel):
    stat_res: int
    composite_exposure_score: int
    composite_method: str  # "three_signal", "gemma_only", etc.
    gemma_theoretical_score: int | None
    karpathy_score: int | None
    anthropic_observed_pct: float | None
    velocity_ratio: float | None
    velocity_label: str | None
    task_breakdown_automatable: list[str] | None
    task_breakdown_human: list[str] | None
    source_note: str  # "Theoretical: Gemma 4 task-level scoring. Observed: Anthropic Economic Index (March 2026). Velocity: observed/theoretical ratio."
```

### Service Changes

No new service modules. Changes to existing services:

- `stats.py` — receipts model updated (see above)
- `boss_fight.py` — Fight AI prompt template updated (see above)
- No changes to API shape — `stat_res` and `boss_ai_score` are already integers in the response

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `tests/test_stats.py` | `test_pentagon_computation` | Medium | `stat_res` values will change for occupations with Anthropic data |
| `tests/test_boss_fight.py` | `test_fight_ai_score` | Medium | `boss_ai_score` values will change |
| `tests/test_gold_engine.py` | `test_program_career_paths_schema` | Low | New fields added to `consumable.ai_exposure` but PCP schema unchanged |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| `test_pentagon_computation` | Update expected `stat_res` values for test fixtures | Composite formula produces different values than Gemma-only |
| `test_fight_ai_score` | Update expected `boss_ai_score` values for test fixtures | Same reason |

#### Confirmed Safe

All tests that don't reference `stat_res` or `boss_ai_score` should be unaffected. The API shape does not change.

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `tests/test_ai_exposure_composite.py` | `test_three_signal_composite` | Formula produces expected scores for known inputs (programmer, plumber, analyst) |
| P0 | `tests/test_ai_exposure_composite.py` | `test_graceful_degradation_no_anthropic` | Missing Anthropic data falls back to Gemma-only score |
| P0 | `tests/test_ai_exposure_composite.py` | `test_graceful_degradation_no_gemma` | Missing Gemma data falls back to Karpathy score |
| P0 | `tests/test_ai_exposure_composite.py` | `test_all_signals_null` | Returns (None, "no_data") when all signals are missing |
| P1 | `tests/test_ai_exposure_composite.py` | `test_velocity_computation` | Velocity ratio computed correctly, labels assigned at correct thresholds |
| P1 | `tests/test_ai_exposure_composite.py` | `test_composite_clamping` | Scores clamp to 0–10 range for edge cases |
| P1 | `tests/test_anthropic_ingest.py` | `test_raw_schema_validation` | Raw Anthropic JSON validates against expected schema |
| P1 | `tests/test_anthropic_ingest.py` | `test_soc_join_coverage` | Validates that >80% of Anthropic occupations join to pipeline SOC codes |
| P2 | `tests/test_ai_exposure_composite.py` | `test_provenance_tracking` | `composite_signals` and `composite_method` populated correctly |
| P2 | `tests/test_boss_fight.py` | `test_fight_ai_prompt_includes_observed` | Fight AI prompt template includes observed/theoretical/velocity fields when available |

#### Test Data Requirements

- Fixture file: `tests/fixtures/anthropic_observed_exposure_sample.json` — 10 representative occupations with known Anthropic percentages
- Fixture file: `tests/fixtures/composite_expected_outputs.json` — pre-computed expected composite scores for the 10 fixtures, manually verified

---

## §5 Architecture Review

### @fp-architect Review
**Status:** PENDING
#### Findings
[Filled in by @fp-architect]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
- [ ] REJECTED

### @fp-data-reviewer Review
**Status:** PENDING
#### Findings
[Filled in by @fp-data-reviewer — composite formula validation, coverage analysis, fallback correctness]
#### Verdict
- [ ] APPROVED
- [ ] CHANGES REQUESTED
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

### Dependency Chain

This spec sits at the end of a clear dependency chain:

```
raw-ingest-karpathy-ai-exposure (COMPLETE)
  ↓
gemma-ai-exposure-rescore (BONUS — must run first)
  ↓
three-signal-ai-exposure-composite (THIS SPEC — bonus on top of bonus)
```

If `gemma-ai-exposure-rescore` hasn't run, this spec still works — it just degrades to a two-signal composite (Karpathy + Anthropic) or Karpathy-only. The composite formula handles all fallback combinations.

### Weight Tuning

The 40/35/25 weights are a starting hypothesis. The A/B comparison deliverable should validate them by checking:

1. Do the composite scores produce a *reasonable* ordering? (Plumbers < teachers < analysts < programmers)
2. Do any occupations produce surprising composites that indicate weight problems?
3. Does the velocity signal add signal or just noise?

If the A/B shows issues, weight tuning is a 30-minute adjustment — the formula is a single function.

### Data Freshness

Anthropic publishes updated Economic Index data approximately quarterly. The manual extraction approach means re-running this ingest requires a human to extract updated numbers from the latest report. For the hackathon, a single snapshot is sufficient. Post-hackathon, consider building a structured data request to Anthropic or monitoring their research page for machine-readable releases.

### Kaggle Writeup Section

Suggested paragraph for the Technical Depth section:

> **Three-Signal AI Exposure Composite.** Most AI career tools use a single exposure score — typically an LLM reading job descriptions and guessing. FutureProof uses three independent signals. First, Gemma 4 evaluates AI exposure at the task level using O*NET work activity data from our governed pipeline, producing a theoretical ceiling. Second, we incorporate Anthropic's Economic Index — empirical data measuring which occupation tasks are actually being performed by AI today, based on millions of real conversations. Third, we compute a velocity metric: the ratio of observed adoption to theoretical capability, revealing how fast AI is arriving in each career. A computer programmer scores 9/10 theoretical and 74.5% observed — AI is already here. A construction manager scores 5/10 theoretical but only 8% observed — the wave is building slowly. Students see all three dimensions, not just a single number, because career planning requires understanding not just *if* AI will arrive but *when*.

---

*— End of Spec —*
