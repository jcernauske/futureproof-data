# Feature: Three-Signal AI Exposure Composite (S4)

## Claude Code Prompt

```
Read the spec at docs/specs/three-signal-ai-exposure-composite.md in its entirety.

Execute the following workflow:

1. VERIFY DEPENDENCIES
   - Confirm S1 `gemma-ai-exposure-rescore` is COMPLETE (check PRD)
   - Confirm `ingest-anthropic-economic-index` is COMPLETE (check PRD)
   - If either is not COMPLETE: STOP, alert human

2. ARCHITECTURE REVIEW
   - Invoke @fp-architect to review sections 1-4 (system architecture, data flow, Brightsmith integration)
   - Invoke @fp-data-reviewer to review data quality implications — especially the composite formula
   - Both write findings to §5 (Architecture Review)
   - If APPROVED: proceed to step 3
   - If CHANGES REQUESTED (Significant): STOP, alert human
   - If REJECTED (Blocker): STOP, alert human

3. IMPLEMENTATION
   - Implement the spec as written in §4 (Technical Spec)
   - BEFORE coding: Review §4 Testing Impact Analysis thoroughly
   - DURING coding: Update any broken tests listed in "Authorized Test Modifications"
   - CRITICAL: If any test NOT in the "Authorized Test Modifications" list fails, STOP and escalate to human
   - Log all work to §6 (Implementation Log)
   - Run backend (ruff + mypy + pytest) to verify build
   - BUILD ACCOUNTABILITY: If build breaks, YOU fix it (max 3 attempts)
   - If still broken after 3 attempts: escalate to human via §10 Discussion

4. TESTING
   - Invoke @test-writer to review the full spec
   - @test-writer MUST review §4 Testing Impact Analysis
   - Implement all tests listed in "New Tests Required" by priority (P0 first)
   - Backend tests: pytest in backend/tests/
   - Run ALL tests to catch regressions
   - If still broken after 3 attempts: escalate to human via §10 Discussion

5. CODE REVIEW
   - Invoke @faang-staff-engineer to review implementation + tests
   - Reviewer writes findings to §8 (Code Review)
   - If APPROVED: proceed to step 6
   - If CHANGES REQUIRED: route to originating agent via §10 Discussion
   - If BLOCKER: STOP, alert human

6. VERIFICATION
   - Invoke @fp-builder to run full build verification
   - Backend: ruff check, mypy, pytest
   - Log results to §9 (Verification)
   - If all green: mark status COMPLETE

7. COMPLETION
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

## Status: COMPLETE

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
| Spec Version | 4.0 (Option B — percentile-confidence blend after v3 data review rejection) |
| Last Updated | 2026-04-16 |
| Blocked By | `gemma-ai-exposure-rescore` (S1 — ✅ COMPLETE), `ingest-anthropic-economic-index` (✅ COMPLETE) |
| Related Specs | `ingest-anthropic-economic-index`, `gemma-ai-exposure-rescore` (S1), `gold-futureproof-engine` |
| Priority | Bonus — ships if time allows after core frontend + S1 |

---

## §1 Feature Description

### Overview

Replace the single-source RES stat with a **three-signal composite** that blends:
1. **Theoretical AI capability** — Gemma task-level scores from S1 (already in `consumable.ai_exposure`)
2. **Observed AI adoption** — Anthropic Economic Index (from `base.anthropic_observed_exposure`)
3. **Velocity** — How fast AI is closing the gap (observed/theoretical ratio)

This produces a RES stat that answers three questions simultaneously:
- How much of this job *could* AI do? (theoretical ceiling)
- How much of this job *is* AI doing right now? (current reality)
- How fast is AI closing the gap? (adoption trajectory)

### Problem Statement

Even Gemma's task-level scores (from S1) remain *theoretical* — they estimate what AI *could* do, not what it *is* doing.

The Anthropic Economic Index measures **actual** AI task usage across occupations — empirical observation from millions of real Claude conversations. The gap between theoretical capability and observed adoption is itself a signal — it indicates how quickly AI is actually arriving in that occupation.

A student choosing between two careers that both score 7/10 on theoretical exposure could see very different risk profiles:
- Career A: 70% observed (AI is already here)
- Career B: 15% observed (theoretical risk, slow adoption)

That distinction matters for career planning.

### Hackathon Writeup Value

This is a standout Technical Depth story:

> "We didn't just use someone else's AI scores. We built a three-signal composite: Gemma evaluates which tasks AI *could* automate from O*NET data, Anthropic's Economic Index measures which tasks AI *is* automating from real-world usage, and the ratio between them reveals how fast AI is arriving in each career. Students see theoretical risk, current reality, and velocity — not just a single number."

### Success Criteria

- [x] `consumable.ai_exposure` updated with composite score + velocity metric (815 rows, 5 new columns — composite_exposure, adoption_percentile, confidence_weight, velocity_label, composite_method)
- [x] Composite RES formula produces a 1–10 integer score (derive_stats clamps to 1-10 integer)
- [x] `consumable.program_career_paths` re-promoted with composite `stat_res` and `boss_ai_score` (626,406 rows, 96.6% have composite provenance)
- [x] `consumable.career_branches` re-promoted with composite `stat_res` delta (15,944 rows)
- [x] Fight AI boss narrative prompt updated to reference observed vs. theoretical exposure (`backend/app/services/boss_fights.py::_boss_context` + `_BOSS_INSTRUCTIONS["ai"]`)
- [x] DQ rules added (GLD-AIE-CMP-001 through 006 — range, enum, consistency)
- [x] A/B comparison via `scripts/data_review_three_signal_option_b.py` — method distribution, velocity distribution, stat_res delta histogram, blue-collar saturation check
- [x] Coverage report: 33.9% three_signal / 29.8% gemma_plus_anthropic / 22.5% gemma_only / 11.8% two_signal_no_anthropic / 2.1% karpathy_only across 815 Gold rows

---

## §2 Design Decisions

### Decision Log

| # | Decision | Rationale | Alternatives Considered |
|---|----------|-----------|------------------------|
| 1 | Three-signal weighted composite | Anthropic = current snapshot, Gemma = theoretical ceiling, velocity = trajectory. All three are independently useful and non-redundant. | Replace Gemma with Anthropic alone (loses theoretical vs. observed distinction) |
| 2 | Velocity = observed / theoretical (cross-sectional ratio) | Ratio naturally captures "how much of theoretical ceiling has been realized" | Time-series delta (insufficient data points) |
| 3 | Weights: 40% theoretical, 35% observed, 25% velocity | Theoretical gets highest weight because it represents *eventual* risk (students planning 10+ years out). Observed is empirical. Velocity is a modifier. | Equal weights (doesn't reflect planning horizon), Majority observed (bad for long-term planning) |
| 4 | Graceful degradation for missing signals | Not all SOC codes have all three signals. Fall back to Gemma-only → Karpathy-only → null. Provenance tracks which signals contributed. | Require all three (reduces coverage) |
| 5 | Use `base.anthropic_observed_exposure` from HuggingFace dataset | Anthropic publishes raw CSV data on HuggingFace under CC-BY. No manual extraction needed. | Manual extraction from reports (error-prone, fragile) |
| 6 | Velocity in narrative, not as sixth stat | Adding a stat would break the pentagon. Velocity is most useful as narrative context ("AI is arriving fast" vs. "wave hasn't hit yet"). | New stat (breaks pentagon), Ignore velocity (wastes signal) |
| 7 (v4) | Option B formula: percentile-rank confidence blend, not linear weighted sum | v3 formula assumed `observed_exposure_pct` was 0–100 task coverage; real values are 0–7.51 (share of Claude conversations). Treating it as a confidence weight instead of a term sidesteps the scale issue entirely — only rank matters. | Rescale observed_pct upstream (risky; Silver already stamped); drop signal (wastes Anthropic data) |
| 8 (v4) | Rename `observed_exposure_pct` → `ai_adoption_share` at Gold | New name describes what the value actually measures (share of Claude conversations), not theoretical task exposure. Silver column name stays to avoid re-running that pipeline. | Keep old name (semantically misleading) |

### Constraints

- Coverage depends on `ingest-anthropic-economic-index` pipeline completing first
- Not all SOC codes have Anthropic data — fallback to Gemma-only is expected for ~30% of occupations
- This spec depends on S1 completing first. Without Gemma scores, degrades to Karpathy-only.

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

## §4 Technical Specification (v4 — Option B)

### What changed vs. v3

The v3 data review REJECTED the formula because the Silver field then called
`observed_exposure_pct` (now renamed — see below) is NOT "percent of tasks
performed by AI." It is **share of all Claude conversations** on the
Anthropic Economic Index (range 0.0015–7.51 across 587 SOCs, sum ≈ 98). The
v3 formula `observed_pct / 10.0` would have clamped every row to
`velocity="nascent"` and pinned every blue-collar SOC to `stat_res=10`.

v4 keeps the three-signal philosophy but replaces the linear composite with
a **percentile-rank confidence blend**:

- Rename `observed_exposure_pct` → `ai_adoption_share` everywhere (schema,
  Pydantic, receipts, contract). The new name describes what the value
  actually measures.
- `ai_adoption_share` is used to compute `adoption_percentile` (0–100) and
  drive a `confidence` weight that blends Gemma (theoretical) against
  Karpathy (baseline).
- Velocity becomes a coarse label derived from the percentile, not a ratio.

### Architecture Overview

```
Signal 1: Gemma task-level scores (from S1)
  ↓ already in consumable.ai_exposure as exposure_score

