# Boss Ceiling — 15-Year Doubling Formula

**Status:** Implemented
**Supersedes:** Current `boss_ceiling = 10 - 9 * wage_percentile_education_tier` formula in `src/gold/futureproof_engine.py` (~lines 169-180)
**Dependencies:** Stage 3 tree computation (already in PRD v8 scope, F3.2)
**Ties to:** Fight Student Loans 15-year horizon (intentional design coherence — both bosses answer "where are you 15 years after graduation")

---

## Problem

The current ceiling formula measures **headroom within an education tier**, not absolute career altitude. A graduate at the 10th percentile of teachers (career caps around $34k at the top) "wins" the ceiling fight because they have room to grow *within the tier* — but they're growing toward $34k. That's not a meaningful win.

The formula confuses "what's possible" with "is the top worth reaching." Two distinct questions, conflated into one score.

---

## New Formula

The boss now asks: **will you roughly double your starting salary in 15 years, after accounting for inflation?**

This pins the ceiling fight to the same 15-year horizon as Fight Student Loans, making the gauntlet a coherent life-projection rather than five disconnected metrics.

### Constants

```python
COL_GROWTH_RATE = 1.02           # 2% annual real-growth floor
HORIZON_YEARS = 15               # matches loan payoff window
INFLATION_MULTIPLE = COL_GROWTH_RATE ** HORIZON_YEARS  # ≈ 1.346
```

The 2% rate is the Federal Reserve's long-run inflation target — chosen for communication clarity, not measurement. Receipts surface this as an editorial assumption, not data-derived.

### Projection method

```python
starting_wage = career_path.starting_wage_p50
# Sources, in order: Scorecard earnings_1yr_median → OEWS p50 of starting SOC

upward_nodes = [n for n in stage_3_nodes if n.wage > starting_wage]

if len(upward_nodes) == 0:
    year_15_wage = starting_wage    # no upward path
    growth_multiple = 1.0
else:
    year_15_wage = p50(upward_nodes.wage)
    growth_multiple = year_15_wage / starting_wage
```

Filtering to `wage > starting_wage` removes lateral/downward moves from the projection. The boss asks "can you climb," so non-climbing nodes shouldn't count toward the answer. Strict `>` filter (no 0.9x softening) is more defensible for v1.

### Scoring

```python
if growth_multiple < INFLATION_MULTIPLE:
    # Auto-LOSE — career doesn't beat inflation
    boss_ceiling_score = 1
    structural_loss = True
elif growth_multiple < 1.7:
    # LOSE/DRAW band — modest real growth
    boss_ceiling_score = scale(growth_multiple, 1.346, 1.7, 2, 6)
    structural_loss = False
elif growth_multiple < 2.0:
    # WIN band — strong growth
    boss_ceiling_score = scale(growth_multiple, 1.7, 2.0, 6, 9)
    structural_loss = False
else:
    # Maxed out — genuine doubling or better
    boss_ceiling_score = 10
    structural_loss = False
```

Win/draw/lose thresholds stay at 7/5/<5 (unchanged from current `BOSS_SPECS`).

### Fallback chain

1. **No Stage 3 tree:** use OEWS p75 of starting SOC as `year_15_wage` proxy (approximates "experienced practitioner in this role")
2. **No upward nodes:** auto-LOSE, `structural_loss = True`
3. **Starting wage suppressed:** use SOC entry-level wage from OEWS
4. **All sources missing:** score = None, fight result = "unknown" (existing pattern)

The previous fallback to `stat_ern` is **removed** — replaced by the OEWS p75 path.

---

## Narrative metadata exposed to Gemma

| Field | Type | Purpose |
|-------|------|---------|
| `growth_multiple` | float | Headline number for prose |
| `starting_wage` | int | Dollars for narrative |
| `year_15_wage` | int | Dollars for narrative |
| `upward_share` | float | upward_nodes / total Stage 3 nodes; color for "most paths grow" vs "few paths grow" |
| `structural_loss` | bool | Triggers structural loss screen language |
| `inflation_floor_wage` | int | `starting_wage * 1.346`; for prose comparison |

---

## Gemma Surface Updates

Both the **full** (`gemma-4-26b-a4b-it` via OpenRouter) and **compact** (`gemma4:e4b` via Ollama) profiles must understand the new framing. The two system prompts (`_NARRATIVE_SYSTEM` and `_COMPACT_NARRATIVE_SYSTEM`) are deliberately profile-aware and **do not reference any specific boss** — they're general voice/format rules. Ceiling-specific content lives in three shared surfaces called by both `_narrative_prompt()` (full) and `_compact_narrative_prompt()` (compact):

