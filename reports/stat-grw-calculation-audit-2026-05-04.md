# GRW (Growth) Stat — Complete Calculation Inventory

**Date:** 2026-05-04
**Purpose:** Identify every location where GRW is calculated, with inputs and formula for each.

---

## Canonical Formula

**File:** `src/gold/bls_ooh_occupation_profiles.py:67-96`

```python
def compute_grw_score(pct: float | None) -> float | None:
    if pct is None:
        return None
    if pct <= -20.0:
        return 1.0
    for pct_lo, pct_hi, score_lo, score_hi in GRW_BREAKPOINTS:
        if pct <= pct_hi:
            fraction = (pct - pct_lo) / (pct_hi - pct_lo)
            return score_lo + fraction * (score_hi - score_lo)
    return 10.0
```

**Input:** `employment_change_pct` — BLS 10-year employment projection (2024→2034)

**Breakpoints (lines 45-53):**

| employment_change_pct | GRW Score |
|----------------------|-----------|
| <= -20% | 1.0 (floor) |
| -20% → -10% | 1.0 → 2.5 |
| -10% → -1% | 2.5 → 4.0 |
| -1% → +1% | 4.0 → 5.0 |
| +1% → +5% | 5.0 → 6.5 |
| +5% → +10% | 6.5 → 7.5 |
| +10% → +20% | 7.5 → 9.0 |
| +20% → +50% | 9.0 → 10.0 |
| >= +50% | 10.0 (cap) |

**Rounding:** round-half-up → `grw_score_rounded` (integer 1-10)

**Design note:** National average growth (~4%) maps to approximately 6.0.

---

## Calculation Sites

### 1. Gold Pipeline — GRW Score Computation

**File:** `src/gold/bls_ooh_occupation_profiles.py:302-304`

```python
grw = compute_grw_score(row.get("employment_change_pct"))
row["grw_score"] = grw
row["grw_score_rounded"] = _round_half_up(grw) if grw is not None else None
```

**Inputs:**
- `employment_change_pct` — from Silver `base.bls_ooh` table (BLS Occupational Outlook Handbook)

**Stored in:** `consumable.occupation_profiles.grw_score_rounded`

---

### 2. Gold Pipeline — Market Score Composite (Uses GRW)

**File:** `src/gold/bls_ooh_occupation_profiles.py:306-317`

```python
market_score = 0.6 * grw_score + 0.4 * openings_score
```

**Inputs:**
- `grw_score` (60% weight) — from site #1
- `openings_score` (40% weight) — derived from annual job openings volume

GRW feeds the Market Boss score as the primary component. This is a secondary composite, not the pentagon stat itself.

---

### 3. Gold Pipeline — `stat_grw` Assignment

**File:** `src/gold/futureproof_engine.py:475-482`

```python
stat_grw = row.get("grw_score_rounded")
row["stat_grw"] = stat_grw
```

Simple pass-through — reads `grw_score_rounded` from occupation_profiles (joined via SOC code) and assigns it as `stat_grw` in `program_career_paths`. No transformation.

---

### 4. Gold Pipeline — Branch Delta (Absolute Difference)

**File:** `src/gold/futureproof_engine.py:606-646`

```python
source_grw = src_op.get("grw_score_rounded")
related_grw = rel_op.get("grw_score_rounded")
grw_delta = (related_grw - source_grw) if (related_grw is not None and source_grw is not None) else None
```

**Inputs:**
- `source_grw` — GRW of the current occupation
- `related_grw` — GRW of the branch target occupation

Unlike ERN/ROI branch deltas (which are derived from `wage_delta` thresholds), GRW branch deltas are computed as the literal difference between the two occupations' GRW scores. Stored in `consumable.career_branches.grw_delta`.

---

### 5. Backend — Pass-Through (No Recomputation)

**File:** `backend/app/services/stat_engine.py:420`

```python
stats = PentagonStats(
    ...
    grw=as_int(row.get("stat_grw")),
    ...
)
```

GRW is read directly from the MCP response. **No effort adjustment** — only ERN gets shifted by effort level. GRW passes through unchanged.

---

### 6. Backend — Market Boss Fight

**File:** `backend/app/services/boss_fights.py:537-541`

```python
def _score_market(career: CareerOutcome) -> tuple[int | None, str]:
    """GRW alone — market demand growth against the threshold."""
    if career.stats.grw is None:
        return None, "GRW unavailable"
    return career.stats.grw, f"GRW {career.stats.grw}"
```

The Market Boss uses GRW as its **sole input** (the post-delta, post-skill-craft value from the pentagon). Standard boss thresholds apply.

---

### 7. Backend — Skill Pool Delta Application

**File:** `backend/app/services/skill_pool.py:313-324`

```python
sum_grw = sum(s.delta_grw for s in skills)
grw = clamp(stats.grw + sum_grw, 1, 10) if stats.grw is not None else None
```

**Skills with delta_grw:**
- Emerging-Tech Certificate: +2
- Industry Conference Circuit: +1
- Portfolio-Building Independent Project: +1

---

### 8. Backend — Branch Tree Delta (From Table)

**File:** `backend/app/services/branch_tree.py:92`

```python
delta_grw=as_int(row.get("grw_delta"))
```

Reads the pre-computed `grw_delta` from the `career_branches` Gold table (site #4). No runtime derivation.

---

### 9. MCP Server — Pass-Through

**File:** `src/mcp_server/futureproof_server.py:2313`

```python
stat_grw = j.get("grw_score_rounded")
```

In the substitution path, GRW is read directly from the occupation_profiles lookup. No inline recomputation.

---

## Data Flow Summary

```
BLS Occupational Outlook Handbook
         |
         v
employment_change_pct (10-year projection, %)
         |
         v
compute_grw_score() — piecewise linear
         |
         v
grw_score (float, 1.0-10.0)
         |
         v
round_half_up → grw_score_rounded (int, 1-10)
         |
    +----+----+
    |         |
    v         v
stat_grw   market_score = 0.6*grw + 0.4*openings
(pentagon)  (Market Boss composite)
    |
    +------+------+
    |      |      |
    v      v      v
 effort  skill  branch
 shift   delta  delta
 (NONE)  (+1,+2) (literal diff)
    |      |
    v      v
  as-is  clamp(1,10)
```

---

## Observations

1. **Simplest pentagon stat.** GRW has a single input (`employment_change_pct`), a single transformation (piecewise linear), and no runtime re-derivation. It's the most straightforward of the five stats.

2. **No effort adjustment.** GRW is purely market-driven — a student's effort level doesn't change how fast their target industry is growing.

3. **Branch deltas are literal.** Unlike ERN/ROI (which use threshold-based heuristics from `wage_delta`), GRW branch deltas are the actual difference between source and target occupation scores. This means a branch from a +5% growth career to a +15% growth career shows the exact GRW point difference.

4. **Feeds two outputs.** GRW powers both the pentagon vertex (display) AND the Market Boss fight (via direct use as the boss score). The Market Boss in `boss_fights.py` uses the stat directly — it doesn't go through the market_score composite from occupation_profiles.

5. **No inconsistencies found.** The same `grw_score_rounded` value flows consistently from Gold through MCP to backend to frontend.