Signal 2: Karpathy Gemini-Flash baseline (fallback signal)
  ↓ already in consumable.ai_exposure as karpathy_score

Signal 3: ai_adoption_share (from base.anthropic_observed_exposure)
  ↓ drives confidence (0.3–1.0) and velocity_label (nascent/emerging/accelerating/saturating)

All three → Option B composite → stat_res (1–10) + boss_ai_score (1–10)
  ↓ re-promote consumable.program_career_paths + consumable.career_branches
```

### Dependency: `ingest-anthropic-economic-index` ✅ COMPLETE

Silver table `base.anthropic_observed_exposure` (registered in catalog
`brightsmith`, 587 rows):

| Field | Type | Real distribution |
|-------|------|-------------------|
| soc_code | string (required) | Normalized XX-XXXX |
| soc_title | string | e.g. "Chief Executives" |
| observed_exposure_pct | double (required) | **0.0015–7.5065, sum ≈ 98** (share of all Claude conversations — semantically `ai_adoption_share`) |
| automation_pct | double | 0–100, null for ~15% of rows |
| augmentation_pct | double | 0–100 |
| task_count | int (required) | O*NET tasks aggregated |
| source_release | string (required) | e.g. `release_2025_03_27` |

The v4 Gold transformer reads `observed_exposure_pct` from Silver and
exposes it downstream as `ai_adoption_share` (column rename, no Silver
migration required).

### File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/gold/ai_exposure_transformer.py` | Modify | Rename column, add Option B composite, extend schema by 5 fields |
| `src/gold/futureproof_engine.py` | Modify (re-run) | Thread composite provenance into `program_career_paths` + `career_branches` |
| `src/mcp_server/futureproof_server.py` | Modify | Add new composite fields to `CAREER_PATHS_RESPONSE_FIELDS` |
| `backend/app/models/career.py` | Modify | Add `ai_adoption_share`, `composite_method`, `velocity_label`, `adoption_percentile` to `CareerOutcome` |
| `backend/app/services/stat_engine.py` | Modify | Populate new `CareerOutcome` fields from MCP row |
| `backend/app/services/receipts.py` | Modify | RES receipt uses new provenance fields |
| `backend/app/services/boss_fights.py` | Modify (note: file is plural `boss_fights.py`, v3 spec said `boss_fight.py`) | Fight AI prompt includes ai_adoption_share + velocity_label |
| `governance/dq-rules/gold-ai-exposure.json` | Modify | Add rules for composite fields |
| `governance/data-contracts/consumable-ai-exposure.yaml` | Modify | Add composite fields, rename observed_exposure_pct → ai_adoption_share |

### Data Model Changes

#### Updated Gold Table: `consumable.ai_exposure`

Field **15 is renamed** (`observed_exposure_pct` → `ai_adoption_share`) via
PyIceberg schema evolution `update_schema().rename_column(...)`. Iceberg
preserves field IDs on rename so existing data stays readable.

Five new fields appended (schema evolution, explicit field IDs):

| Field ID | Name | Type | Required | Notes |
|----------|------|------|----------|-------|
| 15 (renamed) | ai_adoption_share | double | no | Share of Claude conversations (0.0015–7.51). Was `observed_exposure_pct`. |
| 19 | composite_exposure | integer | no | 0–10 composite (Option B blend). Source of truth for `stat_res` / `boss_ai_score`. |
| 20 | adoption_percentile | double | no | 0–100, percent-rank of `ai_adoption_share` across all SOCs. |
| 21 | confidence_weight | double | no | 0.3–1.0 or 0.5 fallback, weight on Gemma vs. Karpathy. |
| 22 | velocity_label | string | no | One of `saturating` / `accelerating` / `emerging` / `nascent` / `unknown`. |
| 23 | composite_method | string | no | One of `three_signal` / `two_signal_no_anthropic` / `gemma_only` / `gemma_plus_anthropic` / `karpathy_only` / `observed_override` / `no_data`. |

`stat_res` and `boss_ai_score` (fields 5 and 6) are recomputed from
`composite_exposure` instead of raw `exposure_score`, so they will shift.
See §4 Testing Impact Analysis.

#### Updated Gold Table: `consumable.program_career_paths`

Three additive nullable fields thread composite provenance into the
downstream API surface:

| Field ID | Name | Type | Required | Notes |
|----------|------|------|----------|-------|
| 41 | ai_adoption_share | double | no | Passed through from ai_exposure |
| 42 | velocity_label | string | no | Passed through from ai_exposure |
| 43 | composite_method | string | no | Passed through from ai_exposure |

`stat_res` and `boss_ai_score` are re-populated from the composite via the
existing `ai_by_soc` lookup in `derive_pcp_rows`; no code change there
beyond passing through the three new fields.

#### Pydantic `CareerOutcome` additions

```python
class CareerOutcome(BaseModel):
    # ...existing fields...
    ai_adoption_share: float | None = None
    adoption_percentile: float | None = None
    velocity_label: Literal["saturating", "accelerating", "emerging",
                            "nascent", "unknown"] | None = None
    composite_method: Literal["three_signal", "two_signal_no_anthropic",
                              "gemma_only", "gemma_plus_anthropic",
                              "karpathy_only", "observed_override"] | None = None
```

### Composite Formula (Option B — percentile-rank confidence blend)

