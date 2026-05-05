# RES (AI Resilience) Stat — Complete Calculation Inventory

**Date:** 2026-05-04
**Purpose:** Identify every location where RES is calculated, with inputs and formula for each.

---

## Overview

RES is the most complex pentagon stat. It has **three layers** of derivation:

1. **Gold pipeline** — derives `stat_res` (AI exposure composite) and `stat_hmn` (O*NET human-essential ratio) independently
2. **Backend display** — blends them 50/50 into the pentagon's `res` value
3. **Fight AI** — uses raw inputs summed (NOT the blended display value)

---

## Calculation Sites

### 1. Gold Pipeline — `stat_hmn` (Human-Essential Ratio)

**File:** `src/gold/onet_work_profiles.py:217-330`

**Formula (two phases):**

**Phase 1 — Human Ratio (line 229):**
```python
human_ratio = human_importance_sum / total_importance_sum
```

Where:
- `human_importance_sum` = sum of importance scores for activities flagged as human-intensive
- `total_importance_sum` = sum of importance scores for ALL activities in the occupation

**Phase 2 — Min-Max Rescale to 1-10 (lines 309-323):**
```python
hmn = 1.0 + 9.0 * (human_ratio - observed_min) / (observed_max - observed_min)
hmn = clamp(hmn, 1.0, 10.0)
hmn_score_rounded = round_half_up(hmn)
```

**Inputs:**
- O*NET Work Activities for each SOC code
- `human_set` — set of element_ids for human-intensive activities (e.g., interpersonal, creative, judgment)
- Each activity's `importance` score

**Edge cases:**
- All ratios identical → midpoint (5.5 → rounds to 6)
- No activities → None
- Range is 0 → midpoint

---

### 2. Gold Pipeline — `stat_res` (AI Exposure Composite)

**File:** `src/gold/ai_exposure_transformer.py:206-508`

This is a multi-step process:

#### Step 2a: Confidence from Adoption Percentile (line 228-235)

```python
confidence = max(0.3, min(1.0, 0.3 + 0.7 * adoption_percentile / 100.0))
```

**Inputs:**
- `adoption_percentile` — percentile rank of `ai_adoption_share` across all 815+ SOCs (0–100)
- `ai_adoption_share` — from Anthropic Economic Index (share of Claude conversations for that occupation)

#### Step 2b: Velocity Label (lines 193-203)

```python
if percentile >= 90: "saturating"
if percentile >= 70: "accelerating"
if percentile >= 40: "emerging"
else:                "nascent"
```

#### Step 2c: Composite Exposure Score (lines 206-283)

`compute_composite(gemma_score, karpathy_score, ai_adoption_share, adoption_percentile)`

**7 routing methods:**

| Method | Condition | Formula |
|--------|-----------|---------|
| `no_data` | Both signals None | None |
| `karpathy_only` | Gemma None | `baseline` (clamped 0-10) |
| `gemma_only` | Karpathy None, no Anthropic | `theoretical` (clamped 0-10) |
| `gemma_plus_anthropic` | Karpathy None, has Anthropic | `theoretical` (clamped 0-10) |
| `observed_override` | Gemma==0 but adoption>0 | `round(baseline × confidence)` |
| `three_signal` | All present + has Anthropic | `round(confidence × theoretical + (1-confidence) × baseline)` |
| `two_signal_no_anthropic` | Both present, no Anthropic | `round(confidence × theoretical + (1-confidence) × baseline)` |

**The primary blend formula (three_signal):**
```
composite = confidence × gemma_score + (1 - confidence) × karpathy_score
```

Where confidence ranges 0.3–1.0 based on adoption percentile. Higher adoption → trust Gemma more.

**Inputs:**
- `gemma_score` (0-10) — Gemma 4 task-level AI exposure assessment
- `karpathy_score` (0-10) — Karpathy/Gemini-Flash baseline
- `ai_adoption_share` (float) — Anthropic Economic Index
- `adoption_percentile` (0-100) — rank of adoption_share across all SOCs