1. `_boss_context()` — data + framing
2. `_boss_instructions()` — what to focus on
3. `_gap_description()` → uses `_BOSS_LEVER_HINT`

Updating these once propagates to both profiles. **Do not introduce separate compact/full ceiling logic.**

### Surfaces to update

| Surface | File | Change |
|---------|------|--------|
| `_boss_context(career, "ceiling")` | `boss_fights.py` ~line 758 | Replace earnings-range logic with 15-year doubling context. Surface `starting_wage`, `year_15_wage`, `growth_multiple`, `inflation_floor_wage`, `upward_share`, `structural_loss` with clear-language framing. |
| `_BOSS_INSTRUCTIONS["ceiling"]` | `boss_fights.py` ~line 868 | Rewrite to focus on 15-year trajectory vs starting salary, not "earnings range." Add structural loss handling instruction. |
| `_BOSS_LEVER_HINT["ceiling"]` | `boss_fights.py` ~line 985 | Rewrite — current text is generic ("advanced credentials, leadership skills"). New version names the actual gap: "growth multiple below 1.35x means inflation outpaces the typical path." |
| `_UNKNOWN_FALLBACKS["ceiling"]` | `boss_fights.py` ~line 1180 | Tweak — current copy says "how high pay can go" which still works, but the new framing is "where pay lands 15 years out." Minor wording update for consistency. |

### Proposed new copy

**`_BOSS_INSTRUCTIONS["ceiling"]`:**

```python
"ceiling": (
    "Explain where pay lands 15 years after graduation compared to "
    "where it starts. Name the actual starting salary and the typical "
    "year-15 salary from the data provided. If the year-15 number "
    "doesn't beat inflation — meaning the student's real buying power "
    "barely changes — say so plainly using the inflation floor figure. "
    "If it roughly doubles, say the real purchasing power genuinely "
    "grows. If most realistic next-step roles stay flat, name that as "
    "the structural problem it is. Do not promise growth that the "
    "data does not show."
),
```

**`_BOSS_LEVER_HINT["ceiling"]`:**

```python
"ceiling": (
    "This score compares the typical year-15 salary to the starting "
    "salary, with a floor for inflation (2% per year, ~1.35x over 15 "
    "years). A low score means the realistic upward paths from this "
    "start either don't go high enough or don't exist. Levers: a "
    "different specialization with stronger upward roles, advanced "
    "credentials that unlock the next tier, or moving into a field "
    "where the typical 15-year path has more headroom. Skills alone "
    "rarely close a structural ceiling — the path itself matters."
),
```

**`_UNKNOWN_FALLBACKS["ceiling"]`:**

```python
"ceiling": (
    "There isn't enough data on where pay lands 15 years into this "
    "career path. When the numbers fill in, this part of your read "
    "will update."
),
```

**`_boss_context()` ceiling branch:**

```python
if boss_id == "ceiling":
    parts = []
    if career.starting_wage is not None:
        parts.append(f"Starting salary: {fmt_dollars(career.starting_wage)}/yr.")
    if career.year_15_wage is not None:
        parts.append(f"Typical salary 15 years in: {fmt_dollars(career.year_15_wage)}/yr.")
    if career.growth_multiple is not None:
        parts.append(
            f"That's a {career.growth_multiple:.2f}x change over 15 years."
        )
    if career.inflation_floor_wage is not None:
        parts.append(
            f"Just to keep pace with inflation (2%/yr), the year-15 salary "
            f"would need to reach {fmt_dollars(career.inflation_floor_wage)}."
        )
    if career.structural_loss:
        parts.append(
            "The typical 15-year path on this career does NOT beat "
            "inflation — this is a structural ceiling, not a tactical gap."
        )
    if career.upward_share is not None:
        if career.upward_share >= 0.7:
            parts.append("Most realistic next-step roles from this start pay more.")
        elif career.upward_share >= 0.3:
            parts.append(
                "Some realistic next-step roles pay more; others stay flat or "
                "drop. The upward paths exist but aren't the default."
            )
        else:
            parts.append(
                "Most realistic next-step roles from this start stay flat or "
                "pay less. Upward paths exist but require deliberate choices."
            )
    if not parts:
        return ""
    return "Ceiling context: " + " ".join(parts)
```

### Profile-specific notes

| Profile | Max tokens | Considerations |
|---------|-----------|----------------|
| `compact_local` (gemma4:e4b) | 400 | Compact prompt builder already trims context — the ceiling block above is short enough to fit. No truncation needed. |
| `full` (gemma-4-26b-a4b-it) | 800 | Full prompt has headroom; `upward_share` nuance lands here best. |