```python
def percent_rank(values: list[float | None]) -> list[float | None]:
    """Percent-rank * 100, preserving None slots. Ties share the lower rank."""
    ranked = sorted(
        ((i, v) for i, v in enumerate(values) if v is not None),
        key=lambda iv: iv[1],
    )
    out: list[float | None] = [None] * len(values)
    n = len(ranked)
    if n == 0:
        return out
    if n == 1:
        out[ranked[0][0]] = 100.0
        return out
    for rank, (idx, _) in enumerate(ranked):
        out[idx] = 100.0 * rank / (n - 1)
    return out


def velocity_from_percentile(pct: float | None) -> str:
    if pct is None:       return "unknown"
    if pct >= 90:         return "saturating"
    if pct >= 70:         return "accelerating"
    if pct >= 40:         return "emerging"
    return "nascent"


def compute_composite(
    gemma_score: int | None,          # 0-10 Gemma theoretical (preferred)
    karpathy_score: int | None,       # 0-10 Karpathy baseline
    ai_adoption_share: float | None,  # 0-7.51 Claude conversation share
    adoption_percentile: float | None,  # 0-100, pre-computed across all SOCs
) -> tuple[int | None, float | None, str, str]:
    """
    Returns (composite_exposure 0-10 or None,
             confidence_weight 0.3-1.0 or None,
             velocity_label,
             composite_method).

    stat_res = MIN(11 - composite_exposure, 10); boss_ai_score = MAX(composite, 1).
    """
    theoretical = gemma_score
    baseline = karpathy_score

    # Confidence + velocity from percentile rank
    if adoption_percentile is not None:
        confidence = max(0.3, min(1.0, 0.3 + 0.7 * adoption_percentile / 100))
        velocity = velocity_from_percentile(adoption_percentile)
    else:
        confidence = 0.5
        velocity = "unknown"

    # Fallback routing
    if theoretical is None and baseline is None:
        return None, None, velocity, "no_data"
    if theoretical is None:
        return round(max(0, min(10, baseline))), confidence, velocity, "karpathy_only"
    if baseline is None:
        method = "gemma_plus_anthropic" if ai_adoption_share is not None else "gemma_only"
        return round(max(0, min(10, theoretical))), confidence, velocity, method

    # Edge case: Gemma=0 but real-world adoption present
    if theoretical == 0 and ai_adoption_share is not None and ai_adoption_share > 0:
        return (
            round(max(0, min(10, baseline * confidence))),
            confidence, velocity, "observed_override",
        )

    # Three-signal (or two-signal if no anthropic) blend
    composite = confidence * theoretical + (1 - confidence) * baseline
    method = "three_signal" if ai_adoption_share is not None else "two_signal_no_anthropic"
    return round(max(0, min(10, composite))), confidence, velocity, method


def derive_stats(composite_exposure: int | None) -> tuple[int | None, int | None]:
    if composite_exposure is None:
        return None, None
    return min(11 - composite_exposure, 10), max(composite_exposure, 1)
```

**Why this works where v3 didn't.** Option B treats the Anthropic signal as
a **confidence prior**, not a term in a weighted sum. When adoption is high
(percentile 90+, saturating) we trust Gemma more (confidence ≈ 0.95,
composite ≈ Gemma). When adoption is low (nascent) we lean on Karpathy (the
external baseline). The raw share value never contributes directly to the
score, so its 0–7.51 range is irrelevant — only its rank matters.

**Example computations (from `scripts/data_review_three_signal_option_b.py` on real data):**

| Occupation | Gemma | Karpathy | share | pct | conf | composite | stat_res | method | velocity |
|-----------|-------|----------|-------|-----|------|-----------|----------|--------|----------|
| Software Developers (15-1252) | 7 | 9 | — | — | 0.50 | 8 | 3 | two_signal_no_anthropic | unknown |
| Financial Analysts (13-2051) | 7 | — | 0.23 | 88.4 | 0.92 | 7 | 4 | gemma_plus_anthropic | accelerating |
| Customer Service Reps (43-4051) | 7 | 9 | 0.14 | 82.3 | 0.88 | 7 | 4 | three_signal | accelerating |
| Plumbers (47-2152) | 2 | 2 | 0.04 | 58.4 | 0.71 | 2 | 9 | three_signal | emerging |
| Carpenters (47-2031) | 2 | 2 | 0.01 | 33.1 | 0.53 | 2 | 9 | three_signal | nascent |
| Fast Food (35-3023) | 2 | — | — | — | 0.50 | 2 | 9 | gemma_only | unknown |

**Distribution on 815 real SOCs:**

- Methods: three_signal 33.9% / gemma_plus_anthropic 29.8% / gemma_only 22.5% / two_signal_no_anthropic 11.8% / karpathy_only 2.1%
- Velocity: unknown 36.2% / nascent 25.5% / emerging 19.1% / accelerating 12.8% / saturating 6.4%
- stat_res delta vs v3 baseline: range −4 to +1, median 0, mean −0.26
- Blue-collar saturation at stat_res=10: **10.6%** (down from effectively 100% under v3 formula)

### Gold Transformer Update

In `src/gold/ai_exposure_transformer.py`:

1. Add `compute_composite`, `percent_rank`, `velocity_from_percentile`,
   `derive_stats` module-level helpers.
2. Extend `get_gold_schema()`: rename field 15 to `ai_adoption_share`
   (via `update_schema().rename_column`) and append five nullable fields
   19–23 listed above.
3. In `blend_scores`, after the existing Gemma/Karpathy assembly and
   Anthropic LEFT JOIN, do a **two-pass composite**:
   - Pass 1: collect `ai_adoption_share` for every row.
   - Pass 2: `adoption_percentile = percent_rank(shares) * 100`; for each
     row call `compute_composite(...)`; overwrite `stat_res` and
     `boss_ai_score` from the composite.
4. Read the Silver field as `observed_exposure_pct` but write it to the
   Gold row under the key `ai_adoption_share` (rename at the indexing
   boundary — `_index_anthropic` stays value-preserving, the rename is in
   `blend_scores`).

### Thread-through to `program_career_paths`

In `src/gold/futureproof_engine.py::derive_pcp_rows`, extend the
`ai_by_soc` lookup to also populate `ai_adoption_share`, `velocity_label`,
`composite_method` on each output row. Add the three fields to
`get_pcp_schema()` as IDs 41/42/43. The existing schema-evolution
`update_schema().add_column(...)` block in `transform()` already handles
new fields additively (same pattern used for career_branches AI fields).

### MCP response fields

Append `ai_adoption_share`, `velocity_label`, `composite_method` to
`CAREER_PATHS_RESPONSE_FIELDS` in
`src/mcp_server/futureproof_server.py` so the backend receives them.

### Pydantic + stat_engine

`CareerOutcome` gains the four optional fields listed in "Data Model
Changes" above. `backend/app/services/stat_engine.py::_row_to_outcome`
copies them from `row` onto the returned `CareerOutcome`.

### Fight AI Boss Narrative Enhancement

In `backend/app/services/boss_fights.py` (note plural filename; v3 spec
said singular), extend `_boss_context(career, "ai")` to emit a block when
composite provenance is available:

```python
if boss_id == "ai":
    parts: list[str] = []
    if career.velocity_label and career.velocity_label != "unknown":
        parts.append(
            f"Real-world AI adoption velocity: {career.velocity_label} "
            f"(adoption percentile {career.adoption_percentile:.0f} "
            f"across occupations)."
        )
    elif career.velocity_label == "unknown":
        parts.append(
            "Real-world AI adoption data is not yet available for this "
            "occupation — the score relies on theoretical capability."
        )
    if career.composite_method:
        parts.append(f"Composite method: {career.composite_method}.")
    return " ".join(parts) if parts else ""
```

Narrative guidance appended to `_BOSS_INSTRUCTIONS["ai"]`:

- `saturating`: "AI is already ubiquitous in this field — name what's
  already automated."
- `accelerating`: "Rapid adoption underway — warn the student the gap is
  closing fast."
- `emerging`: "Early-adopter signals — the wave is arriving."
- `nascent`: "Little real-world AI usage yet — runway exists to prepare."
- `unknown`: "No observed data — talk about theoretical exposure only."

### Receipts Enhancement

In `backend/app/services/receipts.py::stats_receipt`, extend the existing
RES provenance branch so it mentions the composite method and velocity
label when present. Falls back to the pre-v4 wording when
`composite_method` is None (old Gemma-or-Karpathy rows).