#### Step 2d: Composite → stat_res Inversion (lines 286-296)

```python
def derive_stats(composite_exposure):
    stat_res = min(11 - composite_exposure, 10)
    boss_ai_score = max(composite_exposure, 1)
    return stat_res, boss_ai_score
```

**Higher AI exposure → lower resilience.**

#### Step 2e: Two-Pass Application (lines 471-503)

The `blend_scores` function:
1. **First pass** — provisional `stat_res = compute_stat_res(exposure_score)` for each row (lines 421, 441)
2. **Second pass** — compute `adoption_percentile` across ALL rows, then overwrite with composite-based values (lines 475-503)

The second pass ensures percentile ranking uses the full SOC universe before deriving individual scores.

---

### 3. Gold Pipeline — `compute_stat_res` (Simple Inversion)

**File:** `src/gold/ai_exposure_transformer.py:299-307`

```python
def compute_stat_res(exposure_score: int) -> int:
    return min(11 - exposure_score, 10)
```

Used in the first pass only (later overwritten by the composite-based value in most cases).

---

### 4. Backend — `_blend_res` (Display Value)

**File:** `backend/app/services/stat_engine.py:44-67`

```python
def _blend_res(stat_res: int | None, stat_hmn: int | None) -> int | None:
    if stat_res is None and stat_hmn is None:
        return None
    if stat_res is None:
        return stat_hmn
    if stat_hmn is None:
        return stat_res
    return _round_half_up((stat_res + stat_hmn) / 2)
```

**Formula:**
```
RES (display) = round_half_up((stat_res + stat_hmn) / 2)
```

**Partial-null rule:**
- Both present → 50/50 blend
- Only `stat_res` → use stat_res as-is
- Only `stat_hmn` → use stat_hmn as-is
- Both None → None

**Called at line 415:**
```python
raw_stat_res = as_int(row.get("stat_res"))
raw_stat_hmn = as_int(row.get("stat_hmn"))
blended_res = _blend_res(raw_stat_res, raw_stat_hmn)
```

**Note:** This is explicitly a DRAFT formula (comment says "Pending EDA"). The 50/50 weights are provisional pending correlation analysis.

---

### 5. Backend — Fight AI Score (Uses Raw Inputs, NOT Blend)

**File:** `backend/app/services/boss_fights.py:493-523`

```python
def _score_ai(career: CareerOutcome) -> tuple[int | None, str]:
    raw_res = career.raw_stat_res
    raw_hmn = career.raw_stat_hmn
    score = _safe_sum(raw_res, raw_hmn)  # sum, NOT average
    return score, f"raw {res_str} + {hmn_str} = {score}"
```

**Formula:**
```
Fight AI Score = raw_stat_res + raw_stat_hmn
```

**Critical distinction:** Fight AI sums the raw inputs (range 2–20 when both present) rather than using the blended 1–10 display value. This preserves existing thresholds:
- **Win:** score >= 14
- **Draw:** score >= 10

**Partial-null:** Uses `_safe_sum` — sums whichever values are available (can be just one).

---

### 6. MCP Server — Pass-Through (No Recomputation)

**File:** `src/mcp_server/futureproof_server.py:2314-2315`

```python
stat_hmn = j.get("hmn_score_rounded")
stat_res = j.get("stat_res")
```

In the substitution path, `stat_res` comes from the `ai_exposure` table lookup and `stat_hmn` from the `onet_work_profiles` table. No inline recomputation — values are read directly from the Gold tables.

---

### 7. Career Tree — Branch Blending

**File:** `backend/app/services/career_tree.py:221-234`

```python
related_res_raw = as_int(row.get("related_res"))
related_hmn_raw = as_int(row.get("related_hmn"))
child = TreeNode(
    ...
    res=_blend_res(related_res_raw, related_hmn_raw),
    ...
    raw_stat_res=related_res_raw,
    raw_stat_hmn=related_hmn_raw,
)
```

Same `_blend_res` formula applied to branch career nodes. Both raw inputs preserved for Fight AI.

---

### 8. Branch Tree — RES Delta (From Table)

