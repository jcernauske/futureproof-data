# FutureProof Boss Fight System — Complete Technical Writeup

## Overview

The boss fight system (internally called the "gauntlet") puts each career path through five threat assessments representing real obstacles graduates face. Each fight produces a WIN / DRAW / LOSE outcome based on deterministic scoring against threshold values. Losses can be challenged via a "reroll" mechanic where students equip skills that mutate their stats and rescore the fight. Gemma generates personalized coaching narratives for every outcome.

---

## The Five Bosses

| Boss ID | Label | What It Represents |
|---------|-------|--------------------|
| `ai` | Fight AI | Automation exposure — how much of this job can AI already do? |
| `loans` | Fight Student Loans | Debt burden relative to starting salary |
| `market` | Fight the Market | Job market growth from BLS hiring projections |
| `burnout` | Fight Burnout | Workload intensity (time pressure, hours, consequence of error) |
| `ceiling` | Fight the Ceiling | Earnings potential — is there room to grow or a hard cap? |

Defined in `backend/app/services/boss_fights.py` (`BOSS_SPECS` dict, ~line 480) and typed as `BossId = Literal["ai", "loans", "market", "burnout", "ceiling"]` in `backend/app/models/career.py`.

---

## Scoring: How Each Boss Gets Its Number

### Fight AI (boss_ai_score)

**Input data:** Gemma 4 task-level AI exposure scores from O*NET task descriptions, blended with Anthropic Economic Index adoption data and Karpathy exposure scores.

**Pipeline path:**
1. `base.gemma_ai_exposure` or `base.karpathy_ai_exposure` (Silver zone)
2. `ai_exposure_transformer.py` runs `blend_scores()` to produce `consumable.ai_exposure` with a `composite_exposure` field
3. `futureproof_engine.py` LEFT JOINs this into `program_career_paths.boss_ai_score`

**Formula:** `boss_ai_score = max(exposure_score, 1)` — floor of 1, scale 1-10

**Fight scoring:** The fight scorer sums **raw** stat_res + raw stat_hmn (not the blended display values). This is a deliberate design decision from the pentagon-stat-reshape spec — the fight uses the unblended inputs for bit-exact consistency.

**Companion stat:** `stat_res` (AI Resilience) uses the inverse: `min(11 - exposure_score, 10)`

**Composite method (v4 Option B):** When Anthropic adoption data is available, blends:
- Gemma theoretical score (what AI *could* do)
- Observed adoption (what AI *is* doing, from Claude conversation share)
- Velocity signal (saturating / accelerating / emerging / nascent)
- Weight shifts toward Gemma when real-world adoption is high

### Fight Student Loans (boss_loans_score)

**Input data:** College Scorecard institution cost data, program-level earnings, and loan amortization math.

**Two computation paths:**

