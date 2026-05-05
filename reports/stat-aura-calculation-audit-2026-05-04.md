# AURA (Brand Gravity) Stat — Complete Calculation Inventory

**Date:** 2026-05-04
**Purpose:** Identify every location where AURA is calculated, with inputs and formula for each.

---

## Canonical Formula

**File:** `src/gold/institution_aura.py:273-304`

AURA is a multi-step computation:

### Step 1: Percent-Rank Each Signal

**File:** `src/gold/institution_aura.py:195-235`

```python
rp_marketing = PERCENT_RANK(marketing_ratio)     # across all institutions
rp_endowment = PERCENT_RANK(endowment_per_fte)   # across all institutions
rp_athletic  = PERCENT_RANK(athletic_spend_per_fte)  # across all institutions
```

Each signal is independently ranked against the full population. Null signals are excluded from ranking.

### Step 2: Determine Basis

**File:** `src/gold/institution_aura.py:238-270`

```python
def determine_basis(rp_marketing, rp_endowment, rp_athletic):
    if all three non-null:  return "three_term"
    if mkt + endow only:    return "two_term_finance_only"
    if mkt + ath only:      return "two_term_no_endowment"
    if mkt only:            return "one_term_marketing_only"
    else:                   return None  # → aura_score = None
```

### Step 3: Raw Score (MAX + MEAN)

**File:** `src/gold/institution_aura.py:273-287`

```python
def compute_raw_score(rp_marketing, rp_endowment, rp_athletic):
    available = [v for v in (rp_marketing, rp_endowment, rp_athletic) if v is not None]
    if not available:
        return None
    return 0.65 * max(available) + 0.35 * mean(available)
```

**Formula:**
```
raw_score = 0.65 × MAX(available_percentile_ranks) + 0.35 × MEAN(available_percentile_ranks)
```

Null signals are excluded from both MAX and MEAN — not imputed.

### Step 4: P5/P95 Rescale to 1-10

**File:** `src/gold/institution_aura.py:290-304`

```python
def rescale_aura(raw_score):
    span = 0.9400 - 0.1413  # P95 - P5
    t = (raw_score - 0.1413) / span
    t_clipped = max(0.0, min(1.0, t))
    aura_continuous = 1.0 + 9.0 * t_clipped
    return aura_continuous, round(aura_continuous)  # banker's rounding here
```

**Constants (EDA-pinned, lines 96-107):**
- `WEIGHT_MAX = 0.65`
- `WEIGHT_MEAN = 0.35`
- `RAW_SCORE_P5 = 0.1413`
- `RAW_SCORE_P95 = 0.9400`
- `AURA_SCORE_VERSION = "v1"`

---

## Calculation Sites

### 1. Gold Pipeline — Full AURA Computation

**File:** `src/gold/institution_aura.py:423-470` (`compute_aura_columns()`)

Orchestrates the full pipeline for each institution:
1. Compute percent_rank for each signal across full population
2. Determine basis
3. Compute raw_score (MAX+MEAN blend)
4. Rescale via P5/P95 bounds

**Inputs:**

| Signal | Source | Meaning |
|--------|--------|---------|
| `marketing_ratio` | `base.ipeds_finance` | Marketing spend / instruction spend |
| `endowment_per_fte` | `base.ipeds_finance` | Endowment / FTE enrollment |
| `athletic_spend_per_fte` | `base.eada` | Total athletic expenses / FTE |

**FTE source (hybrid):**
```python
total_fte = COALESCE(ipeds_finance.total_fte_enrollment, eada.eada_fte_headcount)
```
~74.5% use IPEDS Finance FTE, ~25.5% fall back to EADA headcount.

**Outputs:**
- `aura_score` (integer 1-10 or None)
- `aura_score_continuous` (float, for audit/receipts)
- `aura_score_basis` (enum string or None)
- `aura_score_version` ("v1")

**Stored in:** `consumable.institution_aura` (~3,223 rows, grain: UNITID)

---

### 2. Backend — Runtime Fetch (One Per Build)

**File:** `backend/app/services/stat_engine.py:70-101`

```python
def _fetch_aura(unitid: int) -> tuple[int | None, str | None, str | None]:
    result = mcp_client.call("get_institution_aura", {"unitid": unitid})
    row = result.get("data")
    return (
        as_int(row.get("aura_score")),
        row.get("aura_score_basis"),
        row.get("aura_score_version"),
    )
```

**Key behaviors:**
- Called **once per build** — institution-level, same value for all career outcomes
- Fails soft — logs warning, returns `(None, None, None)` on MCP failure
- Does NOT cascade to HTTP 500 — AURA is supplementary

---

### 3. Backend — Pentagon Assignment

**File:** `backend/app/services/stat_engine.py:416-421`

```python
stats = PentagonStats(
    ern=...,
    roi=...,
    res=...,
    grw=...,
    aura=aura_score,  # from _fetch_aura, same for all rows
)
```

AURA is stamped identically on every `CareerOutcome` for a given build. No per-occupation variation.

---

### 4. Backend — No Effort/Slider/Delta Modification

AURA is the only pentagon stat that is **completely immutable at runtime:**