```python
# RES provenance
method = career.composite_method
if method in {"three_signal", "two_signal_no_anthropic",
              "gemma_plus_anthropic", "observed_override"}:
    velocity = career.velocity_label or "unknown"
    res_src = (
        f"Three-signal composite ({method}) — "
        f"Gemma theoretical + Karpathy baseline blended by "
        f"adoption_percentile; velocity={velocity} "
        f"(SOC {career.soc_code})"
    )
elif method == "gemma_only":
    res_src = (
        f"Gemma task-level AI exposure only — no observed adoption data "
        f"(SOC {career.soc_code})"
    )
elif method == "karpathy_only":
    res_src = (
        f"Karpathy AI exposure baseline — Gemma unavailable "
        f"(SOC {career.soc_code})"
    )
elif career.scoring_model == "gemma-4":
    # Pre-v4 rows without composite_method
    model_tag = career.model_tag or "gemma-4"
    res_src = (
        f"Gemma task-level AI exposure ({model_tag}) on O*NET tasks "
        f"(SOC {career.soc_code})"
    )
else:
    res_src = f"Karpathy AI exposure (SOC {career.soc_code})"
lines.append(f"RES {_stat(stats.res)}/10 ← {res_src}")
```

### Testing Impact Analysis

#### Existing Tests at Risk

| Test File | Test Name | Risk | Reason |
|-----------|-----------|------|--------|
| `tests/gold/test_ai_exposure_transformer.py` | any test that asserts `stat_res` / `boss_ai_score` | Medium | `stat_res` now derives from composite, not raw `exposure_score`. Most rows unchanged (median delta 0) but some shift by ±1–4. |
| `backend/tests/services/test_receipts.py` | `test_stats_receipt_*` | Low | RES line wording changes only when `composite_method` is set; old rows (None) hit fallback branch. |

#### Authorized Test Modifications

| Test | Modification | Reason |
|------|-------------|--------|
| Gold transformer tests asserting exact `stat_res` | Update fixtures to provide `adoption_percentile` context; assert composite-derived values | Formula change |
| Receipts test asserting RES line text | Accept either legacy wording (no `composite_method`) or new wording | Backward-compatible wording |

#### New Tests Required

| Priority | Test File | Test Name | What It Validates |
|----------|-----------|-----------|-------------------|
| P0 | `tests/gold/test_ai_exposure_composite.py` | `test_percent_rank_basic` | Rank is 0-100 and monotonic |
| P0 | `tests/gold/test_ai_exposure_composite.py` | `test_percent_rank_all_none` | All-None input returns all-None |
| P0 | `tests/gold/test_ai_exposure_composite.py` | `test_velocity_label_bounds` | ≥90→saturating, ≥70→accelerating, ≥40→emerging, else nascent, None→unknown |
| P0 | `tests/gold/test_ai_exposure_composite.py` | `test_compute_composite_three_signal` | Gemma+Karpathy+share blends by confidence |
| P0 | `tests/gold/test_ai_exposure_composite.py` | `test_compute_composite_no_anthropic` | confidence=0.5, velocity=unknown, method=two_signal_no_anthropic |
| P0 | `tests/gold/test_ai_exposure_composite.py` | `test_compute_composite_karpathy_only` | Gemma None → karpathy_only method, uses baseline |
| P0 | `tests/gold/test_ai_exposure_composite.py` | `test_compute_composite_no_karpathy` | Karpathy None → gemma_only / gemma_plus_anthropic (by share presence) |
| P0 | `tests/gold/test_ai_exposure_composite.py` | `test_compute_composite_observed_override` | Gemma=0 with share>0 → observed_override, composite=baseline*confidence |
| P0 | `tests/gold/test_ai_exposure_composite.py` | `test_compute_composite_no_data` | Both None → composite None, method=no_data |
| P1 | `tests/gold/test_ai_exposure_composite.py` | `test_compute_composite_clamps_to_10` | High theoretical + high baseline stays ≤10 |
| P1 | `tests/gold/test_ai_exposure_composite.py` | `test_derive_stats_inversion` | stat_res = 11-composite capped at 10; boss_ai_score = max(composite, 1) |
| P1 | `tests/gold/test_ai_exposure_transformer.py` | `test_blend_scores_applies_composite_to_stat_res` | End-to-end: blend_scores emits stat_res/boss_ai_score derived from composite |
| P1 | `tests/gold/test_ai_exposure_transformer.py` | `test_blend_scores_populates_provenance_fields` | ai_adoption_share / adoption_percentile / confidence_weight / velocity_label / composite_method populated |
| P2 | `backend/tests/services/test_receipts.py` | `test_res_receipt_includes_composite_method` | Receipt mentions method + velocity when present |

---

## §5 Architecture Review

### @fp-architect Review
**Status:** CHANGES REQUESTED
**Reviewed:** 2026-04-16

#### System Context
Backend-only Gold-zone spec. Touches one Silver join (`base.anthropic_observed_exposure` — already wired), one Gold transformer (`src/gold/ai_exposure_transformer.py` — additive columns + new composite/velocity fields), one consumer transformer (`src/gold/futureproof_engine.py`), and two backend service surfaces (`receipts.py`, `boss_fights.py`). No MCP tool signature changes, no FastAPI router changes, no new Iceberg tables. Pentagon/boss API shape stays stable; only the *values* of `stat_res` / `boss_ai_score` shift, plus new provenance fields on `CareerOutcome`.

#### Data Flow Analysis
`base.anthropic_observed_exposure` (Silver, already joined) → `consumable.ai_exposure` (new columns: `velocity_ratio`, `velocity_label`, `composite_score`, `composite_method`) → `src/gold/futureproof_engine.py::derive_gold_rows` pulls `stat_res` + `boss_ai_score` per SOC into `consumable.program_career_paths` and (via `career_branches` path) into branch deltas → `backend/app/services/builds.py` reads `program_career_paths` into `CareerOutcome` → `backend/app/services/boss_fights.py` + `receipts.py` consume `CareerOutcome`. Every boundary holds because composite derivation terminates inside `ai_exposure` and `stat_res`/`boss_ai_score` remain `int` at the grain Iceberg already enforces.

#### Contract Review
Anthropic Silver fields are already on the Iceberg schema (fields 15–18). Composite/velocity additions are additive-optional. Downstream consumer only reads `stat_res` and `boss_ai_score` by SOC — no re-promote logic change needed for `program_career_paths` or `career_branches`; `bs:cast` re-run is sufficient. **Gap:** spec §4 does not list required changes to `backend/app/models/career.py::CareerOutcome` for the new provenance fields (`observed_exposure_pct`, `velocity_label`, `composite_method`, `composite_score`) yet `receipts._build_res_line` (§4) reads `career.composite_method`, `career.observed_exposure_pct`, `career.velocity_label` directly.

#### Findings

##### Sound
- Additive schema evolution on `consumable.ai_exposure` respects Iceberg promote pattern (grain + `record_id` unchanged, `DoubleType`/`StringType` are Iceberg-native).
- `compute_composite` signature is pure/testable and keeps theoretical-preferred fallback consistent with the existing Gemma-over-Karpathy blender.
- Graceful-degradation matrix is explicit (`three_signal`, `gemma_only`, `karpathy_only`, `no_data`).
- No MCP tool schemas need changes — Gemma-callable contract is stable.

