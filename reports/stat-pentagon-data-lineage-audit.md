# Stat Pentagon Data Lineage Audit

**Audit date:** 2026-04-28
**Scope:** Trace every value in the FutureProof stat pentagon (ERN, ROI, RES, GRW, HMN) from the rendered SVG axis back through the API contract, gold formulas, silver transformers, and finally to the bronze ingestor + upstream URL.

This is a code audit. Every formula in this report is transcribed verbatim from source with file/line citations. No measurements were taken from the live database — DuckDB row counts and distribution checks are out of scope.

---

## 1. Executive Summary

### In plain language

The pentagon is a five-axis radar chart shown after a student picks a school and major. Each axis answers one question about the future this degree leads to:

- **ERN — Earning Power.** Will I make good money?
- **ROI — Return on Investment.** Is this degree worth what it costs?
- **RES — AI Resilience.** Will AI take this job?
- **GRW — Growth Outlook.** Will this field still be hiring in 10 years?
- **HMN — Human Edge.** Is this work fundamentally human, or could software eventually do it?

Every value is on a **1–10 scale where higher is always better for the student**. A perfect pentagon would be all 10s — high pay, low cost, AI-proof, growing field, deeply human work. A score of `null` means the underlying data was missing (small programs, rare occupations); the axis just doesn't render.

### The numbers behind it

The pentagon has five axes, each scored 1–10 (or `null` when source data is absent). Four are computed at the gold layer and threaded into `consumable.program_career_paths`; one (ROI) is recomputed in the backend when residency or financing inputs change.

| Stat | Measures | Score range | Computed in | Primary source |
|------|----------|------------|-------------|----------------|
| **ERN** | Earning Power | 1–10 | `src/gold/futureproof_engine.py:77-89` | College Scorecard (program earnings) + BLS OOH (occupation wages) |
| **ROI** | Return on Investment | 1–10 | `src/gold/futureproof_engine.py:92-115`, recomputed in `backend/app/services/stat_engine.py:67-88` | College Scorecard (institution net price + program earnings) |
| **RES** | AI Resilience | 1–10 | `src/gold/ai_exposure_transformer.py:286-296` | Gemma 4 task scoring + Karpathy fallback + Anthropic Economic Index |
| **GRW** | Growth Outlook | 1–10 | `src/gold/bls_ooh_occupation_profiles.py:67-96` | BLS Occupational Outlook Handbook |
| **HMN** | Human Edge | 1–10 | `src/gold/onet_work_profiles.py:146-330` | O*NET Work Activities |

**Quick lineage**

| Stat | Frontend | Backend field | Gold table.column | Silver source | Bronze source | Upstream URL |
|------|----------|---------------|-------------------|---------------|---------------|--------------|
| ERN | `PentagonChart.tsx:23` | `PentagonStats.ern` | `consumable.program_career_paths.stat_ern` | `base.college_scorecard`, `base.bls_ooh` | `bronze.college_scorecard`, `bronze.bls_ooh` | `ed-public-download.app.cloud.gov/.../Most-Recent-Cohorts-Field-of-Study.csv` + `bls.gov/emp/tables/occupational-projections-and-characteristics.htm` |
| ROI | `PentagonChart.tsx:24` | `PentagonStats.roi` | `consumable.program_career_paths.stat_roi` | `base.college_scorecard`, `base.college_scorecard_institution` | `bronze.college_scorecard`, `bronze.college_scorecard_institution` | `ed-public-download.app.cloud.gov/.../Most-Recent-Cohorts-Field-of-Study.csv` + `Most-Recent-Cohorts-Institution.csv` |
| RES | `PentagonChart.tsx:25` | `PentagonStats.res` | `consumable.ai_exposure.stat_res` (joined into `program_career_paths`) | `base.gemma_ai_exposure`, `base.karpathy_ai_exposure`, `base.anthropic_economic_index` | `bronze.karpathy_ai_exposure`, `bronze.anthropic_economic_index` (Gemma is computed locally, no bronze ingestor) | `raw.githubusercontent.com/karpathy/jobs/.../scores.json` + `huggingface.co/datasets/Anthropic/EconomicIndex` |
| GRW | `PentagonChart.tsx:26` | `PentagonStats.grw` | `consumable.occupation_profiles.grw_score_rounded` (joined into `program_career_paths`) | `base.bls_ooh` | `bronze.bls_ooh` | `bls.gov/emp/tables/occupational-projections-and-characteristics.htm` |
| HMN | `PentagonChart.tsx:27` | `PentagonStats.hmn` | `consumable.onet_work_profiles.hmn_score_rounded` (joined into `program_career_paths`) | `base.onet_occupations`, `base.onet_activity_profiles` | `bronze.onet_work_activities`, `bronze.onet_task_statements` | `onetcenter.org/dl_files/database/db_30_2_text.zip` |

**The CIP-SOC crosswalk** (`bronze.cip_soc_crosswalk` ← `nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx`) is the connective tissue that lets program-level stats (ERN, ROI) live alongside occupation-level stats (RES, GRW, HMN) in a single row of `program_career_paths`.

---

## 2. The Five Stats

Each subsection follows the same template: definition → frontend → backend → MCP → gold formula → gold inputs → silver source → bronze source → edge cases.

### 2.1 ERN — Earning Power

**In plain language.** How much money this degree leads to. We combine two numbers: what graduates of *this exact program at this exact school* earned one year out (60% weight), and what people in the *career field as a whole* earn (40% weight). The program-specific number gets more weight because what your school + major actually produced beats a generic occupation average. ERN is a **percentile** rank — a 7 roughly means "earnings beat 60–70% of comparable programs/occupations," not "made $70k."

**Definition.** A blended 1–10 percentile-based score combining program-level earnings (60% weight, ranked within CIP family) with occupation-level wages (40% weight, ranked across all SOCs).

**Frontend.**
- Axis declaration: `frontend/src/components/PentagonChart.tsx:23`
- Type contract: `frontend/src/types/build.ts:7` (`ern: number | null`)
- Stat tooltip / explanation copy: `frontend/src/data/statExplanations.ts:24-36`

**Backend model.**
- `backend/app/models/career.py:59` — `PentagonStats.ern: int | None`

**Backend post-gold adjustment.**
- `backend/app/services/stat_engine.py:38-44, 53-64, 263` — the **effort slider** shifts ERN by `−2` (`working_hard`) up to `+2` (`all_in`). Result is clamped to [1, 10] (`_clamp_stat`). ROI is intentionally not adjusted (line 34 comment: "effort reflects earning potential while in school, not debt load").

**MCP server.** Pure passthrough. `src/mcp_server/futureproof_server.py:172` declares `stat_ern` in the response field allow-list. No reshape.