1. **Cost-of-Attendance path (preferred, computed at request time):**
   - `modeled_debt = published_cost_4yr * loan_pct` (loan_pct is the user's financing slider, 0.0-1.0)
   - `financed_dte = modeled_debt / earnings_1yr_median`
   - Runs OBBBA Tiered Standard loan amortization (10-25 year term) to get `total_interest_paid`
   - `interest_burden = total_interest_paid / earnings_1yr_median`
   - Maps interest_burden to 1-10 score via `_interest_burden_to_score()`
   - Computed in `backend/app/services/stat_engine.py` (~line 234)

2. **Legacy fallback (pre-computed in Gold zone):**
   - `boss_loans = 11 - stat_roi`
   - Used when institution cost data is missing

   **Byproducts surfaced to UI:** `modeled_total_debt`, `financed_dte`, `total_interest_paid`, `monthly_payment`, `term_months`

### Fight the Market (boss_market_score)

**Input data:** BLS Occupational Outlook Handbook employment growth projections.

**Pipeline path:** `base.bls_ooh` (Silver) -> `consumable.occupation_profiles.market_score_rounded` (Gold) -> `futureproof_engine`

**Formula:** Direct mapping — the GRW stat *is* the market score. No additional scaling.

### Fight Burnout (boss_burnout_score)

**Input data:** O*NET Work Context survey data — 12 burnout-relevant elements:
- Time pressure, work-life balance, consequence of error, physical exertion, wear/tear, interpersonal conflict, public interaction, stressful decisions, mentoring/teaching, frustrating work, fast pace, hazards

**Pipeline path:** `src/gold/onet_work_profiles.py` (~line 260)

**Formula:** `burnout_score = 1.0 + 9.0 * avg_normalized_importance` (mean of 12 elements, scaled 1-10)

**Score inversion during fight:** Higher raw burnout = more risk = *lower* readiness. The fight scorer inverts: `readiness = 11 - raw_burnout_score`. So a raw 8/10 burnout risk becomes a 3/10 fight readiness.

**Burnout drivers:** Top 3 contributing elements are extracted and surfaced as user-facing explanations.

### Fight the Ceiling (boss_ceiling_score)

**Input data:** Stage 3 career branches (related_wage from `consumable.career_branches`), Scorecard earnings_1yr_median, OEWS wage percentiles.

**Computation path:** `stat_engine.compute_ceiling_from_branches()` at request time (supersedes Gold-zone formula).

**Formula (15-year doubling projection):**
1. `starting_wage` = Scorecard `earnings_1yr_median` (preferred) or OEWS p50 (`median_annual_wage`) or OEWS p25 (`wage_p25`)
2. Filter Stage 3 branches to upward nodes (`related_wage > starting_wage`)
3. `year_15_wage` = median of upward node wages
4. `growth_multiple` = `year_15_wage / starting_wage`
5. Score mapped via inflation-adjusted bands:
   - `growth_multiple < 1.346` (inflation floor): auto-LOSE, score = 1, `structural_loss = True`
   - `1.346 - 1.7`: score 2-6 (LOSE/DRAW band)
   - `1.7 - 2.0`: score 6-9 (WIN band)
   - `>= 2.0`: score 10 (genuine doubling)

**Inflation constant:** 2% annual (Federal Reserve long-run target), compounded 15 years = 1.346x.

**Fallback chain:**
1. No Stage 3 tree: use OEWS p75 as `year_15_wage` proxy
2. No upward nodes: auto-LOSE, `structural_loss = True`
3. Starting wage suppressed: use OEWS p25
4. All sources missing: score = None, fight result = "unknown"

**Narrative metadata:** `growth_multiple`, `starting_wage`, `year_15_wage`, `upward_share`, `structural_loss`, `inflation_floor_wage` — all surfaced to Gemma for narrative generation.

---

## Win/Draw/Lose Classification

Defined in `BOSS_SPECS` (`boss_fights.py` ~line 480):

| Boss | Win (>=) | Draw (>=) | Lose (<) |
|------|----------|-----------|----------|
| AI | 12 | 7 | 7 |
| Loans | 7 | 5 | 5 |
| Market | 6 | 4 | 4 |
| Burnout | 7 | 5 | 5 |
| Ceiling | 7 | 5 | 5 |

Note: Fight AI's thresholds are higher because it sums two stats (raw_stat_res + raw_stat_hmn), so the scale is roughly 2-20 instead of 1-10.

Classification logic:
```
if score >= win_threshold: "win"
elif score >= draw_threshold: "draw"
elif score is None: "unknown"
else: "lose"
```

### Final Verdict (aggregate across 5 fights)

| Condition | Verdict |
|-----------|---------|
| 0 scored fights | "Insufficient data..." |
| 3+ wins, 0 losses | DOMINANT BUILD |
| wins > losses | SOLID BUILD (with gap label) |
| wins == losses | MIXED BUILD |
| wins < losses | VULNERABLE BUILD |

---

## The Reroll Mechanic

### What Rerolls Are

When a student loses or draws a fight, they can equip "skills" — concrete career strategies (e.g., "Get AWS Certified", "Build a Portfolio") — that modify their stats. The fight is then rescored with the mutated stats. This transforms a passive scorecard into an interactive coaching moment.

### Skill Pool

Skills are generated by Gemma during build creation. Each skill has:
- `title`: Human-readable name
- `rationale`: Why this helps
- `targets`: Which boss IDs it affects
- `delta_ern`, `delta_roi`, `delta_res`, `delta_grw`: Stat modifications
- `delta_burnout_raw`, `delta_ceiling_raw`, `delta_loans_raw`: Direct boss score modifications

### Frontend Flow

1. Student sees LOSE/DRAW result on a fight
2. "Equip skills to fight again" CTA appears
3. RerollFlow component mounts, showing available skills as checkbox cards
4. Student selects one or more skills (stat impact badges shown per skill)
5. Student clicks "Rematch" button
6. API call: `POST /build/{build_id}/reroll` with `{ boss_id, skill_ids }`
7. New result animates in with improvement indicator (e.g., "LOSE -> WIN")

### Backend Reroll Process (`backend/app/routers/gauntlet.py`)

1. Retrieve build from state
2. Extract selected skills from `build.skill_pool` by ID
3. **Apply skills to career:** `skill_pool.apply_skills(career, picks)` mutates stat values
4. **Rescore:** `boss_fights.rescore_fight(mutated_career, boss_id)` computes new raw_score + result
5. **Preserve history:** Original result/score copied to `original_result` / `original_raw_score` (first reroll only — persists across cascading attempts)
6. **Generate narrative:** Gemma writes updated coaching commentary via `generate_reroll_commentary_async()` with context about the original result, new result, and equipped skills
7. **Update gauntlet:** Replace old fight in `build.gauntlet.fights`, recompute W/L/D/verdict
8. **Move skills:** Equipped skills transfer from `build.skill_pool` to `build.skills_crafted`
9. Return new `BossFightResult` to frontend

### Reroll Limits

- **MAX_REROLLS = 3** per boss (enforced client-side in GauntletScreen.tsx)
- Backend enforcement is implicit via skill pool exhaustion
- After 3 attempts or when no applicable skills remain, the frontend shows the **Structural Loss** screen

### Structural Loss

When all available skills for a boss are exhausted and the student still loses:
- An explicit "structural loss" screen appears
- Messaging explains the gap is structural (school + major + career combination), not tactical
- Reassures the student that Next Steps will address this
- Single "Continue" button advances to the next fight

### Data Mutations on Reroll

| Field | Change |
|-------|--------|
| `fight.result` | May change (lose -> draw -> win) |
| `fight.raw_score` | Recalculated from mutated career |
| `fight.reason` | New scoring explanation |
| `fight.narrative` | Updated Gemma coaching text |
| `fight.rerolled` | Set to true |
| `fight.reroll_count` | Incremented |
| `fight.original_result` | Stamped on first reroll, preserved thereafter |
| `fight.original_raw_score` | Stamped on first reroll |
| `fight.applied_skill_titles` | Cumulative list of equipped skill names |
| `gauntlet.wins/losses/draws` | Recounted |
| `gauntlet.verdict` | Re-derived |
| `build.career` | Stats mutated by applied skills |
| `build.skill_pool` | Equipped skills removed |
| `build.skills_crafted` | Equipped skills added |

---

## Gemma's Role

Gemma is the **narrative generation layer**. Every fight result gets a personalized 2-3 sentence coaching explanation. Gemma never determines scores or outcomes — those are purely deterministic from the data. Gemma explains what the data means in clear language.

### What Gemma Generates

1. **Initial fight narratives** (5x, parallel during build creation) — Explains each outcome in real-world terms
2. **Reroll commentary** — Updated narrative after skills are equipped, acknowledging what changed
3. **Wrap-up commentary** — Final summary after all skills on a boss are exhausted
4. **Next Steps checklist** — Post-gauntlet action plan with 4 sections (guidance counselor, college recruiters, self-verification, family discussion)
5. **Skill pool** — The skills themselves are Gemma-generated during build creation

### System Prompt Directives

The narrative system prompt (`boss_fights.py` ~line 617) instructs Gemma to:
- Write at 7th-grade reading level, like "a calm older sibling with honest answers"
- Use actual dollar figures, years, percentages — never stat codes (ERN, ROI) or score fractions (7/10)
- **Never use game language** — no "boss", "fight", "battle", "won", "lost", "defeated"
- Structure as: what this means -> specific why -> concrete lever to change it
- 2-3 sentences max

### Boss-Specific Gemma Instructions

| Boss | Gemma Instruction Focus |
|------|------------------------|
| Ceiling | Name starting salary and year-15 salary; compare to inflation floor; flag structural ceiling if growth < 1.346x |
| Loans | Explain monthly payment burden vs. starting salary; compare debt to one year of pay |
| AI | Name which daily tasks AI can already do; discuss adoption velocity; give one concrete skill to stay ahead |
| Market | Frame hiring outlook with specific growth numbers |
| Burnout | Explain workload intensity with the top contributing factors |

### Model Awareness

The system detects which Gemma model is running and adjusts:

| Profile | Model | Max Tokens | Prompt Style | Concurrency |
|---------|-------|------------|--------------|-------------|
| `compact_local` | gemma4:e4b (Ollama) | 400 | Compact (2 sentences) | Sequential |
| `full` | gemma-4-26b-a4b-it (OpenRouter) | 800 | Full (2-3 sentences with detail) | Parallel fanout |

### Reroll-Specific Prompts

When a student rerolls, Gemma receives:
- The original fight narrative
- The original result and score
- The new result and score
- List of equipped skill titles
- Full career context

Gemma then writes updated commentary acknowledging the improvement (or lack thereof) and what real work the skills represent.

### Fallback Behavior (Gemma Unavailable)

The system **never crashes or shows empty text**. Two fallback tiers:

**Tier 1 — No data for this boss** (`_UNKNOWN_FALLBACKS`):
- Per-boss deterministic copy explaining data isn't available
- Example: "There isn't enough data yet on how much AI is being used in this career..."

**Tier 2 — Gemma transport failure** (`_DEGRADED_FALLBACKS`):
- Per-outcome (win/draw/lose) generic copy
- Example: "The numbers on this part of the path look strong. The write-up didn't load this time..."

Fallbacks are applied **server-side** before the Build object reaches the frontend. The frontend never receives an empty narrative string.

### Infrastructure

- **Client:** `backend/app/services/gemma_client.py` — OpenAI-compatible abstraction over Ollama and OpenRouter
- **Concurrency:** Module-level semaphore caps concurrent calls at `GEMMA_MAX_CONCURRENCY` (default 8)
- **Logging:** Every Gemma call appends to `logs/gemma.jsonl` with timestamps, tokens, latency
- **Error handling:** `generate()` and `generate_async()` swallow all exceptions and return empty string — the fallback system handles the rest

---

## Data Flow Summary

```
Silver Zone (Raw Data)
├── base.gemma_ai_exposure          → AI task-level scores
├── base.karpathy_ai_exposure       → Karpathy AI exposure
├── base.anthropic_economic_index   → Real-world AI adoption
├── base.bls_ooh                    → Employment growth projections
├── base.onet_work_profiles         → 12 burnout context elements
├── base.college_scorecard_inst     → Institution cost data
├── base.college_scorecard          → Program earnings, debt
└── base.bls_oews_wage_percentiles  → Wage distribution by education tier

        ↓ Gold Zone Transformers

├── ai_exposure_transformer.py
│   └── blend_scores() → consumable.ai_exposure
│       ├── boss_ai_score = max(exposure_score, 1)
│       └── stat_res = min(11 - exposure_score, 10)
├── onet_work_profiles.py
│   └── burnout_score = 1 + 9 * avg(12 normalized elements)
├── occupation_profiles.py
│   └── market_score_rounded = GRW (direct from BLS)
│   └── wage_percentile_education_tier (for ceiling)
├── career_outcomes.py
│   └── earnings, debt, ROI
└── futureproof_engine.py → consumable.program_career_paths
    ├── Joins all sources
    ├── boss_loans = 11 - stat_roi (fallback)
    ├── boss_ceiling (Gold baseline, superseded at request time)
    └── Output: unitid × cipcode × soc_code with all 5 boss scores

        ↓ Backend (FastAPI, request time)

├── stat_engine.py
│   ├── Loans boss recomputed with loan_pct slider
│   │   ├── modeled_total_debt = cost_4yr * loan_pct
│   │   ├── Loan amortization → total_interest_paid
│   │   └── interest_burden → 1-10 score
│   └── Ceiling boss from Stage 3 branches
│       ├── starting_wage → upward branch wages → growth_multiple
│       └── 15-year doubling bands → 1-10 score
├── boss_fights.py
│   ├── score_gauntlet() → 5 scorer functions → classify → W/L/D verdict
│   ├── narrate_one() → Gemma coaching per fight (parallel)
│   └── rescore_fight() → reroll path
└── gauntlet.py router
    ├── POST /reroll → apply skills, rescore, re-narrate
    └── POST /wrapup → final summary

        ↓ Frontend

└── GauntletScreen.tsx
    ├── GauntletIntro (2.5s auto-advance)
    ├── BossFightCard × 5 (entrance → result → reroll? → resolved)
    ├── FinalBoss (verdict + scorecard)
    └── NextSteps (Gemma action plan)
```

---

## Key Files

| Category | File | Key Lines/Purpose |
|----------|------|-------------------|
| **Scoring** | `backend/app/services/boss_fights.py` | BOSS_SPECS (~480), scorers (~525-600), classify (~603) |
| **Stat Engine** | `backend/app/services/stat_engine.py` | Loans boss loan math (~234-257) |
| **Gold Assembly** | `src/gold/futureproof_engine.py` | Boss score assembly (~596-610), ceiling formula (~169-180) |
| **AI Exposure** | `src/gold/ai_exposure_transformer.py` | Composite scoring (~286-316) |
| **Burnout** | `src/gold/onet_work_profiles.py` | 12-element burnout score (~260-304) |
| **Narratives** | `backend/app/services/boss_fights.py` | System prompt (~617-690), prompts (~767-880), fallbacks (~1013-1079) |
| **Gemma Client** | `backend/app/services/gemma_client.py` | Ollama/OpenRouter abstraction, concurrency, logging |
| **Models** | `backend/app/models/career.py` | BossFightResult, GauntletResult, BossScores |
| **Reroll API** | `backend/app/routers/gauntlet.py` | POST /reroll, POST /wrapup |
| **Build Orchestration** | `backend/app/routers/builds.py` | Gemma fanout (~112-200) |
| **Frontend Screen** | `frontend/src/screens/GauntletScreen.tsx` | Gauntlet lifecycle, reroll handling |
| **Fight Card** | `frontend/src/components/gauntlet/BossFightCard.tsx` | Individual fight display |
| **Reroll UI** | `frontend/src/components/gauntlet/RerollFlow.tsx` | Skill selection for rerolls |
| **Types** | `frontend/src/types/build.ts` | BossFightResult, GauntletResult, AppliedSkill |
| **Store** | `frontend/src/store/gauntletStore.ts` | Phase management, skill selection state |
| **MCP** | `src/mcp_server/futureproof_server.py` | Exposes all 5 boss scores via get_career_paths |