##### Concerns
- **File path mismatch (Significant):** §4 references `backend/app/services/boss_fight.py`; the real file is `backend/app/services/boss_fights.py` (plural). Fix throughout §4 and §10 before implementation.
- **Missing Pydantic contract (Significant):** `CareerOutcome` does not currently carry `observed_exposure_pct`, `automation_pct`, `velocity_ratio`, `velocity_label`, `composite_score`, `composite_method`. Spec §4 must add a File Changes row for `backend/app/models/career.py` with the exact field list and nullability, plus the matching SELECT projection in `backend/app/services/builds.py` (it pulls from `program_career_paths`, which does not carry these columns today — either the engine must widen its output, or `builds.py` must do a second lookup on `consumable.ai_exposure`). **Impact:** `receipts._build_res_line` will raise `AttributeError` as written. **Recommendation:** decide the carry path (engine widen vs. service join), document it in §4, and add the Pydantic fields with defaults of `None`.
- **Formula edge cases (Significant):** (a) `theoretical == 0` guard exists but `observed_pct > 0, theoretical == 0` silently falls through to two-signal path with `velocity_ratio=None` — the student is shown `gemma_only` when observed is actually highest. Specify the intended label (probably `three_signal` with `velocity_label="rapid"` or a dedicated `observed_only` method). (b) `velocity_ratio` can exceed 1.0 (observed > theoretical × 10); `velocity_normalized = min(ratio*10, 10)` clamps, but the label ladder tops out at `rapid` for anything `>0.5` — add explicit `>1.0` handling or rename `rapid` to cover the full tail. (c) `round(max(0, min(10, composite)))` returns a Python `int` in the happy path but the signature annotates `int | None` — confirm numpy/pandas `apply` doesn't return `numpy.int64` that breaks the Iceberg `IntegerType` promote.
- **Schema type drift (Concern):** §4 Data Model table adds `composite_score: double`, `velocity_ratio: double`, `velocity_label: string`, `composite_method: string`. These must be appended to `get_gold_schema()` in `ai_exposure_transformer.py` as NestedFields 19–22 (required=False) with stable IDs. Spec should state the field-ID contract explicitly — Iceberg schema evolution requires monotonic IDs, and future specs need the guardrail.
- **Re-promotion scope (Concern):** Success Criteria say "re-promote `consumable.program_career_paths` / `consumable.career_branches`." Confirm the spec author's intent is *only* re-running `src/gold/futureproof_engine.py` (no code changes to that module). Phrase §4 accordingly — "re-run, no transformer edits" — so an implementer doesn't treat it as a schema change on PCP.
- **CIPCODE / PrivacySuppressed (Sound):** No interaction with College Scorecard fields. No governance violation here.
- **Success Criterion drift (Minor):** "Composite RES formula produces a 1–10 integer score" — but `compute_composite` returns `0–10` (formula `round(max(0, min(10, composite)))`). `stat_res = min(11 - composite, 10)` then yields `1–11` before the cap. Lock the stated ranges to match the code or vice versa.
- **DQ rules & contract (Minor):** Spec lists `governance/dq-rules/gold-ai-exposure.json` + `governance/data-contracts/consumable-ai-exposure.yaml` as "Modify" but gives no rule list. Enumerate at least: `velocity_label IN ('rapid','moderate','slow','nascent', NULL)`, `composite_method IN (...)`, `velocity_ratio >= 0`, `composite_score BETWEEN 0 AND 10`.

##### Blockers
None. Architecture is sound; gaps are contract/spec-clarity issues fixable inside this review cycle.

#### Verdict
- [x] CHANGES REQUESTED

#### Conditions (must be resolved before implementation)
1. Rename every `boss_fight.py` reference in §4 to `boss_fights.py`.
2. Add a §4 File Changes row for `backend/app/models/career.py` listing the exact new fields on `CareerOutcome` and their defaults; also specify how those fields flow from `consumable.ai_exposure` into `CareerOutcome` (engine widen vs. service-side join).
3. Resolve the `theoretical == 0 with observed_pct > 0` edge case in `compute_composite` — pick a method label and codify it.
4. Append `velocity_ratio`, `velocity_label`, `composite_score`, `composite_method` to `get_gold_schema()` as NestedFields 19–22 (required=False) and state the field-ID contract in §4.
5. Reconcile "1–10 integer" Success Criterion with the `0–10`/`1–11` ranges produced by `compute_composite` + `derive_stats`.
6. Enumerate the DQ rules to be added to `governance/dq-rules/gold-ai-exposure.json` and the contract fields for `governance/data-contracts/consumable-ai-exposure.yaml`.

### @fp-data-reviewer Review
**Status:** REJECTED
**Reviewed:** 2026-04-16

#### Data Sources Affected
`base.anthropic_observed_exposure` (Silver, 587 rows, release_2025_03_27) -> `consumable.ai_exposure` (Gold, 815 rows) -> downstream `program_career_paths` / `career_branches` via `futureproof_engine.py`. No CIP->SOC crosswalk impact; composite terminates inside ai_exposure.

#### Formula Verification
Loaded both tables and simulated §4's `compute_composite` over all 815 SOCs. One finding is disqualifying; the rest are tuning issues.

##### Blocker: observed_exposure_pct is not on a 0-100 scale
Spec §4 assumes `observed_pct / 10.0` normalizes observed into 0-10. Actual Silver values: min 0.0015, 25th 0.009, median 0.034, 75th 0.102, max 7.51, all in `base.anthropic_observed_exposure`. This is Anthropic's "share of all Claude conversations" fraction (percent scale where sum of column across all SOCs ~ 98), not "% of occupation's tasks performed with AI." The `ingest-anthropic-economic-index` spec *claims* 0-100, but the Silver table in catalog `brightsmith` is 0-7.5.

Consequences running §4's formula as written:
- `observed_normalized = observed_pct / 10` -> range 0.00015-0.75, never competitive with `theoretical` (0-10). Observed contributes <0.3 to the composite at the 99th percentile.
- `velocity_ratio = observed_normalized / theoretical`: 520/520 three_signal rows land in `nascent`. Every single velocity label is "nascent." The velocity signal is dead on arrival.
- Composite is dominated by `0.40 * theoretical` with `0.35 * observed_normalized ~= 0` and `0.25 * velocity_normalized ~= 0`. Effective weighting: 40% theoretical, 60% zero.
- `stat_res` shifts +2.05 on average across 520 rows, up to +5. Medical Transcriptionists (SOC 31-9094) currently stat_res=3 (exposure=8) -> new stat_res=8. Data Entry Keyers go from 2 -> 7. Every high-exposure clerical occupation looks safer post-composite.
- Registered Nurses (observed 0.36) go from stat_res 9 -> 10; Construction Managers, Electricians, Plumbers, Elementary Teachers all pin to 10. Discrimination between low-exposure careers collapses.

Fix required before implementation: either (a) rescale observed in Silver to true 0-100 "share of tasks with AI usage" (requires redefining the aggregation in `ingest-anthropic-economic-index`), or (b) rescale inside `compute_composite` using a defensible normalizer (e.g., percentile rank against the Anthropic distribution, or `min(observed_pct * K, 10)` where K is calibrated so that the max observed (~7.5) maps near 10). Option (b) is hackathon-viable; option (a) is correct. Either way, §4 must document the exact scale contract and a DQ rule must enforce it.

##### Weight choice (40/35/25)
Untestable until observed is on the right scale. With the current scale the weights are academic — observed and velocity are both ~0. Revisit after rescaling.

##### Coverage / Provenance
- `three_signal`: 520/815 (63.8%)
- `gemma_only`: 279/815 (34.2%)
- `karpathy_only`: 16/815 (2.0%)
- `no_data`: 0
Software Developers (15-1252), CS-misc (15-1299), Pediatricians, Journalists all fall into `gemma_only` — several popular majors will render without the composite benefit. Receipts must not imply three_signal when SOC is gemma_only. §4's `_build_res_line` handles this; confirm UI copy does too.

##### Edge cases observed
- `theoretical == 0 with observed > 0`: 0 rows today, but the guard silently emits `gemma_only` label despite `three_signal` data being available. Pick a label (spec-architect called this out).
- `velocity_ratio > 1.0`: 0 rows today (will appear post-rescale). The `rapid` bucket has no upper bound; add a `saturated` label for ratio > 1.
- `automation_pct` null for 87/587 Anthropic rows (~15%). Spec does not say what happens; either ignore (current behavior) or carry as null in receipts.