**Gold formula.** `src/gold/futureproof_engine.py:77-89`:
```python
def compute_stat_ern(cip_family_earnings_rank, wage_percentile_overall):
    if cip_family_earnings_rank is None or wage_percentile_overall is None:
        return None
    raw = 0.6 * cip_family_earnings_rank + 0.4 * wage_percentile_overall
    return _round_half_up(1.0 + 9.0 * raw)
```
- Both inputs are `[0, 1]` percentile ranks. Raw is therefore `[0, 1]` and the output is round-half-up to integer in `[1, 10]`.
- `_round_half_up` (line 66) matches DuckDB rounding (so 2.5 → 3, not banker's-rounded 2).
- Called in the gold join at `src/gold/futureproof_engine.py:467-470` as part of `derive_pcp_rows`.

**Gold inputs.**

| Input | From | Computed by |
|-------|------|-------------|
| `cip_family_earnings_rank` | `consumable.career_outcomes` (col 24) | `src/gold/college_scorecard_career_outcomes.py:218-227` — `PERCENT_RANK() OVER (PARTITION BY cip_family ORDER BY earnings_1yr_median)` over rows where `earnings_1yr_median IS NOT NULL` |
| `wage_percentile_overall` | `consumable.occupation_profiles` (col 17) | `src/gold/bls_ooh_occupation_profiles.py:179-186` — `PERCENT_RANK() OVER (ORDER BY median_annual_wage)` over rows where `median_annual_wage IS NOT NULL`. **CRITICAL** comment at line 148-150 warns nulls must be excluded or DuckDB places them at ~0.185 and corrupts the ranking. |

**Silver sources.**

| Silver column | Silver table | Transformer |
|---------------|--------------|-------------|
| `earnings_1yr_median` | `base.college_scorecard` | `src/silver/college_scorecard_transformer.py` — passthrough of `MD_EARN_WNE` / `EARN_MDN_HI_1YR` after sentinel-to-null coercion |
| `cip_family` | `base.college_scorecard` | Derived in transformer: first 2 digits of CIPCODE → CIP 2020 family name (54-family hardcoded dict) |
| `median_annual_wage` | `base.bls_ooh` | `src/silver/bls_ooh_transformer.py` — passthrough; top-coded "≥239,200" rows are flagged `median_wage_capped=true` and surfaced as 239200.0 |

**Bronze sources.**

| Bronze table | Ingestor | Upstream URL | Format |
|--------------|----------|--------------|--------|
| `bronze.college_scorecard` | `src/raw/college_scorecard_ingestor.py` | Primary: `https://ed-public-download.app.cloud.gov/downloads/Most-Recent-Cohorts-Field-of-Study.csv` · Fallback: `https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Field-of-Study_04172025.zip` | CSV (~174 cols, ~500MB uncompressed) |
| `bronze.bls_ooh` | `src/raw/bls_ooh_ingestor.py` | `https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm` (HTML page with dynamic XLSX link); fallback: `data/raw/xlsx_cache/bls_ooh.xlsx` | XLSX |

**Edge cases / caveats.**
- ERN is `None` if either input is `None`. A program with earnings but no SOC match (or vice versa) drops to four stats on the pentagon.
- The `60/40` blend is fixed in code; there is no config flag.
- `earnings_1yr_median` in College Scorecard is suppressed for small cohorts (<30 completions) and arrives as the sentinel `"PrivacySuppressed"`, which the bronze ingestor coerces to `NULL`. Such rows still flow through but contribute neither to the percentile rank nor to a program's ERN.
- The percentile rank is recomputed from scratch on every gold promote — adding/removing schools or majors shifts every program's ERN.

---

### 2.2 ROI — Return on Investment

**In plain language.** Whether the price tag of this degree is reasonable given what graduates earn. We take the **4-year cost of attendance** and divide by **first-year earnings**. If 4 years of school costs about half of what you'll make in your first year (ratio 0.5), that's a great deal — score 9. If it costs roughly the same as one year's earnings (ratio 1.0), it's mediocre — score 5. If it costs 2× a year's earnings, that's bad — score 2. Loans, financial aid percentages, and how the student plans to pay are **deliberately not part of ROI** — that's the separate Loans Boss fight. ROI asks "is the *program* a good economic deal?", not "can this student afford it?"

**Definition.** A 1–10 piecewise-linear score derived from the debt-to-earnings ratio (DTE). Lower DTE → higher score. Lower-bound clamp at DTE ≤ 0.25 (score 10); upper-bound clamp at DTE ≥ 2.5 (score 1).

**Frontend.**
- Axis declaration: `frontend/src/components/PentagonChart.tsx:24`
- Type contract: `frontend/src/types/build.ts:8`; cost-of-attendance fields and ROI provenance docs `frontend/src/types/build.ts:31-66`

**Backend model.**
- `backend/app/models/career.py:60` — `PentagonStats.roi: int | None`
- ROI provenance fields: `backend/app/models/career.py:142-153` — `roi_cost_basis: 'cost_of_attendance' | 'debt_median' | 'none'` and `financed_dte`

**Backend post-gold adjustment.** This is the most-modified pentagon stat after gold:

1. **Residency adjustment** (`backend/app/services/stat_engine.py:151-173, 213-220`): if the student's `home_state ≠ school_state` and the school is `Public`, add `(tuition_out_of_state − tuition_in_state)` to `net_price_annual`.
2. **DTE recomputation** (`stat_engine.py:225-233`): if residency changed `net_price`, recompute `roi_dte = (adjusted_net_price × 4) / earnings_1yr_median`.
3. **ROI re-derivation** (`stat_engine.py:67-88, 236-239`): call `compute_stat_roi(roi_dte)` from the gold module. Falls back to the row's pre-baked `stat_roi` if `roi_dte` is null (e.g., substitution-path occupation-only rows).
4. **No effort shift** (`stat_engine.py:34-37, 60`): comment is explicit — "A student studying harder doesn't reduce the tuition bill."

**MCP server.** Pure passthrough — `src/mcp_server/futureproof_server.py:173`.

**Gold formula.** `src/gold/futureproof_engine.py:55-115`:
```python
ROI_BREAKPOINTS = [
    (0.25, 0.50, 10.0, 9.0),  # excellent
    (0.50, 0.75, 9.0, 7.0),   # good
    (0.75, 1.00, 7.0, 5.0),   # mediocre
    (1.00, 1.50, 5.0, 3.0),   # bad — debt exceeds annual earnings
    (1.50, 2.50, 3.0, 1.0),   # terrible
]

def compute_stat_roi(debt_to_earnings_annual):
    if debt_to_earnings_annual is None:
        return None
    dte = debt_to_earnings_annual
    if dte <= 0.25:
        return 10
    for dte_lo, dte_hi, roi_lo, roi_hi in ROI_BREAKPOINTS:
        if dte <= dte_hi:
            fraction = (dte - dte_lo) / (dte_hi - dte_lo)
            return _round_half_up(roi_lo + fraction * (roi_hi - roi_lo))
    return 1
```
Mapping summary:

| DTE range | ROI |
|-----------|-----|
| ≤ 0.25 | 10 |
| 0.25 → 0.50 | 10 → 9 (linear) |
| 0.50 → 0.75 | 9 → 7 |
| 0.75 → 1.00 | 7 → 5 |
| 1.00 → 1.50 | 5 → 3 |
| 1.50 → 2.50 | 3 → 1 |
| ≥ 2.50 | 1 |

**Gold inputs.** The crucial input is `debt_to_earnings_annual`, computed in `src/gold/college_scorecard_career_outcomes.py:248-270`:
```sql
debt_to_earnings_annual = CASE
    WHEN earnings_1yr_median IS NULL THEN NULL
    WHEN net_price_annual IS NOT NULL
        THEN (net_price_annual * 4.0) / earnings_1yr_median
    WHEN debt_median IS NOT NULL
        THEN debt_median / earnings_1yr_median
    ELSE NULL
END

roi_cost_basis = CASE
    WHEN earnings_1yr_median IS NULL THEN 'none'
    WHEN net_price_annual IS NOT NULL THEN 'cost_of_attendance'
    WHEN debt_median IS NOT NULL THEN 'debt_median'
    ELSE 'none'
END
```
- **Numerator priority:** `net_price_annual × 4` (preferred, cost basis) → `debt_median` (legacy fallback).
- **Denominator:** `earnings_1yr_median`.
- The `roi_cost_basis` provenance string is carried all the way to the API so receipts can render "ROI based on 4-year cost of attendance" vs. "based on median actual debt."
- This change ("cost-based ROI") is documented in `~/.claude/plans/why-are-we-still-jaunty-curry.md` (referenced from `backend/app/models/career.py:31-46`).

**Silver sources.**

| Silver column | Silver table | Transformer |
|---------------|--------------|-------------|
| `net_price_annual` | `base.college_scorecard_institution` | `src/silver/college_scorecard_institution_transformer.py` — control-based unification: `CONTROL=1` → `NPT4_PUB`, else `NPT4_PRIV` |
| `debt_median` | `base.college_scorecard` | `src/silver/college_scorecard_transformer.py` — passthrough of `DEBT_ALL_STGP_EVAL_MDN` |
| `earnings_1yr_median` | `base.college_scorecard` | passthrough of `MD_EARN_WNE` / `EARN_MDN_HI_1YR` |

**Bronze sources.**

| Bronze table | Ingestor | Upstream URL |
|--------------|----------|--------------|
| `bronze.college_scorecard` | `src/raw/college_scorecard_ingestor.py` | (same as ERN row above) |
| `bronze.college_scorecard_institution` | `src/raw/college_scorecard_institution_ingestor.py` | Primary: `https://ed-public-download.app.cloud.gov/downloads/Most-Recent-Cohorts-Institution.csv` · Fallback: `https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Institution_04172025.zip` |

The institution file is `~1,900` columns; the ingestor selects ~28 cost-relevant fields (COSTT4_A, COSTT4_P, NPT4_PUB, NPT4_PRIV, NPT41_PUB–NPT45_PUB, TUITIONFEE_IN, TUITIONFEE_OUT, ROOMBOARD_ON, ROOMBOARD_OFF, BOOKSUPPLY).

**Edge cases / caveats.**
- ROI is `None` when both `net_price_annual` and `debt_median` are null, or when `earnings_1yr_median` is null. The `roi_cost_basis` field surfaces which numerator fired (`'cost_of_attendance'`, `'debt_median'`, `'none'`).
- The Loans Boss is a *separate*, financing-aware computation (`stat_engine.py:91-148`): `boss_loans = 11 − compute_stat_roi(financed_dte)` where `financed_dte = (cost_per_year × 4 × loan_pct) / earnings`. This is the only place the `loan_pct` knob is read for the pentagon row; ROI itself is loan_pct-independent.
- Out-of-state students at public schools get a residency surcharge: `net_price + (tuition_out − tuition_in)` (`stat_engine.py:151-173`).

---

### 2.3 RES — AI Resilience

**In plain language.** How safe this career is from being automated by AI — higher means safer. We blend three signals:

1. **Gemma 4 reads each task** the occupation does (per O*NET) and judges how automatable it is.
2. **Karpathy's manual scores** act as a second opinion / baseline — they cover ~342 occupations he hand-rated.
3. **Anthropic's Economic Index** tells us what people *actually* use Claude for. If real-world Claude usage already touches an occupation a lot, we trust the AI signal more. If barely anyone uses Claude for it yet, we lean harder on Karpathy's baseline.

A 10 means "AI struggles to replace this work, even hypothetically." A 1 means "AI does most of this already." The `composite_method` field on each row tells you which signals were available — `gemma_only` is rougher than `three_signal` because we have less corroboration. RES is the only stat that uses Gemma's local inference; everything else is pure data joins.

**Definition.** A 1–10 score derived as `MIN(11 − composite_exposure, 10)`, where `composite_exposure` is a confidence-weighted blend of Gemma 4 theoretical task scores, Karpathy's manual baseline, and (when available) Anthropic Economic Index real-world adoption.

**Frontend.**
- Axis declaration: `frontend/src/components/PentagonChart.tsx:25`
- Type contract: `frontend/src/types/build.ts:9`
- Stat explanation: `frontend/src/data/statExplanations.ts:51-62`

**Backend model.**
- `backend/app/models/career.py:61` — `PentagonStats.res: int | None`
- AI provenance fields: `backend/app/models/career.py:119-140` — `scoring_model`, `model_tag`, `karpathy_score`, `task_breakdown_automatable`, `task_breakdown_human`, `ai_adoption_share`, `adoption_percentile`, `velocity_label`, `composite_method`

**Backend post-gold adjustment.** None. RES is read straight from the row.

**MCP server.** Passthrough — `src/mcp_server/futureproof_server.py:174`. The MCP server also surfaces composite-method provenance fields (lines 216-219) and Gemma's per-task breakdown (`task_breakdown_automatable`, `task_breakdown_human`) for the Fight AI narrative — these are JSON-decoded at line 43-57 but the numeric stat is not modified.

**Gold formula.** Two-step, both in `src/gold/ai_exposure_transformer.py`:

**Step 1 — composite_exposure** (`compute_composite`, lines 206-283):
```python
if adoption_percentile is not None:
    confidence = max(0.3, min(1.0, 0.3 + 0.7 * adoption_percentile / 100.0))
    velocity = velocity_from_percentile(adoption_percentile)
else:
    confidence = 0.5
    velocity = "unknown"

# Method routing
if theoretical is None and baseline is None:    return None,           method='no_data'
if theoretical is None:                          return baseline,       method='karpathy_only'
if baseline is None:                             return theoretical,    method='gemma_only' or 'gemma_plus_anthropic'
if theoretical == 0 and ai_adoption_share > 0:   return baseline*conf,  method='observed_override'
# Regular blend:
composite = confidence * theoretical + (1.0 - confidence) * baseline
method = 'three_signal' if ai_adoption_share is not None else 'two_signal_no_anthropic'
```
Composite is clamped to `[0, 10]` and rounded.

**Step 2 — stat_res** (`derive_stats`, lines 286-296):
```python
def derive_stats(composite_exposure):
    if composite_exposure is None:
        return None, None
    return min(11 - composite_exposure, 10), max(composite_exposure, 1)
    # returns (stat_res, boss_ai_score)
```

So a SOC with composite_exposure=0 → RES=10 (capped), and composite_exposure=10 → RES=1.

**Velocity label** (lines 193-203, used by narrative copy not the stat itself):
- ≥90 percentile → `saturating`
- ≥70 → `accelerating`
- ≥40 → `emerging`
- < 40 → `nascent`
- null → `unknown`

**Composite method** ends up in `composite_method` field surfaced through `program_career_paths` (`src/gold/futureproof_engine.py:489`):
- `three_signal` — Gemma + Karpathy + Anthropic adoption
- `two_signal_no_anthropic` — Gemma + Karpathy
- `gemma_plus_anthropic` — Gemma + Anthropic (no Karpathy)
- `gemma_only` — Gemma only
- `karpathy_only` — Karpathy only (Gemma missing or errored)
- `observed_override` — Gemma said 0 but Anthropic shows real-world usage
- `no_data` — neither signal

**Gold inputs.**

| Input | Source | Notes |
|-------|--------|-------|
| `gemma_score` (theoretical) | `base.gemma_ai_exposure` | Gemma 4 task-level scoring; ~798 SOCs covered when promoted (rows with `error != null` are treated as missing and fall through to Karpathy) |
| `karpathy_score` (baseline) | `base.karpathy_ai_exposure` | Karpathy's manual 0–10 score; ~342 SOCs in source, ~400–500 after Silver expansion |
| `ai_adoption_share` | `base.anthropic_economic_index` | SUM of `task_pct` across tasks mapped to that SOC (share of Claude conversations involving the occupation's tasks) |
| `adoption_percentile` | Computed in gold | `percent_rank` of `ai_adoption_share` across all SOCs (lines 173-190) |

**Silver sources.**

| Silver column | Silver table | Transformer |
|---------------|--------------|-------------|
| Gemma scores | `base.gemma_ai_exposure` | `src/silver/gemma_ai_exposure_transformer.py` — wraps the local Gemma scoring run, no upstream URL |
| Karpathy scores | `base.karpathy_ai_exposure` | `src/silver/karpathy_ai_exposure_transformer.py` — normalizes SOC codes, resolves null SOCs via title-match against `base.bls_ooh`, expands broad SOCs (XX-XXX0) to detailed codes, dedupes by `num_jobs_2024` |
| Anthropic adoption | `base.anthropic_economic_index` | `src/silver/anthropic_observed_exposure_transformer.py` — aggregates per-SOC `SUM(task_pct)`, collapses 5-axis automation breakdown to `automation_pct` (directive + feedback_loop) and `augmentation_pct` (task_iteration + validation + learning) |

**Bronze sources.**

| Bronze table | Ingestor | Upstream | Format |
|--------------|----------|----------|--------|
| `bronze.karpathy_ai_exposure` | `src/raw/karpathy_ai_exposure_ingestor.py` | `https://raw.githubusercontent.com/karpathy/jobs/master/scores.json` joined to `https://raw.githubusercontent.com/karpathy/jobs/master/occupations.csv` on `slug` | JSON + CSV (342 rows) |
| `bronze.anthropic_economic_index` | `src/raw/anthropic_economic_index_ingestor.py` | `https://huggingface.co/datasets/Anthropic/EconomicIndex` (HuggingFace dataset, cloned via git lfs to `data/raw/anthropic_economic_index/`); release preference order: `release_2026_03_24`, `release_2026_01_15`, `release_2025_03_27` | Three CSVs per release: `task_pct_v2.csv`, `automation_vs_augmentation_by_task.csv`, `onet_task_statements.csv` |
| Gemma scores | (no bronze ingestor) | Computed locally by Gemma 4 via Ollama or OpenRouter (see `INFERENCE_BACKEND` in `.env`); persisted directly to silver | JSONL of model outputs |

**Edge cases / caveats.**
- Confidence is bounded to `[0.3, 1.0]` even when `adoption_percentile` is 0 — the formula `max(0.3, min(1.0, 0.3 + 0.7 × p/100))` ensures Gemma always carries at least 30% weight.
- Gemma scoring runs are reproducible only at the level of the `model_tag` field — different Ollama tags or quantizations will produce different scores for the same SOC.
- Anthropic data is multi-release: the ingestor walks a hardcoded preference list and emits the first present release (release fingerprint stored in `anthropic_source_release`).
- `composite_method='no_data'` rows are pruned from `consumable.ai_exposure` (their `stat_res` would be null), so they simply don't appear in the lookup that feeds `program_career_paths`. The PCP row gets `stat_res=None`.

---

### 2.4 GRW — Growth Outlook

**In plain language.** Will this career still be hiring 10 years from now? The U.S. Bureau of Labor Statistics projects, occupation by occupation, how much employment will grow or shrink over a 10-year window. We take that single percentage and map it to a 1–10 score. A 10 means BLS projects >20% growth (booming field, lots of openings); a 5 means roughly flat (stable, replacement hiring only); a 1 means >20% decline (occupation is shrinking — fewer jobs every year). This is a **single-source signal** — if the BLS projection is wrong, GRW is wrong, and there's no second opinion.

**Definition.** A 1–10 piecewise-linear score derived from the BLS-projected employment change percentage over a 10-year horizon.

**Frontend.**
- Axis declaration: `frontend/src/components/PentagonChart.tsx:26`
- Type contract: `frontend/src/types/build.ts:10`
- Stat explanation: `frontend/src/data/statExplanations.ts:64-75`

**Backend model.** `backend/app/models/career.py:62` — `PentagonStats.grw: int | None`. No backend adjustment.

**MCP server.** Passthrough — `src/mcp_server/futureproof_server.py:175`.

**Gold formula.** `src/gold/bls_ooh_occupation_profiles.py:67-96`:
```python
GRW_BREAKPOINTS = [
    (-20.0, -10.0, 1.0, 2.5),
    (-10.0,  -1.0, 2.5, 4.0),
    ( -1.0,   1.0, 4.0, 5.0),
    (  1.0,   5.0, 5.0, 6.5),
    (  5.0,  10.0, 6.5, 7.5),
    ( 10.0,  20.0, 7.5, 9.0),
    ( 20.0,  50.0, 9.0, 10.0),
]

def compute_grw_score(pct):
    if pct is None:
        return None
    if pct <= -20.0:
        return 1.0
    for pct_lo, pct_hi, score_lo, score_hi in GRW_BREAKPOINTS:
        if pct <= pct_hi:
            fraction = (pct - pct_lo) / (pct_hi - pct_lo)
            return score_lo + fraction * (score_hi - score_lo)
    return 10.0  # cap at 10 for >50% growth
```
The float result becomes `grw_score`; it is round-half-up'd to int and stored as `grw_score_rounded` (col 14 of `consumable.occupation_profiles`).

`src/gold/futureproof_engine.py:342, 472` — the gold join attaches `grw_score_rounded` to the program row as `stat_grw`. There is no per-row recomputation; it's a direct copy from `consumable.occupation_profiles`.

**Gold input.** `employment_change_pct` is a passthrough column from silver; the gold layer does not recompute it.

**Silver source.** `src/silver/bls_ooh_transformer.py` reads `base.bls_ooh` from bronze. `employment_change_pct` is computed at bronze ingest time:
- `employment_change_pct = (employment_projected − employment_current) / employment_current × 100`
- `employment_current` and `employment_projected` are multiplied by 1000 at ingest because the BLS XLSX reports in thousands.

The silver transformer also derives a coarse `growth_category` bucket from `employment_change_pct` (`< -10` declining_fast, `-10..-1` declining, `-1..1` stable, `1..10` growing, `10..20` growing_fast, `≥20` booming). This is independent of the GRW score and used elsewhere for tags/labels.

**Bronze source.**

| Bronze table | Ingestor | Upstream | Notes |
|--------------|----------|----------|-------|
| `bronze.bls_ooh` | `src/raw/bls_ooh_ingestor.py` | `https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm` (HTML page with dynamic XLSX link); fallback: `data/raw/xlsx_cache/bls_ooh.xlsx` | XLSX. Filters out aggregate "XX-0000" rows. Median wages > $239,200 are top-coded by BLS — flagged with `median_wage_capped=true`. |

**Edge cases / caveats.**
- Catchall "All Other" SOCs (e.g., `13-1199`) and broad rolled-up SOCs are flagged in silver (`catchall_flag`, `broad_occupation_flag`) but still receive a GRW score. Some downstream consumers may want to exclude them.
- A SOC with no projected employment change row gets `grw_score=None` and the program inherits `stat_grw=None`.

---

### 2.5 HMN — Human Edge

**In plain language.** How much of this work is fundamentally human — leading people, building relationships, making creative decisions, hands-on physical work, caring for others. O*NET measures 41 different work activities for every occupation, scoring how important each one is to the job. We've hand-picked 14 of those 41 as "human-intensive" (managing people, teaching, conflict resolution, physical labor, creative thinking, etc.) and ask: of all the importance scores, what fraction lives in those 14? An occupation where most of the work is "human-intensive" gets a high HMN; an occupation that's mostly symbol-pushing on a screen gets a low one. **HMN is a relative score** — we min/max-rescale across all occupations, so a 7 means "this job is more human-centric than most occupations in O*NET," not an absolute "70% of the work is human."

**Definition.** A 1–10 score derived from the importance-weighted share of a SOC's work activity that falls into 14 hand-curated "human-intensive" Generalized Work Activities, then min/max-rescaled across all SOCs in the universe.

**Frontend.**
- Axis declaration: `frontend/src/components/PentagonChart.tsx:27`
- Type contract: `frontend/src/types/build.ts:11`
- Stat explanation: `frontend/src/data/statExplanations.ts:76-88`

**Backend model.** `backend/app/models/career.py:63` — `PentagonStats.hmn: int | None`. No backend adjustment.

**MCP server.** Passthrough — `src/mcp_server/futureproof_server.py:176`. Top-5 human activities (`top_human_activities`) are JSON-decoded for narrative, but the stat itself is unmodified.

**Gold formula.** `src/gold/onet_work_profiles.py:146-330` — a two-phase compute inside `derive_gold_rows`:

**Phase 1 (per-occupation, lines 217-231):**
```python
human_acts = [a for a in acts if a["element_id"] in HUMAN_INTENSIVE_ELEMENT_IDS]
human_importance_sum = sum(a["importance"] for a in human_acts if a["importance"] is not None)
total_importance_sum = sum(a["importance"] for a in acts if a["importance"] is not None)
human_ratio = human_importance_sum / total_importance_sum  # if total > 0
```

The 14 human-intensive O*NET work activity element IDs (`onet_work_profiles.py:46-61`):

| Element ID | Activity name |
|-----------|---------------|
| 4.A.4.b.4 | Guiding, Directing, and Motivating Subordinates |
| 4.A.4.b.5 | Coaching and Developing Others |
| 4.A.4.a.7 | Resolving Conflicts and Negotiating with Others |
| 4.A.4.a.8 | Performing for or Working Directly with the Public |
| 4.A.4.a.4 | Establishing and Maintaining Interpersonal Relationships |
| 4.A.4.b.2 | Developing and Building Teams |
| 4.A.4.b.3 | Training and Teaching Others |
| 4.A.4.a.6 | Selling or Influencing Others |
| 4.A.4.b.1 | Coordinating the Work and Activities of Others |
| 4.A.2.b.2 | Thinking Creatively |
| 4.A.2.b.1 | Making Decisions and Solving Problems |
| 4.A.3.a.1 | Performing General Physical Activities |
| 4.A.3.a.2 | Handling and Moving Objects |
| 4.A.4.a.5 | Assisting and Caring for Others |

(There are 41 Generalized Work Activities total in O*NET; the other 27 are excluded from the numerator.)

**Phase 2 (global rescale, lines 309-330):**
```python
ratios = [r["human_ratio"] for r in phase1_results if r["human_ratio"] is not None]
observed_min = min(ratios)
observed_max = max(ratios)

for result in phase1_results:
    hr = result.pop("human_ratio")
    if hr is not None and (observed_max - observed_min) > 0:
        hmn = 1.0 + 9.0 * (hr - observed_min) / (observed_max - observed_min)
        hmn = max(1.0, min(10.0, hmn))  # clamp
    elif hr is not None:
        hmn = 5.5  # all ratios identical → midpoint
    else:
        hmn = None
    result["hmn_score"] = hmn
    result["hmn_score_rounded"] = _round_half_up(hmn)
```

The rescaled score is stored as `hmn_score_rounded` (col 8 of `consumable.onet_work_profiles`) and copied verbatim to `program_career_paths.stat_hmn` at `src/gold/futureproof_engine.py:345, 473`.

**Gold inputs.**

| Input | Source |
|-------|--------|
| `acts` (per occupation) | `base.onet_activity_profiles` — pivoted from O*NET work activities for the occupation, with `element_id`, `element_name`, `importance` |
| `human_set` | Hardcoded `HUMAN_INTENSIVE_ELEMENT_IDS` constant (lines 46-61) |

**Silver source.** `src/silver/onet_transformer.py` produces `base.onet_occupations`, `base.onet_activity_profiles`, `base.onet_context_profiles` by pivoting O*NET work-activity / work-context rows from long format (one row per `(soc, element_id, scale_id)`) to wide-format-per-occupation. The `importance` field comes through unchanged from O*NET (1–5 scale, or 0–100 depending on element).

**Bronze source.**

| Bronze table | Ingestor | Upstream | Notes |
|--------------|----------|----------|-------|
| `bronze.onet_task_statements`, `bronze.onet_work_activities`, `bronze.onet_work_context`, `bronze.onet_experience` | `src/raw/onet_ingestor.py` (multiple ingestor classes) | `https://www.onetcenter.org/dl_files/database/db_30_2_text.zip` (O*NET 30.2 tab-delimited) | ZIP containing TSVs. Each occupation has ~5–20 tasks and a row per `(element_id, scale_id)` for work activities and context. |

**Edge cases / caveats.**
- HMN is a **relative** score — the 1–10 range is meaningful only against the SOC universe present at compute time. Adding/removing occupations from O*NET shifts every score.
- The "all ratios identical" branch is theoretical (would never fire on the real ~900 SOC O*NET dataset) but exists as a guard.
- An occupation with no activity rows at all gets `hmn_score=None` and the program inherits `stat_hmn=None`.
- The 14-element list is **hand-curated**, not data-driven — changing the list is a deliberate spec-level decision, not a tunable knob.

---

## 3. The Joining Layer: `consumable.program_career_paths`

**In plain language.** This is the one table the backend reads to build the pentagon. It has one row per `(school, major, possible career)` combo — and a single major usually leads to many careers (a Computer Science degree could become "Software Developer," "Data Scientist," "Information Security Analyst," and so on). So in the API, picking one school + major fans out into multiple pentagon rows, and the frontend presents these as branching career paths the student could take. The CIP-SOC crosswalk (Department of Education's "this academic program → these occupations" lookup) is what does the fanning-out.

This is the table the backend actually reads. Grain: `unitid × cipcode × soc_code`. Schema is at `src/gold/futureproof_engine.py:161-233` (53 fields, including the 5 stats and the 5 boss scores). The join SQL is at `src/gold/futureproof_engine.py:295-386`.

**The join graph:**

```
career_outcomes  (unitid × cipcode × credlev)
        │
        │  INNER JOIN on co.cipcode = LEFT(xw.cipcode, 5)
        │  (5-char prefix match — folds 6-digit CIPs to family granularity)
        ▼
   crosswalk  (cipcode × soc_code, many-to-many)
        │
        │  LEFT JOIN on xw.soc_code = op.soc_code
        ├─ occupation_profiles  → stat_grw, market score, wage percentile
        │
        │  LEFT JOIN on xw.soc_code = onet.bls_soc_code
        ├─ onet_work_profiles   → stat_hmn, burnout, top activities
        │
        │  Python-side dict lookup on soc_code
        └─ ai_exposure          → stat_res, boss_ai, composite provenance
```

After the SQL join, `derive_pcp_rows` (`src/gold/futureproof_engine.py:389-531`):

1. Computes `stat_ern` and `stat_roi` per row (the program-level stats).
2. Copies `grw_score_rounded` → `stat_grw` and `hmn_score_rounded` → `stat_hmn`.
3. Looks up `stat_res` and AI provenance fields from the AI exposure dict (`ai_data` at line 464).
4. Derives boss scores: `boss_loans_score = 11 - stat_roi`, `boss_market_score`, `boss_burnout_score`, `boss_ceiling_score`.
5. Dedups on the (unitid, cipcode, soc_code) grain via `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY stat_richness DESC)` (lines 372-385) — when a (CIP, SOC) pair matches multiple ways, the row with the most non-null stats wins.

**Match quality** (`derive_match_quality`, lines 132-141) records which joins succeeded:
- `full` — both BLS and O*NET joined
- `partial_no_onet`, `partial_no_bls`, `scorecard_only` — partial coverage
- This drives `overall_confidence` (`high`, `medium`, `low`) per row.

---

## 4. Bronze/Raw Source Catalog

One subsection per upstream data source, with ingestor, output table, raw URL, key columns, and DQ governance reference.

### 4.1 College Scorecard — Field of Study

- **Ingestor:** `src/raw/college_scorecard_ingestor.py`
- **Upstream URL:** `https://ed-public-download.app.cloud.gov/downloads/Most-Recent-Cohorts-Field-of-Study.csv` (primary); `https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Field-of-Study_04172025.zip` (fallback)
- **Format:** CSV, ~174 columns, ~500 MB uncompressed. Read in 50,000-row chunks per `CLAUDE.md` rule.
- **Filter at ingest:** `CREDLEV=3` (bachelor's only).
- **Bronze table:** `bronze.college_scorecard` at `data/bronze/iceberg_warehouse/bronze.college_scorecard`
- **Grain:** `unitid × cipcode × credlev`
- **Key columns extracted:** UNITID, INSTNM, CIPCODE, CIPDESC, CREDDESC, CREDLEV, MD_EARN_WNE, EARN_MDN_HI_1YR, EARN_MDN_HI_2YR, DEBT_ALL_STGP_EVAL_MDN, IPEDSCOUNT1, IPEDSCOUNT2, CONTROL.
- **Sentinel handling:** "PrivacySuppressed", "PS", "NA" → NULL.
- **CIP normalization:** XX.XXXX format enforced; treated as string (per CLAUDE.md rule: "CIPCODE must always be treated as string type, never float").
- **Powers:** ERN (numerator), ROI (denominator).
- **DQ scorecard:** `governance/dq-scorecards/raw-ingest-college-scorecard-scorecard.md`

### 4.2 College Scorecard — Institution

- **Ingestor:** `src/raw/college_scorecard_institution_ingestor.py`
- **Upstream URL:** `https://ed-public-download.app.cloud.gov/downloads/Most-Recent-Cohorts-Institution.csv` (primary); same fallback domain.
- **Format:** CSV, ~1,900 columns, ~170 MB. Selectively extracts ~28 cost fields.
- **Filter at ingest:** `PREDDEG=3` (predominantly bachelor's) OR `ICLEVEL=1` (4-year).
- **Bronze table:** `bronze.college_scorecard_institution`
- **Grain:** `unitid` (one row per institution; first-row-wins dedup).
- **Key columns extracted:** UNITID, INSTNM, STABBR, CONTROL, PREDDEG, COSTT4_A, COSTT4_P, NPT4_PUB, NPT4_PRIV, NPT41_PUB–NPT45_PUB (quintile net prices), NPT41_PRIV–NPT45_PRIV, TUITIONFEE_IN, TUITIONFEE_OUT, ROOMBOARD_ON, ROOMBOARD_OFF, BOOKSUPPLY.
- **Powers:** ROI (numerator via `net_price_annual`), residency adjustment in backend.
- **DQ scorecard:** `governance/dq-scorecards/raw-ingest-college-scorecard-institution-scorecard.md`

### 4.3 BLS Occupational Outlook Handbook

- **Ingestor:** `src/raw/bls_ooh_ingestor.py`
- **Upstream URL:** `https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm` (HTML page with dynamic XLSX link); fallback: `data/raw/xlsx_cache/bls_ooh.xlsx`. Browser-like User-Agent required.
- **Format:** XLSX with flexible header matching across BLS table variants.
- **Filter at ingest:** Excludes aggregate "XX-0000" rows.
- **Bronze table:** `bronze.bls_ooh`
- **Grain:** `soc_code`
- **Key columns extracted:** soc_code, occupation_title, employment_current, employment_projected, employment_change_num, employment_change_pct, openings_annual_avg, median_annual_wage, median_wage_capped, education_typical, education_code, work_experience, work_experience_code, training_typical, training_code.
- **Top-coding:** `median_annual_wage` at `≥239,200` is parsed to `239200.0` and flagged `median_wage_capped=true`.
- **Unit conversion:** Employment values multiplied by 1000 at ingest (BLS reports in thousands).
- **Powers:** GRW (`employment_change_pct`), ERN (occupation wage percentile), boss_market.
- **DQ scorecard:** `governance/dq-scorecards/raw-ingest-bls-ooh-scorecard.md`

### 4.4 O*NET — Task Statements + Work Context

- **Ingestor:** `src/raw/onet_ingestor.py` (multiple classes: `OnetTaskStatementsIngestor`, `OnetWorkContextIngestor`, `OnetWorkActivitiesIngestor`)
- **Upstream URL:** `https://www.onetcenter.org/dl_files/database/db_30_2_text.zip` (O*NET 30.2). Fallback: `data/raw/onet_cache/`.
- **Format:** ZIP → TSV. Files extracted: "Task Statements.txt", "Work Activities.txt", "Work Context.txt".
- **Bronze tables:**
  - `bronze.onet_task_statements` — one row per (onet_soc_code, task_id)
  - `bronze.onet_work_activities` — one row per (onet_soc_code, element_id, scale_id) for the 41 Generalized Work Activities
  - `bronze.onet_work_context` — one row per (onet_soc_code, element_id, scale_id) for context elements
  - `bronze.onet_experience` — education / training / experience scales (RL, RW, PT, OJ)
- **Powers:** HMN (work activities + 14 hand-curated human-intensive elements), burnout score, top-5 activity narrative, experience requirements.
- **DQ scorecard:** `governance/dq-scorecards/raw-ingest-onet-scorecard.md`

### 4.5 Karpathy AI Exposure Scores

- **Ingestor:** `src/raw/karpathy_ai_exposure_ingestor.py`
- **Upstream URLs:**
  - `https://raw.githubusercontent.com/karpathy/jobs/master/scores.json` (per-slug 0–10 score)
  - `https://raw.githubusercontent.com/karpathy/jobs/master/occupations.csv` (slug → SOC, title, metadata)
  - Joined at ingest on `slug` (kebab-case occupation identifier).
- **Format:** JSON + CSV. ~342 rows.
- **Bronze table:** `bronze.karpathy_ai_exposure`
- **Grain:** `slug`
- **Key columns:** slug, occupation_title, category, soc_code (often NULL), exposure_score (0–10 int), rationale, median_pay_annual, num_jobs_2024, entry_education.
- **Powers:** RES (Karpathy fallback baseline).
- **DQ scorecard:** `governance/dq-scorecards/raw-ingest-karpathy-ai-exposure-scorecard.md`

### 4.6 Anthropic Economic Index

- **Ingestor:** `src/raw/anthropic_economic_index_ingestor.py`
- **Upstream URL:** `https://huggingface.co/datasets/Anthropic/EconomicIndex` (HuggingFace dataset, cloned via git lfs to `data/raw/anthropic_economic_index/`).
- **Release preference:** `release_2026_03_24` → `release_2026_01_15` → `release_2025_03_27` (first with `task_pct_v2.csv` wins).
- **Format:** Three CSVs per release, joined at ingest on task text (case-insensitive, trailing-period-normalized):
  1. `task_pct_v2.csv` — `task_name`, `pct` (0–100, source-level sum=100)
  2. `automation_vs_augmentation_by_task.csv` — `task_name`, 5-axis breakdown
  3. `onet_task_statements.csv` — O*NET-SOC bridge (many-to-many task → SOC)
- **Bronze table:** `bronze.anthropic_economic_index`
- **Grain:** `(task_id, soc_code)` composite (task-to-SOC fan-out)
- **Special handling:**
  - The `task_name='none'` placeholder is preserved with `soc_code=NULL` (one row, no split, captured by DQ rule `RAW-AEI-017`).
  - When a task fans out to N SOCs, `task_pct` is split N ways so the global sum stays at 100.
  - Tasks with only malformed SOCs are dropped (chaos-monkey P1 guard) rather than emitted as NULL-SOC rows.
- **Powers:** RES (real-world adoption signal → confidence weight), `velocity_label`, `composite_method`.
- **DQ scorecard:** `governance/dq-scorecards/raw-anthropic-economic-index-scorecard.md`

### 4.7 Gemma 4 Theoretical AI Exposure

- **Ingestor:** *None* — Gemma scoring is **computed locally**, not externally sourced.
- **Inference path:** Gemma 4 is invoked via Ollama (`localhost:11434`) or OpenRouter (`google/gemma-4-26b-a4b-it`) per the `INFERENCE_BACKEND` env var (`.env`). Spec: `docs/specs/cloud-gemma-deployment.md`.
- **Persistence:** Output lands directly in silver as `base.gemma_ai_exposure` (no bronze stage, since the "raw" data is the model's structured output, not an external file).
- **Provenance:** Each scored row carries `scoring_model='gemma-4'` and a `model_tag` (the exact Ollama tag, e.g., `gemma4:26b-it-q4_K_M`) so receipts can audit which model produced the score.
- **Powers:** RES (theoretical signal — the preferred score when available; ~798 SOCs covered when promoted).
- **Spec reference:** `docs/specs/three-signal-ai-exposure-composite-v3.md` (composite v4); `docs/specs/gemma-ai-exposure-rescore.md` (Gemma rescore v4).

### 4.8 CIP-SOC Crosswalk

- **Ingestor:** `src/raw/cip_soc_crosswalk_ingestor.py`
- **Upstream URL:** `https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx`
- **Fallback:** `data/raw/xlsx_cache/CIP2020_SOC2018_Crosswalk.xlsx`
- **Format:** XLSX, sheet "CIP-SOC".
- **Bronze table:** `bronze.cip_soc_crosswalk`
- **Grain:** `(cipcode, soc_code)` many-to-many.
- **Special:** 194 "no match" rows (SOC `99-9999`) are preserved at bronze, filtered at silver.
- **Role:** Connective tissue. It does not power any pentagon stat directly, but it's the join key that lets program-level (CIP) stats and occupation-level (SOC) stats coexist in `program_career_paths`.

### 4.9 BEA Regional Price Parities

- **Ingestor:** `src/raw/bea_rpp_ingestor.py`
- **Upstream URL:** `https://apps.bea.gov/api/data/?UserID={api_key}&method=GetData&datasetname=Regional&TableName=SARPP&LineCode=1&Year=2024&GeoFips=STATE&ResultFormat=JSON`
- **Auth:** `BEA_API_KEY` env var.
- **Fallback:** `data/raw/bea_cache/bea_rpp_2024.csv`
- **Bronze table:** `bronze.bea_rpp`
- **Grain:** `geo_fips` (51 rows: 50 states + DC).
- **Role:** **Does not power any pentagon stat.** RPP is used for cost-of-living adjustments (`compare_purchasing_power` MCP tool, narrative copy) and for the `consumable.regional_price_parities` table read by the Career Outcomes routing logic. None of ERN/ROI/RES/GRW/HMN reads from this source.

---

## 5. Backend Adjustments After Gold

**In plain language.** The data pipeline pre-computes the pentagon once per data refresh, but two things can change *per student request*: how hard they say they'll work (the effort slider) and where they live (residency surcharge for out-of-state public schools). When those change, the backend recomputes the affected stat on the fly, using the same formulas the gold layer uses.

The backend re-derives stats only when a per-request input could change them. All adjustments live in `backend/app/services/stat_engine.py`.

### 5.1 Effort slider — adjusts ERN only

| `effort` | Shift to ERN |
|----------|--------------|
| `working_hard` | −2 |
| `working` | −1 |
| `balanced` | 0 |
| `focused` | +1 |
| `all_in` | +2 |

(`stat_engine.py:38-44`. Applied at `_apply_effort` line 53-64; called from `_row_to_outcome` line 263. Result clamped to [1, 10].)

ROI is not adjusted (`stat_engine.py:34-37`): "effort reflects earning potential while in school, not debt load."

### 5.2 Cost-based ROI re-derivation

`_derive_roi` (`stat_engine.py:67-88`) calls `compute_stat_roi(cost_based_dte)` from the gold module to recompute ROI when:

- The student's residency has changed the effective net price (out-of-state surcharge added at `stat_engine.py:151-173, 213-220`).
- The DTE is non-null (otherwise the row's pre-baked `stat_roi` is used as fallback).

This recomputation uses the **same gold formula and same breakpoints** — the only difference is the input DTE.

### 5.3 Loans Boss derivation

The Loans Boss is not a pentagon stat, but it is computed via the ROI formula and sits next to the pentagon in the API contract, so it's worth documenting:

- `_derive_loans_boss` (`stat_engine.py:91-148`)
- `modeled_total_debt = cost_per_year × 4 × loan_pct`
- `financed_dte = modeled_total_debt / earnings_1yr_median`
- `boss_loans_score = 11 − compute_stat_roi(financed_dte)`
- `cost_per_year = net_price_annual` (preferred) or `debt_median / 4` (fallback)
- Special: `loan_pct ≤ 0` → boss_score = 1 (auto-win).

This is the **only** path through the system where the per-request `loan_pct` knob influences the row.

---

## 6. Notes & Caveats

1. **Pentagon stats are integers in `[1, 10]` or `null`.** All five compute paths use `_round_half_up` (DuckDB-compatible rounding) and clamp to 1–10. Null propagates when any required input is missing.

2. **ROI provenance.** Two fields surfaced in every API response let consumers audit ROI:
   - `roi_cost_basis ∈ {'cost_of_attendance', 'debt_median', 'none'}` — which numerator drove the gold-level DTE.
   - `financed_dte` — the loan_pct-aware DTE used for the Loans Boss (always distinct from the ROI's input DTE, which is loan_pct-independent).

3. **RES composite_method values** (carried through `program_career_paths.composite_method`):
   - `three_signal` — Gemma + Karpathy + Anthropic
   - `two_signal_no_anthropic` — Gemma + Karpathy
   - `gemma_plus_anthropic` — Gemma + Anthropic (no Karpathy row for that SOC)
   - `gemma_only` — Gemma only
   - `karpathy_only` — Gemma missing or errored, Karpathy fallback
   - `observed_override` — Gemma=0 but real-world adoption > 0; trust observation
   - `no_data` — neither Gemma nor Karpathy had a row (drops from `consumable.ai_exposure`, so the program row gets `stat_res=None`)

4. **HMN is min/max-rescaled across the SOC universe.** The 1–10 scale is internally consistent at any one promote, but is not stable across promotes if the SOC set changes. Do not compare HMN scores across schema versions without recomputing.

5. **GRW caps at 10 for >50% growth** (`bls_ooh_occupation_profiles.py:95-96`). Any SOC with `employment_change_pct > 50` gets the same 10. Below `−20%`, scores floor at 1.

6. **CIP-SOC crosswalk is many-to-many.** A single program (unitid × cipcode) typically maps to multiple SOCs. The grain of `program_career_paths` is `unitid × cipcode × soc_code`, so each program shows up as multiple pentagon rows in the API — one per career path.

7. **CIP intent substitution does not re-derive stats.** When the substitution flow blends broad-CIP earnings with specific-SOC career paths (`src/mcp_server/futureproof_server.py:2704-2768`), it surfaces the gold-computed stats verbatim. Per memory note (`feedback_no_substitution_caveat.md`), no "Limited data" warning is shown on these cards.

8. **Gemma scoring drift.** Different Gemma model tags or quantizations produce different RES scores for the same SOC. The `model_tag` field in the API response surfaces the exact tag so receipts and audit trails can tell scorecard versions apart.

---

## 7. Reference Index

### 7.1 File-to-stat mapping

| File | ERN | ROI | RES | GRW | HMN |
|------|-----|-----|-----|-----|-----|
| `frontend/src/components/PentagonChart.tsx` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `frontend/src/types/build.ts` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `frontend/src/data/statExplanations.ts` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `backend/app/models/career.py` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `backend/app/services/stat_engine.py` | ✓ (effort) | ✓ (recompute) | — | — | — |
| `src/mcp_server/futureproof_server.py` | passthrough | passthrough | passthrough | passthrough | passthrough |
| `src/gold/futureproof_engine.py` | ✓ (compute) | ✓ (compute) | join (lookup) | join (copy) | join (copy) |
| `src/gold/college_scorecard_career_outcomes.py` | input rank | input DTE | — | — | — |
| `src/gold/bls_ooh_occupation_profiles.py` | input wage pct | — | — | ✓ (compute) | — |
| `src/gold/onet_work_profiles.py` | — | — | — | — | ✓ (compute) |
| `src/gold/ai_exposure_transformer.py` | — | — | ✓ (compute) | — | — |

### 7.2 Spec references

- **Cost-based ROI rewrite:** `~/.claude/plans/why-are-we-still-jaunty-curry.md` (referenced from `backend/app/models/career.py:31-46, 142-152`)
- **Three-signal AI exposure composite (v4):** `docs/specs/three-signal-ai-exposure-composite-v3.md` (referenced from `src/gold/ai_exposure_transformer.py:148-156`)
- **Gemma AI exposure rescore (v4):** `docs/specs/gemma-ai-exposure-rescore.md`
- **CIP intent substitution:** `docs/specs/cip-intent-substitution.md`
- **O*NET experience requirements (v1.2.0):** `docs/specs/onet-experience-requirements.md` (referenced from `src/gold/futureproof_engine.py:283-287`)
- **Raw ingest — College Scorecard Institution (Zone 3):** referenced from `src/gold/college_scorecard_career_outcomes.py:8-14, 50-62, 110-117`
- **DQ scorecards root:** `governance/dq-scorecards/`

### 7.3 Key constants (single point of truth)

| Constant | Location | Value |
|----------|----------|-------|
| ROI breakpoints | `src/gold/futureproof_engine.py:55-63` | 5 piecewise segments |
| GRW breakpoints | `src/gold/bls_ooh_occupation_profiles.py:45-53` | 7 piecewise segments |
| Human-intensive O*NET element IDs | `src/gold/onet_work_profiles.py:46-61` | 14 element IDs |
| Burnout O*NET element IDs | `src/gold/onet_work_profiles.py:64-74` | 9 element IDs |
| ERN blend weights | `src/gold/futureproof_engine.py:88` | `0.6 × program + 0.4 × occupation` |
| Effort shifts | `backend/app/services/stat_engine.py:38-44` | −2, −1, 0, +1, +2 |
| Adoption confidence formula | `src/gold/ai_exposure_transformer.py:228-231` | `max(0.3, min(1.0, 0.3 + 0.7 × p/100))` |
| Velocity buckets | `src/gold/ai_exposure_transformer.py:193-203` | 90 / 70 / 40 percentile thresholds |