- **No effort adjustment** — only ERN shifts with effort (stat_engine.py:103-108)
- **No skill deltas** — `delta_aura` is always 0 per pentagon-stat-reshape Decision 5
- **No branch deltas** — AURA is institution-level; branching to a different career doesn't change the school
- **No slider impact** — excluded from `/rescore` endpoint logic
- **No boss fight** — AURA does not power any boss (stat_engine.py:79 comment: "does not drive any boss fight scoring")

---

### 5. MCP Server — Tool Handler

**File:** `src/mcp_server/futureproof_server.py:1435-1474`

```python
def _handle_get_institution_aura(self, input_dict: dict) -> dict:
    # Queries consumable.institution_aura by unitid
    # Returns full row with aura_score, aura_score_basis, aura_score_version
```

**Tool:** `get_institution_aura({"unitid": <int>})`
Returns the institution row intact, including None for schools without coverage.

---

### 6. Backend — Receipt/Explain-Stat Rendering

**File:** `backend/app/services/ask_gemma.py` (lines ~466-600)

**Basis-to-signals mapping:**
```python
_AURA_BASIS_SIGNALS = {
    "three_term": ["endowment_per_fte", "marketing_ratio", "athletic_spend_per_fte"],
    "two_term_finance_only": ["endowment_per_fte", "marketing_ratio"],
    "two_term_no_endowment": ["marketing_ratio", "athletic_spend_per_fte"],
    "one_term_marketing_only": ["marketing_ratio"],
}
```

**Math line:** `"MAX-MEAN blend of {n} signals → composite {continuous:.2f} → AURA score {score}/10"`

**Evidence bullets show actual values:**
- "Marketing: 0.042 ratio — how much the school spends getting its name out"
- "Endowment: $X/student — accumulated wealth backing the school"
- "Athletics: $X/student — visibility investment through sports"

---

### 7. Backend — Receipts (Basis Humanization)

**File:** `backend/app/services/receipts.py:225-260`

```python
_BASIS_HUMAN = {
    "three_term": "endowment + marketing + athletics",
    "two_term_finance_only": "endowment + marketing (no athletics signal)",
    "two_term_no_endowment": "marketing + athletics (no endowment signal)",
    "one_term_marketing_only": "marketing reach only",
}
```

Renders as: `"AURA 8/10 ← endowment + marketing + athletics (institution-level)"`

---

## `aura_score_basis` Enum

| Basis | Signals Used | Typical Institutions |
|-------|-------------|---------------------|
| `three_term` | marketing + endowment + athletics | Major universities with full IPEDS + EADA coverage |
| `two_term_finance_only` | marketing + endowment | ~1,183 schools without EADA athletics data |
| `two_term_no_endowment` | marketing + athletics | ~75 schools missing endowment data |
| `one_term_marketing_only` | marketing only | ~602 schools (mostly for-profits) |
| `NULL` | none | ~579 schools (no marketing_ratio signal) → aura_score = NULL |

**Rule:** `aura_score IS NULL ⟺ aura_score_basis IS NULL`

---

## Data Flow Summary

```
IPEDS Finance                    EADA (Athletics)
     |                                |
     v                                v
marketing_ratio              athletic_spend_per_fte
endowment_per_fte
     |                                |
     +---------------+----------------+
                     |
                     v
         PERCENT_RANK each signal
         (across full population)
                     |
                     v
         determine_basis (which signals available?)
                     |
                     v
         raw_score = 0.65 × MAX(rp_*) + 0.35 × MEAN(rp_*)
                     |
                     v
         rescale: P5/P95 clip → 1 + 9 × t
                     |
                     v
         aura_score (int, 1-10)
                     |
                     v
         consumable.institution_aura (UNITID grain)
                     |
                     v
         _fetch_aura(unitid) — once per build
                     |
                     v
         stamped on ALL CareerOutcome rows for that build
                     |
                     v
         Pentagon vertex (immutable — no deltas, no effort, no boss)
```

---

## Observations

1. **Institution-level, not occupation-level.** AURA is the only pentagon stat that doesn't vary by career choice. All career outcomes for a school share the same AURA. This is by design — it measures the school's brand power, not the career's attributes.

2. **Completely immutable at runtime.** No effort shift, no skill delta, no branch delta, no slider impact. Once computed in the Gold pipeline, AURA never changes for a given build.

3. **No boss fight.** AURA is purely informational — it shows up on the pentagon but doesn't drive any boss fight scoring. Comment at line 79: "AURA is supplementary... does not drive any boss fight scoring."

4. **Fails soft.** If the MCP call fails, AURA degrades to None gracefully. The pentagon renders a missing-data treatment (open ring), and the build still completes.

5. **v1 replaced v0-draft.** The v0-draft formula (0.40/0.40/0.20 fixed weights, min/max rescale) failed 11/14 anchor school validations. v1 (0.65 MAX + 0.35 MEAN, P5/P95 rescale) passes all 13 anchors.

6. **Partial-signal graceful degradation.** Schools with fewer available signals still get an AURA score — just from fewer inputs. Only schools completely lacking `marketing_ratio` get NULL. The MAX+MEAN formula naturally adapts to however many signals are available.

7. **~10% of institutions have no AURA.** 579 schools (mostly 2-year colleges without IPEDS Finance coverage) get NULL. Rendered as "no brand-gravity data for this school yet."