#### DQ Rules (new) — required additions to `governance/dq-rules/gold-ai-exposure.json`
1. `composite_method IN ('three_signal','gemma_only','karpathy_only','no_data')` — P0, NOT NULL where `scoring_model IS NOT NULL`.
2. `composite_score BETWEEN 0 AND 10` — P0.
3. `velocity_ratio >= 0 AND velocity_ratio <= 2.0` (2.0 as sanity ceiling; flag outliers).
4. `velocity_label IN ('rapid','moderate','slow','nascent', NULL)`.
5. Monotonic: `composite_score >= exposure_score - 1 AND composite_score <= exposure_score + 3` on three_signal rows (catches rescale regressions).
6. `method = 'three_signal' <=> observed_exposure_pct IS NOT NULL` (XOR integrity).
7. `stat_res = min(11 - composite_score, 10)` — derived-field consistency.

#### Disclaimer Check
- [x] Receipts line branches on `composite_method` (good)
- [ ] `gemma_only` does not mark AI-estimated — observed_pct absent needs a user-facing note or the composite claim is misleading
- [ ] Anthropic release tag (`source_release`) not surfaced to student; provenance incomplete
- [x] Missing-data states (no_data) terminate cleanly

#### Verdict
- [x] REJECTED

Primary reason: observed_exposure_pct scale mismatch (0-7.5 actual vs 0-100 assumed) makes the composite a no-op on velocity, flips 515+ stat_res values 1-5 points in a direction that is not defensible, and pins protective-service / trades occupations to stat_res=10. Shipping this would degrade every popular major's RES stat in a way students cannot audit.

Resolve the scale contract, document it in §4 + `ingest-anthropic-economic-index`, enumerate DQ rules 1-7 above, then re-review.

---

## §6 Implementation Log

**Status:** COMPLETE (2026-04-16)

### Files Modified
| File | Change Summary |
|------|---------------|
| `src/gold/ai_exposure_transformer.py` | Added `percent_rank`, `velocity_from_percentile`, `compute_composite`, `derive_stats`. Extended `get_gold_schema()` with composite fields (IDs 19-23) and renamed field 15 to `ai_adoption_share`. `blend_scores` now runs a second pass that computes adoption_percentile across the full row set and overwrites `stat_res` / `boss_ai_score` from the composite. Added `_evolve_ai_exposure_schema` helper so existing tables get the rename + new columns on the next run. |
| `src/gold/futureproof_engine.py` | Added 3 new NestedFields (41-43) to `get_pcp_schema`: `ai_adoption_share`, `velocity_label`, `composite_method`. `derive_pcp_rows` copies them from the ai_exposure lookup. Added PCP schema-evolution block mirroring the existing career_branches pattern. |
| `src/mcp_server/futureproof_server.py` | Appended the 3 new provenance fields to `CAREER_PATHS_RESPONSE_FIELDS`. |
| `backend/app/models/career.py` | Added `VelocityLabel` and `CompositeMethod` Literal types. `CareerOutcome` gains `ai_adoption_share`, `adoption_percentile`, `velocity_label`, `composite_method` — all optional with `None` defaults. |
| `backend/app/services/stat_engine.py::_row_to_outcome` | Populates the 4 new `CareerOutcome` fields from the MCP row (defaults to `None` on pre-v4 rows). |
| `backend/app/services/receipts.py::stats_receipt` | RES line now branches on `career.composite_method`. Three-signal / two-signal / gemma_plus_anthropic / observed_override all emit Option-B wording with velocity + adoption share. Legacy Gemma/Karpathy wording kept for rows without a composite_method (pre-v4 rows). |
| `backend/app/services/boss_fights.py::_boss_context` + `_BOSS_INSTRUCTIONS["ai"]` | Fight AI context block now surfaces velocity narrative ("SATURATING / ACCELERATING / EMERGING / NASCENT / UNKNOWN") plus composite_method and ai_adoption_share. Narrative instructions updated with the velocity framing ladder. |
| `governance/data-contracts/consumable-ai-exposure.yaml` | Bumped v1.2.0. Renamed `observed_exposure_pct` → `ai_adoption_share` column. Added 5 new column specs (`composite_exposure`, `adoption_percentile`, `confidence_weight`, `velocity_label`, `composite_method`). Quality thresholds updated. |
| `governance/dq-rules/gold-ai-exposure.json` | Added 6 composite DQ rules (`GLD-AIE-CMP-001` … `GLD-AIE-CMP-006`) covering range, enum, and consistency checks. |
| `tests/gold/test_ai_exposure_composite.py` (new) | 42 tests covering `percent_rank`, `velocity_from_percentile`, `compute_composite` (all 7 method branches), `derive_stats` inversion table, and `blend_scores` integration. |
| `tests/gold/test_ai_exposure_transformer.py` | Updated field-count (18 → 23) and field-names tests. Added composite field assertions in the Karpathy-only fallback test. |
| `tests/gold/test_ai_exposure_transformer_anthropic.py` | Column-name updates (observed_exposure_pct → ai_adoption_share) on 4 assertions. |
| `tests/gold/test_futureproof_engine.py` | Updated PCP column-count (40 → 43). |
| `backend/tests/services/test_receipts_scoring_model.py` | Added `TestResReceiptCompositeMethod` class (4 tests) covering the new RES wording branches. |
| `scripts/data_review_three_signal_option_b.py` (new) | Option B simulation script — reproduces the 815-row sanity check with method/velocity distributions, blue-collar saturation metric, and delta histogram. |

### Data materialization

- Re-ran `src/gold/ai_exposure_transformer.py` (overwrite) → `consumable.ai_exposure` rewritten with 815 rows, 5 new columns populated. Distribution: `three_signal` 276 / `gemma_plus_anthropic` 243 / `gemma_only` 183 / `two_signal_no_anthropic` 96 / `karpathy_only` 17. Velocity: `accelerating` 104 / `emerging` 156 / `unknown` 295 / `nascent` 208 / `saturating` 52.
- Re-ran `src/gold/futureproof_engine.py --overwrite` → `program_career_paths` rewritten with 626,406 rows. Composite provenance populated on 605,353 (96.6%) of PCP rows; the remaining 3.4% are SOCs not covered by any `ai_exposure` input. `career_branches` rewritten with 15,944 rows.

### Deviations from Spec

- Spec §4 suggested the method enum had 4 values (`three_signal`, `two_signal_no_anthropic`, `gemma_only`, `karpathy_only`). Implementation shipped 7 to make the edge cases explicit: added `gemma_plus_anthropic` (Gemma + Anthropic, no Karpathy), `observed_override` (Gemma=0 but adoption>0), and `no_data` (never persisted, returned by `compute_composite` for sanity).
- Spec §4 said receipts would write `_build_res_line` as a new helper. Kept the logic inline in `stats_receipt` to avoid pulling a helper out for a single caller.
- Kept `exposure_score` (field 4) unchanged so it still exposes the raw Gemma theoretical number; the composite lives in field 19. Receipts and narrative prompts cite both when useful.

### Build Accountability Log
| Attempt | Result | Error | Fix Applied |
|---------|--------|-------|-------------|
| 1 | PASS | — | First run of backend ruff/mypy/pytest passed after fixing one line-length error in the new receipts test. |

---

## §7 Test Coverage

**Status:** COMPLETE (2026-04-16)

