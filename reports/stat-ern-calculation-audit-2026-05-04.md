# ERN (Earning Power) Stat — Complete Calculation Inventory

**Date:** 2026-05-04
**Purpose:** Identify every location where ERN is calculated, with inputs and formula for each.

---

## Canonical Formula

**File:** `src/gold/futureproof_engine.py:77-89`

```python
def compute_stat_ern(
    cip_family_earnings_rank: float | None,
    wage_percentile_overall: float | None,
) -> int | None:
    if cip_family_earnings_rank is None or wage_percentile_overall is None:
        return None
    raw = 0.6 * cip_family_earnings_rank + 0.4 * wage_percentile_overall
    return _round_half_up(1.0 + 9.0 * raw)
```

**Algebraic form:**
```
stat_ern = ROUND(1 + 9 × (0.6 × cip_family_earnings_rank + 0.4 × wage_percentile_overall))
```

- Output range: 1–10 (integer)
- Rounding: round-half-up (`math.floor(x + 0.5)`), not banker's rounding
- Returns None if either input is None

---

## Calculation Sites

### 1. Gold Pipeline — `cip_family_earnings_rank` Derivation

**File:** `src/gold/college_scorecard_career_outcomes.py:218-227`

**Formula (SQL):**
```sql
PERCENT_RANK() OVER (
    PARTITION BY cip_family
    ORDER BY earnings_1yr_median
) AS cip_family_earnings_rank
```

**Inputs:**
- `earnings_1yr_median` — field-of-study median earnings 1 year post-graduation (College Scorecard)
- `cip_family` — 2-digit CIP prefix (e.g., "52" for Business)

**Semantics:** Where this program's graduates land in the earnings distribution among all programs in the same broad field. Range 0.0–1.0.

**Null handling:** Only rows with non-null `earnings_1yr_median` participate (`WHERE earnings_1yr_median IS NOT NULL`).

---

### 2. Gold Pipeline — `wage_percentile_overall` Derivation

**File:** `src/gold/bls_ooh_occupation_profiles.py:179-186`

**Formula (SQL):**
```sql
PERCENT_RANK() OVER (
    ORDER BY median_annual_wage
) AS wage_percentile_overall
```

**Inputs:**
- `median_annual_wage` — BLS OOH median annual wage for the occupation

**Semantics:** Where this occupation's wage ranks among all U.S. occupations. Range 0.0–1.0.

**Null handling:** Only rows with non-null `median_annual_wage` participate (`WHERE median_annual_wage IS NOT NULL`).

---

### 3. Gold Pipeline — Row Assembly

**File:** `src/gold/futureproof_engine.py:468-479`

```python
cip_rank = row.pop("cip_family_earnings_rank", None)
stat_ern = compute_stat_ern(
    cip_rank,
    row.pop("wage_percentile_overall", None),
)
row["stat_ern"] = stat_ern
```