**File:** `backend/app/services/branch_tree.py:91`

```python
delta_res=as_int(row.get("res_delta"))
```

Unlike ERN and ROI (which derive deltas from `wage_delta`), the RES delta comes directly from the `career_branches` Gold table — it's pre-computed in the pipeline, not derived at runtime.

---

### 9. Skill Pool — RES Delta Application

**File:** `backend/app/services/skill_pool.py:310-322`

```python
sum_res = sum(s.delta_res for s in skills)
res = clamp(stats.res + sum_res, 1, 10) if stats.res is not None else None
```

**Skills with delta_res:**
| Skill | delta_res | Notes |
|-------|-----------|-------|
| Data Analytics Minor | +2 | |
| AI Literacy Elective | +1 | |
| Paid Internship | +2 | consolidated from legacy delta_hmn(1) + delta_res(1) |
| Design Thinking Course | +2 | consolidated from legacy delta_hmn(2) |
| Stress Management Course | +1 | consolidated from legacy delta_hmn(1) |
| Cohort Study Group | +1 | consolidated from legacy delta_hmn(1) |

---

## Data Flow Summary

```
                    SIGNAL 1                              SIGNAL 2
                    --------                              --------
    Gemma 4          Karpathy         Anthropic           O*NET
  (task-level)      (baseline)     (observed adoption)  (work activities)
   0-10 int         0-10 int       float (share)         importance scores
      |                |                |                      |
      v                v                v                      v
      +-------+--------+               |              human_importance_sum
              |                         |              ─────────────────────
              v                         v              total_importance_sum
      confidence = 0.3 + 0.7 *                               |
        (adoption_percentile / 100)                           v
              |                                        human_ratio (0-1)
              v                                               |
   composite = conf × gemma                                   v
             + (1-conf) × karpathy                   min-max rescale (1-10)
              |                                               |
              v                                               v
   stat_res = min(11 - composite, 10)                stat_hmn (1-10)
              |                                               |
              +------------------+----------------------------+
                                 |
                    +------------+------------+
                    |                         |
                    v                         v
           _blend_res (display)      _score_ai (Fight AI)
           = round((res+hmn)/2)      = raw_res + raw_hmn
                    |                         |
                    v                         v
           Pentagon RES (1-10)       Fight score (2-20)
                    |
              +-----+-----+
              |           |
              v           v
           skill       branch
           deltas      deltas
           (+1,+2)     (from table)
              |
              v
         clamp(1, 10)
```

---

## Observations

1. **DRAFT status.** The `_blend_res` 50/50 weight is explicitly provisional ("Pending EDA"). A correlation analysis between `stat_res` and `stat_hmn` is needed to pick final weights.

2. **Fight AI intentionally diverges from display.** The pentagon shows a blended 1–10, but the boss fight uses raw sum (2–20 scale). This preserves bit-exact compatibility with pre-reshape thresholds.

3. **Three data sources for one stat.** RES uniquely combines:
   - Gemma 4 task-level AI exposure (theoretical)
   - Karpathy/Gemini-Flash baseline (empirical)
   - Anthropic Economic Index (observed real-world adoption)
   - O*NET human-essential activity analysis

4. **Confidence-weighted blend.** The composite isn't a fixed-weight average — it dynamically weights Gemma vs. Karpathy based on how much real-world AI adoption exists for that occupation. High adoption → trust Gemma's theoretical score more.

5. **No runtime re-derivation.** Like ERN, the backend reads Gold values and only applies blending + skill/branch deltas. The complex composite is computed once at pipeline promotion time.

6. **Partial-null coverage:**
   - 33.9% of SOCs get the full three-signal composite
   - 29.8% get gemma + anthropic (no Karpathy)
   - 22.5% get gemma only
   - 11.8% get two-signal without Anthropic
   - 2.1% get karpathy only fallback

7. **`delta_res` consolidation.** The skill pool's `delta_res` absorbed the former `delta_hmn` — there is no longer a separate human-essential skill modifier. This happened during the pentagon-stat-reshape spec.