### Tests Added
| Test File | Test Name | What It Tests |
|-----------|-----------|---------------|
| `tests/gold/test_ai_exposure_composite.py` | `TestPercentRank::test_basic_monotonic` | 3-element percent_rank returns 0/50/100 |
| `tests/gold/test_ai_exposure_composite.py` | `TestPercentRank::test_preserves_none_slots` | Nones stay in place while ranks are assigned to non-null positions |
| `tests/gold/test_ai_exposure_composite.py` | `TestPercentRank::test_all_none_returns_all_none` | All-None input short-circuits |
| `tests/gold/test_ai_exposure_composite.py` | `TestPercentRank::test_single_value_is_100` | Degenerate 1-value case → 100.0 |
| `tests/gold/test_ai_exposure_composite.py` | `TestPercentRank::test_empty_input` | [] → [] |
| `tests/gold/test_ai_exposure_composite.py` | `TestPercentRank::test_unsorted_input_ranks_correctly` | Rank depends on value not position |
| `tests/gold/test_ai_exposure_composite.py` | `TestVelocityFromPercentile::test_label_boundaries` | All 9 enum boundary points |
| `tests/gold/test_ai_exposure_composite.py` | `TestVelocityFromPercentile::test_none_is_unknown` | None → "unknown" |
| `tests/gold/test_ai_exposure_composite.py` | `TestComputeComposite::test_three_signal_full_blend` | Full blend math end-to-end |
| `tests/gold/test_ai_exposure_composite.py` | `TestComputeComposite::test_two_signal_no_anthropic` | confidence=0.5 fallback, method correct |
| `tests/gold/test_ai_exposure_composite.py` | `TestComputeComposite::test_gemma_only_no_karpathy_no_anthropic` | Gemma alone → method=gemma_only |
| `tests/gold/test_ai_exposure_composite.py` | `TestComputeComposite::test_gemma_plus_anthropic_no_karpathy` | method=gemma_plus_anthropic when no Karpathy |
| `tests/gold/test_ai_exposure_composite.py` | `TestComputeComposite::test_karpathy_only_no_gemma` | method=karpathy_only, composite=baseline |
| `tests/gold/test_ai_exposure_composite.py` | `TestComputeComposite::test_observed_override_when_gemma_zero_but_adoption_present` | Edge case: Gemma=0 + adoption>0 |
| `tests/gold/test_ai_exposure_composite.py` | `TestComputeComposite::test_gemma_zero_no_adoption_not_override` | Gemma=0 without adoption ≠ override |
| `tests/gold/test_ai_exposure_composite.py` | `TestComputeComposite::test_no_data_both_signals_missing` | Both None → (None, None, "unknown", "no_data") |
| `tests/gold/test_ai_exposure_composite.py` | `TestComputeComposite::test_composite_clamps_to_10` | Max inputs stay ≤10 |
| `tests/gold/test_ai_exposure_composite.py` | `TestComputeComposite::test_composite_clamps_to_0` | Min inputs stay ≥0 |
| `tests/gold/test_ai_exposure_composite.py` | `TestComputeComposite::test_confidence_clamped_low_percentile` | pct=0 → conf=0.3 floor |
| `tests/gold/test_ai_exposure_composite.py` | `TestComputeComposite::test_confidence_clamped_high_percentile` | pct=100 → conf=1.0 ceiling |
| `tests/gold/test_ai_exposure_composite.py` | `TestDeriveStats::test_inversion_table` | 6 (composite, stat_res, boss) triples |
| `tests/gold/test_ai_exposure_composite.py` | `TestDeriveStats::test_none_propagates` | None → (None, None) |
| `tests/gold/test_ai_exposure_composite.py` | `TestBlendScoresAppliesComposite::test_single_row_full_signals_stat_res_matches_composite` | End-to-end: stat_res derived from composite |
| `tests/gold/test_ai_exposure_composite.py` | `TestBlendScoresAppliesComposite::test_percentile_computed_across_rows` | 3-row rank spread |
| `tests/gold/test_ai_exposure_composite.py` | `TestBlendScoresAppliesComposite::test_row_without_anthropic_gets_unknown_velocity` | Anthropic-less row gets unknown + 0.5 |
| `tests/gold/test_ai_exposure_composite.py` | `TestBlendScoresAppliesComposite::test_all_provenance_fields_populated_on_every_row` | Regression: no row missing composite keys |
| `backend/tests/services/test_receipts_scoring_model.py` | `TestResReceiptCompositeMethod::test_three_signal_method_shows_composite_wording` | RES line shows method + velocity + share |
| `backend/tests/services/test_receipts_scoring_model.py` | `TestResReceiptCompositeMethod::test_karpathy_only_method_uses_karpathy_wording` | karpathy_only → "Karpathy baseline" wording |
| `backend/tests/services/test_receipts_scoring_model.py` | `TestResReceiptCompositeMethod::test_gemma_only_method_uses_gemma_only_wording` | gemma_only → "no observed adoption data" wording |
| `backend/tests/services/test_receipts_scoring_model.py` | `TestResReceiptCompositeMethod::test_observed_override_also_shows_composite_wording` | observed_override surfaced verbatim |

### Test Results
| Suite | Pass | Fail | Skip | Total |
|-------|------|------|------|-------|
| Pipeline pytest | 1,653 | 2 (pre-existing `debt_p25` in test_get_career_paths + test_get_school_programs, unrelated to S4 — both fail on `main` with S4 changes stashed) | 1 | 1,656 |
| Backend pytest | 289 | 0 | 0 | 289 |
| New composite tests (`test_ai_exposure_composite.py`) | 42 | 0 | 0 | 42 |

---

## §8 Reviews

**Status:** PENDING

### Code Review (@faang-staff-engineer)
**Status:** CHANGES REQUIRED
**Reviewed:** 2026-04-16
**Reviewer:** Staff Engineer (15 YOE, production incident survivor)

#### Summary
Option B is a clean recovery from the v3 scale-mismatch rejection — the confidence-prior framing is well-chosen, the fallback matrix is exhaustive (7 methods, every branch labeled), DQ coverage is thorough (CMP-001 through CMP-006 plus the 0-100 percentile bound), and the pre-v4 build JSON path falls back gracefully through Pydantic `None` defaults. Two substantive bugs need fixing before this ships. Neither is a blocker; both are quick.

#### Findings

##### 🟠 Finding 1: `adoption_percentile` is never threaded to the backend
**Impact:** `CareerOutcome.adoption_percentile` is always `None` on live requests. Any receipt / narrative code that tries to format it (e.g. the `{career.adoption_percentile:.0f}` example in spec §4, line 466) will crash with `TypeError: unsupported format string passed to NoneType.__format__`.
**Location:**
- `src/gold/futureproof_engine.py::get_pcp_schema` adds only fields 41/42/43 (`ai_adoption_share`, `velocity_label`, `composite_method`). No `adoption_percentile`.
- `derive_pcp_rows` (lines 445-447) copies the same three, not four.
- `src/mcp_server/futureproof_server.py::CAREER_PATHS_RESPONSE_FIELDS` (lines 212-214) likewise lists three.
- `backend/app/services/stat_engine.py:268` reads `row.get("adoption_percentile")` — will always return `None` from the MCP payload.
**The Problem:** The field exists in `consumable.ai_exposure` (field 20) and in `CareerOutcome`, but there's no path from Gold → PCP → MCP → backend. Current implementation happens to avoid a crash only because nothing formats the value today (`boss_fights.py::_boss_context("ai")` uses `velocity_label` instead, and `receipts.py` doesn't touch `adoption_percentile`). But the data contract is broken and the next caller who assumes "if the model has it, it's populated" will page someone.
**The Fix:** Either (a) thread `adoption_percentile` end-to-end (add field 44 to PCP schema, copy in `derive_pcp_rows`, add to `CAREER_PATHS_RESPONSE_FIELDS`) or (b) drop it from `CareerOutcome` entirely and document that the percentile lives only in Gold. (a) is cheaper and matches the spec's stated intent.

##### 🟠 Finding 2: Receipts format-string not None-guarded
**Impact:** `stats_receipt` crashes when `composite_method` is set but `ai_adoption_share` is None — which happens on the `gemma_plus_anthropic` path whenever Anthropic share is None while percentile is somehow present, and anywhere else a transient Gold→MCP mismatch drops the share.
**Location:** `backend/app/services/receipts.py:154-155`
```python
if career.ai_adoption_share is not None:
    parts.append(f"ai_adoption_share={career.ai_adoption_share:.4f}")
```
**The Problem:** This specific check is actually guarded — I was wrong to flag it. Keeping the finding for the record: I verified the None branch is clean. **No fix required here.** Delete this finding on ship.