This is where the two percentile inputs (from sites #1 and #2) get joined via SOC crosswalk and passed into the canonical formula during Gold table promotion into `consumable.program_career_paths`.

---

### 4. Backend — Effort Adjustment (Only Stat Affected)

**File:** `backend/app/services/stat_engine.py:103-146`

**Formula:**
```python
EFFORT_SHIFT = {
    "working_hard": -2,
    "working":      -1,
    "balanced":      0,
    "focused":      +1,
    "all_in":       +2,
}

new_ern = clamp(stat_ern + EFFORT_SHIFT[effort], 1, 10)
```

**Inputs:**
- `stats.ern` — base ERN from Gold (site #3)
- `effort` — user-selected effort level (slider)

**Key design note (lines 103-108):** ERN is the ONLY pentagon stat affected by effort. ROI, RES, GRW, and AURA pass through unchanged. Rationale: effort reflects earning potential (studying harder → better job outcomes), not cost structure.

---

### 5. Backend — Pass-Through Read

**File:** `backend/app/services/stat_engine.py:417`

```python
stats = PentagonStats(
    ern=as_int(row.get("stat_ern")),
    ...
)
stats = _apply_effort(stats, effort)
```

No re-computation — reads the Gold-level `stat_ern` and applies effort shift. The backend does NOT re-derive ERN from raw inputs at request time (unlike ROI which re-derives from published_cost_4yr).

---

### 6. MCP Server — Substitution Path (Fan-Out)

**File:** `src/mcp_server/futureproof_server.py:2310`

```python
stat_ern = compute_stat_ern(cip_fam_rank, j.get("wage_percentile_overall"))
```

**Inputs:**
- `cip_fam_rank` = `school.get("cip_family_earnings_rank")` — from career_outcomes row for the school (line 2210)
- `j.get("wage_percentile_overall")` — from occupation_profiles row for each SOC in the crosswalk

**Context:** When a program doesn't exist in `program_career_paths` (e.g., substituted CIP), the MCP server builds rows from scratch by cross-joining the school's earnings rank with each occupation's wage percentile.

---

### 7. MCP Server — Schools-for-Career Path

**File:** `src/mcp_server/futureproof_server.py:2823-2825`

```python
ern = compute_stat_ern(
    school_row.get("cip_family_earnings_rank"),
    op.get("wage_percentile_overall"),
)
row["stat_ern"] = ern
```

**Inputs:**
- `school_row.get("cip_family_earnings_rank")` — from career_outcomes for that school+CIP
- `op.get("wage_percentile_overall")` — from occupation_profiles for the target SOC

**Context:** Leaderboard query that ranks schools for a given career. ERN is recomputed inline when joining school data with occupation data.

---

### 8. MCP Server — Composite Score (ERN + ROI)

**File:** `src/mcp_server/futureproof_server.py:3601-3606`

```sql
(CAST(stat_ern AS DOUBLE) + CAST(stat_roi AS DOUBLE)) / 2.0 AS composite_score,
RANK() OVER (
    ORDER BY
        (CAST(stat_ern AS DOUBLE) + CAST(stat_roi AS DOUBLE)) / 2.0 DESC,
        earnings_1yr_median DESC NULLS LAST,
        net_price_annual ASC NULLS LAST
) AS abs_rank
```

**Inputs:**
- `stat_ern` — pre-computed in Gold table
- `stat_roi` — pre-computed in Gold table

**Context:** The schools-for-career leaderboard ranks programs by the average of ERN and ROI. ERN is not recomputed here — it reads the stored value from `consumable.program_career_paths`.

---

### 9. Branch Tree — ERN Delta

**File:** `backend/app/services/branch_tree.py:20-35`

**Formula:**
```python
def _derive_ern_delta(row):
    wage_delta = row.get("wage_delta")
    if wage_delta >= 20_000:  return +2
    if wage_delta >= 5_000:   return +1
    if wage_delta <= -20_000: return -2
    if wage_delta <= -5_000:  return -1
    return 0
```

**Inputs:** `wage_delta` — salary change when branching to a new career

**Thresholds:**
| Wage Delta | ERN Delta |
|-----------|-----------|
| >= +$20k | +2 |
| >= +$5k | +1 |
| -$5k to +$5k | 0 |
| <= -$5k | -1 |
| <= -$20k | -2 |

This is a delta applied to existing ERN in branch nodes, not an absolute recalculation.

---

### 10. Skill Pool — ERN Delta Application

**File:** `backend/app/services/skill_pool.py:310-322`

**Formula:**
```python
sum_ern = sum(s.delta_ern for s in skills)
ern = clamp(stats.ern + sum_ern, 1, 10) if stats.ern is not None else None
```

**Inputs:**
- `stats.ern` — current ERN (after effort adjustment)
- `skills[].delta_ern` — per-skill integer modifier

**Skills with delta_ern (from skill definitions):**
- `industry_conference`: +1
- `portfolio_project`: +1
- `professional_cert`: +1
- `tech_leadership_course`: +1

---

## Data Flow Summary

```
College Scorecard                BLS OOH
      |                              |
      v                              v
PERCENT_RANK by CIP family    PERCENT_RANK globally
      |                              |
      v                              v
cip_family_earnings_rank       wage_percentile_overall
(0.0-1.0)                     (0.0-1.0)
      |                              |
      +----------+-------------------+
                 |
                 v
   compute_stat_ern(rank, pct)
   = ROUND(1 + 9 * (0.6*rank + 0.4*pct))
                 |
                 v
          stat_ern (1-10)
                 |
     +-----------+-----------+
     |           |           |
     v           v           v
  effort      skill       branch
  shift       deltas      deltas
  (-2..+2)    (+1 each)   (-2..+2)
     |           |           |
     v           v           v
  clamp(1,10) clamp(1,10) applied to
                          branch node
```

---

## Observations

1. **ERN is the only stat with an effort adjustment.** All other pentagon stats pass through unchanged regardless of the effort slider.

2. **No runtime re-derivation.** Unlike ROI (which the backend re-derives from `published_cost_4yr`), ERN is read as-is from Gold and only shifted by effort/skills/branches. The raw percentile inputs are not re-queried at request time.

3. **Consistent across all paths.** The MCP substitution paths (sites #6, #7) use the same `compute_stat_ern` function with the same inputs. No inconsistency found (unlike ROI's `loan_pct` issue in the MCP server).

4. **Both inputs required.** If either `cip_family_earnings_rank` or `wage_percentile_overall` is None, ERN is None. There is no fallback or degraded mode — the program simply lacks an ERN score.

5. **60/40 weighting rationale.** The spec (`docs/specs/completed/gold-futureproof-engine.md:142-156`) explains: 60% weight on school-specific program earnings (what THIS school's graduates earn) vs 40% on occupation-level wages (what this CAREER pays nationally). School choice matters more than occupation average.