The compact profile's system prompt restricts output to 2 sentences. The new ceiling instructions are compatible — the data block carries the heavy lifting, and Gemma just needs to translate one or two of those facts.

### Test scenarios for both profiles

After implementation, verify with at least these cases on both `compact_local` and `full`:

1. **Strong WIN** — accounting → senior accountant ($52k → $105k, 2.0x). Narrative should name doubling.
2. **Structural LOSE** — elementary teacher → teacher with master's ($44k → $58k, 1.32x). Narrative must say it doesn't beat inflation; should NOT promise growth.
3. **DRAW** — paralegal → senior paralegal ($48k → $72k, 1.50x). Narrative should say modest real growth, not doubling.
4. **No data fallback** — fight result = "unknown". Verify `_UNKNOWN_FALLBACKS["ceiling"]` copy renders, no Gemma call made.

Log `gemma.jsonl` entries for each case and confirm `boss_id: "ceiling"` calls reach both `profile_tier` values during testing.

---

## Receipts provenance

`receipts.py` surfaces this line for the ceiling stat:

> "Inflation floor: 2.0% annual real growth (Federal Reserve long-run target). 15-year compound: 1.346x. Starting wage from [source]. Year-15 projection from p50 of upward Stage 3 career paths."

The 2% is explicitly framed as an editorial assumption with a citation, not as a measurement. Matches governance posture: data validates data; assumptions are labeled.

---

## Edge cases

| Case | Behavior |
|------|----------|
| All Stage 3 nodes below starting wage | Auto-LOSE, `structural_loss = True` |
| Single upward node | Use it directly; flag `confidence = "low"` in narrative metadata |
| Starting wage = 0 or null | Use SOC entry-level wage; if still null, score = None |
| Stage 3 tree exists but empty | Fall back to OEWS p75 path |
| High-variance career (sales, arts) | Score on p50 to stay honest; optionally surface p75 as "upside scenario" in narrative |

---

## Implementation notes

**Touched files:**
- `src/gold/futureproof_engine.py` — replace ceiling formula (~lines 169-180)
- `backend/app/services/boss_fights.py` — update ceiling scorer; update `_boss_context`, `_BOSS_INSTRUCTIONS`, `_BOSS_LEVER_HINT`, `_UNKNOWN_FALLBACKS` for ceiling
- `backend/app/services/stat_engine.py` — wire Stage 3 tree into ceiling computation at request time
- `backend/app/models/career.py` — add `structural_loss`, `growth_multiple`, `year_15_wage`, `starting_wage`, `upward_share`, `inflation_floor_wage` fields to BossFightResult or CareerOutcome
- `frontend/src/components/gauntlet/BossFightCard.tsx` — surface structural loss state for ceiling
- `docs/reports/boss-fights.md` — update Fight the Ceiling section

**Config structure (forward-compatible):**

```python
# config.py or boss_fights.py
INFLATION_CONFIG = {
    "annual_rate": 0.02,
    "horizon_years": 15,
    "source": "Federal Reserve long-run target",
    "source_url": "https://www.federalreserve.gov/monetarypolicy/review-of-monetary-policy-strategy-tools-and-communications-statement-on-longer-run-goals-monetary-policy-strategy.htm",
}
```

If CPI ingestion is added post-hackathon, this config becomes the swap point — no formula changes needed.

---

## Why this is better than the current formula

| Aspect | Current (wage_percentile_education_tier) | New (15-year doubling) |
|--------|-----------------------------------------|------------------------|
| Measures | Headroom within tier | Absolute real-wage growth |
| $34k cap → "WIN" bug | Yes | No (auto-LOSE if cap < inflation floor) |
| Punishes high starters | Yes (doctors "lose" the ceiling fight) | No (uses growth, not percentile) |
| Uses branch tree | No | Yes |
| Duplicates ERN | Partial — both measure earnings | No — ERN is altitude now, ceiling is trajectory |
| Narrative quality | "Your range is narrow" | "$52k → $105k over 15 years, real doubling" |
| Ties to other bosses | None | Shared 15-year horizon with Fight Student Loans |

---

## Post-hackathon

- **CPI ingestion:** add BLS CPI-U pipeline (`CUUR0000SA0`) to replace the 2% constant with trailing 10-year average. Swap point already in config.
- **Regional inflation:** BLS publishes CPI by metro area. Could regionalize the inflation floor for students in high-cost vs low-cost markets.
- **Confidence tagging:** if tree has only 1-2 upward nodes, the p50 is noisy. Surface `confidence = "low"` and let Gemma soften the prose.
- **ERN stat refresh:** with ceiling now measuring trajectory, the `stat_explainer()` ERN line could be tightened to clarify altitude-only framing. Out of scope for this spec.