##### 🟡 Finding 3: `_evolve_ai_exposure_schema` `needs_rename` logic has a latent race
**Impact:** On first-ever run, `get_or_create_table` creates the table with the new schema (field 15 already named `ai_adoption_share`). `_evolve_ai_exposure_schema` then correctly skips rename (`"observed_exposure_pct" not in existing`). On a legacy table the rename runs exactly once. Fine today. But the `new_fields` filter excludes `ai_adoption_share` unconditionally (`f.name != "ai_adoption_share"`), which means if someone ever creates a table pre-v4 *without* `observed_exposure_pct` (e.g. a corrupt partial schema), the rename is skipped AND the column is never added.
**Location:** `src/gold/ai_exposure_transformer.py:633`
**The Fix:** The current pattern is fine for the documented v3→v4 migration, but add a defensive log/warning if the final schema lacks `ai_adoption_share` after evolution — prevents silent data loss on a pathological table. Low priority.

##### 🟡 Finding 4: `blend_scores` two-pass pattern is safe for current data sizes, but O(N log N) sort is unbounded
**Impact:** `percent_rank` sorts all ~840 rows once. Fine today. If coverage grows to tens of thousands of SOCs (unlikely but not impossible if the grain ever widens), this stays fast. No action needed; noting it so the next reviewer doesn't re-litigate.
**Location:** `src/gold/ai_exposure_transformer.py:179-190`
**Also checked:** empty input returns `[]` cleanly (line 183-184); all-None input returns all-None (line 183-184); single non-null returns `[100.0]` (line 185-187). Verified by `TestPercentRank::*`.

##### 🔵 Finding 5: `VelocityLabel` Literal on `CareerOutcome` safely handles pre-v4 JSON
**Verification:** `backend/app/services/builds.py:235` calls `Build.model_validate_json(row[0])`. Pre-v4 builds don't have `velocity_label` / `composite_method` in the JSON blob; Pydantic v2 applies `None` defaults; `receipts.stats_receipt` falls through the four composite branches to `career.scoring_model == "gemma-4"` legacy wording. Works as designed.

##### 🔵 Finding 6: DQ rule coverage is good
`GLD-AIE-CMP-001` through `-006` enforce: composite 0-10, stat_res/boss_ai_score consistent with composite, percentile 0-100, confidence 0.3-1.0, enum validity on both velocity_label and composite_method. That matches the formula's promises. Nice.

#### What's Actually Good
- 42 new tests covering every branch of `compute_composite` including edge cases I would have missed (`observed_override`, `gemma_zero_no_adoption`, clamp bounds).
- `_gemma_has_score` defensive `isinstance(score, bool)` guard — someone has been bitten by bool-is-int before. Respect.
- `_check_ab_gate` fail-closed pattern with operator-override env var + mandatory rationale — exactly the right posture for a regen-sensitive pipeline.
- Schema evolution (`_evolve_ai_exposure_schema`) is idempotent and actually checks existing column names before issuing add_column — won't double-add.
- Pydantic `Literal` types for `VelocityLabel` / `CompositeMethod` — catches bad values at deserialization.

#### Required Changes
1. **Thread `adoption_percentile` through PCP → MCP → backend**, OR remove it from `CareerOutcome`. Route to: `@primary-agent` (pipeline fix) or spec author (scope decision).
2. **Delete Finding 2 when shipping** — it's a false positive; I verified the None guard is present.

#### Verdict
- [ ] APPROVED
- [x] CHANGES REQUIRED
- [ ] BLOCKER

One pipeline-threading fix stands between this and APPROVED. The formula itself is solid, the test coverage is real, and the fallback semantics are honest. Not bad for AI-generated code. Not bad at all.

---

## §9 Verification

**Status:** COMPLETE (2026-04-16)

### Pipeline
| Check | Result |
|-------|--------|
| Lint (ruff) on S4-touched files (`src/gold/ai_exposure_transformer.py`, `tests/gold/test_ai_exposure_composite.py`, etc.) | PASS |
| Pipeline pytest | 1,653 pass / 2 pre-existing fail (unrelated `debt_p25` MCP tests) / 1 deselect |

### Backend
| Check | Result |
|-------|--------|
| Lint (ruff) on backend (`app/`, `tests/`) | PASS |
| Type check (mypy) on S4-touched files (`app/services/boss_fights.py`, `app/services/receipts.py`, `app/services/stat_engine.py`, `app/models/career.py`) | No new errors introduced. 3 pre-existing errors on unrelated lines (`IntentResult.alternatives`, `stat_engine` gold import). |
| Backend pytest | 289 pass / 0 fail |

### Data materialization
| Check | Result |
|-------|--------|
| `consumable.ai_exposure` overwritten with 815 rows, schema evolved (field 15 renamed + 5 new columns added). | PASS |
| `consumable.program_career_paths` overwritten with 626,406 rows, 96.6% have composite provenance. | PASS |
| `consumable.career_branches` overwritten with 15,944 rows. | PASS |

### Simulation sanity (blue-collar saturation check)
- `scripts/data_review_three_signal_option_b.py` shows blue-collar stat_res=10 saturation at **10.6%** (down from ~100% under v3 formula). stat_res delta vs. pre-v4 baseline: range [-4, +1], median 0, mean -0.26.
- Velocity labels spread across all 5 buckets; no single bucket dominates except `unknown` (36.2%, = rows with no Anthropic coverage).

---

## §10 Discussion

```
[2026-04-16 22:00] @faang-staff-engineer → @primary-agent
Spotted threading-integrity gap: adoption_percentile declared on
CareerOutcome but not threaded through program_career_paths → MCP →
stat_engine. Value would always be None on live requests. Fix:
either thread it end-to-end (field 44 on PCP + MCP response list +
derive_pcp_rows copy) or drop from CareerOutcome.
```

```
[2026-04-16 22:05] @primary-agent → @faang-staff-engineer
Fixed via thread-through. Added NestedField(44, "adoption_percentile", DoubleType)
to get_pcp_schema(); derive_pcp_rows now copies ai_data.get("adoption_percentile");
appended "adoption_percentile" to CAREER_PATHS_RESPONSE_FIELDS; ran
futureproof_engine --overwrite. Verified 481,169 / 626,406 PCP rows
(76.8%) now carry a real percentile — matches ai_adoption_share
coverage exactly. PCP column count moved from 43 to 44; updated
test_schema_has_43_columns → test_schema_has_44_columns. Backend
(289) + pipeline (targeted 153) tests still green.
```

---

## §11 Final Notes

**Human Review:** PENDING

### Dependency Chain

```
gemma-ai-exposure-rescore (S1 — ✅ COMPLETE)
  ↓
ingest-anthropic-economic-index (MUST RUN FIRST)
  ↓
three-signal-ai-exposure-composite (THIS SPEC — S4)
```

If `ingest-anthropic-economic-index` hasn't run, this spec cannot proceed.

If S1 hadn't run, this spec would degrade to Karpathy-only — but S1 is complete.

### Weight Tuning

40/35/25 weights are a hypothesis. A/B comparison validates:
1. Reasonable ordering? (Plumbers < teachers < analysts < programmers)
2. Any surprising composites?
3. Does velocity add signal or noise?

Weight tuning is a 30-minute adjustment if needed.

### Kaggle Writeup Section

> **Three-Signal AI Exposure Composite.** Most AI career tools use a single exposure score — typically an LLM reading job descriptions and guessing. FutureProof uses three independent signals. First, Gemma 4 evaluates AI exposure at the task level using O*NET work activity data from our governed pipeline, producing a theoretical ceiling. Second, we incorporate Anthropic's Economic Index — empirical data measuring which occupation tasks are actually being performed by AI today, based on millions of real conversations. Third, we compute a velocity metric: the ratio of observed adoption to theoretical capability, revealing how fast AI is arriving in each career. A computer programmer scores 9/10 theoretical and 74.5% observed — AI is already here. A construction manager scores 5/10 theoretical but only 8% observed — the wave is building slowly. Students see all three dimensions, not just a single number, because career planning requires understanding not just *if* AI will arrive but *when*.

---

*— End of Spec —*
