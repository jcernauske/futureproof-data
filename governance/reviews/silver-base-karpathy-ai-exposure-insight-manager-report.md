# Insight Report: Silver → Gold — base.karpathy_ai_exposure

**Date:** 2026-04-16
**Agent:** @insight-manager
**Source Table:** `base.karpathy_ai_exposure` (Iceberg, Silver zone)
**Entities:** 419 occupation-rows (342 Bronze slugs → expansion → dedup)
**Records:** 419 Silver / 389 BLS-matched (promoted to Gold)
**Time Range:** Single vintage (Karpathy 2024 scoring pass; no time dimension — one LLM-generated snapshot per occupation)
**Downstream consumers already shipped:** `consumable.ai_exposure` (Gold, 389 rows), `consumable.program_career_paths` backfill (stat_res, boss_ai_score), `consumable.career_branches` backfill, MCP tool `get_ai_exposure`

---

## Domain Context

Karpathy AI Exposure is the fifth and final data source in the FutureProof pentagon. It is a set of LLM-generated (0-10) exposure scores + natural-language rationales produced by Andrej Karpathy for U.S. BLS occupations. Higher = more likely to be reshaped / displaced by near-term AI. It is the sole provider of two pentagon primitives:

- **`stat_res`** (AI Resilience): `MIN(11 - exposure_score, 10)` — fifth stat in the character sheet
- **`boss_ai_score`** (Fight AI boss strength): `MAX(exposure_score, 1)` — fifth boss in the gauntlet

Unlike the other sources, Karpathy has NO canonical join key of its own. It piggybacks on the BLS SOC taxonomy but the source data is messy: 290 Bronze rows have detailed SOCs, 50 have broad codes, 52 are null-SOC. Silver's job was to collapse that mess into a clean SOC grain. It succeeded: 23/23 DQ rules passing, 389/419 rows `bls_match = true`, zero grain duplicates.

Business terms already in glossary: BT-080 Exposure Score, BT-081 Exposure Rationale, BT-027 SOC Code, BT-028 Occupation Title.

---

## Executive Summary

Silver `base.karpathy_ai_exposure` is a **complete, passthrough-grade Silver table**: 419 rows, 100% DQ passing, clean SOC grain, rationale ≥ 297 chars on every row. The mandatory Tier-1 Gold product (`consumable.ai_exposure`) **has already been built, DQ-hardened, and wired into the live MCP server** — the RES stat and Fight AI boss are shipping in the F3 UI today. The highest-value remaining moves are **coverage expansion** (Karpathy only scores 342 of 832 occupations in `consumable.occupation_profiles` = 46.8% coverage, leaving 443 occupations with NULL `stat_res` / `boss_ai_score`) and **confidence carry-through** (the 36 title-matched + 110 broad-expansion rows are lower-confidence than the 243 direct matches but the Gold table strips the provenance column). There is no need for a new spec to build Gold from scratch; the report recommends **three enhancement specs** and **one fallback Gemma-scoring spec** to close the coverage gap before demo day.

---

## 1. What Silver Already Provides (Authoritative Inventory)

| Field | Type | Role | Observed Distribution |
|---|---|---|---|
| `record_id` | varchar | PK | `kai-<16-hex>`; 419 unique, zero collisions |
| `soc_code` | varchar | **Join key** | 389 non-null + 30 null; format `XX-XXXX` |
| `slug` | varchar | Provenance | 342 distinct Karpathy slugs (fan-out during expansion preserves slug) |
| `occupation_title` | varchar | Display | Karpathy's original titles (differ from BLS titles) |
| `category` | varchar | Analytical dim | 25 Karpathy groupings (top: healthcare=56, life-physical-and-social-science=38, architecture-and-engineering=33) |
| `exposure_score` | int | Core measure | range 1–10, mean 5.20, median 5.0, mode 7 (71 rows) |
| `rationale` | varchar | **Primary LLM payload** | 100% non-null; min 297, max 587, median 404 chars |
| `bls_match` | boolean | Gate flag | 389 true / 30 false — Gold filters on true |
| `soc_resolved_method` | varchar | **Confidence signal** | direct 243 (62.5%) / broad_expansion 110 (28.3%) / title_match 36 (9.3%) / unresolved 30 |
| `source_load_date`, `ingested_at` | date/ts | Provenance | |

Key invariants verified by EDA + DQ:
- **Inverse invariant holds universally**: `stat_res + boss_ai_score = 11` for all 389 BLS-matched rows.
- **Zero exposure_score=0 rows** — the floor/ceiling branches in the derivations are never exercised in current data.
- **Zero SOC duplicates** after broad expansion + dedup; SOC grain is clean.
- **100% SOC joinability**: all 389 Gold SOC codes exist in `consumable.occupation_profiles`.

---

## 2. Existing Gold Data Products Using This Silver

### 2.1 `consumable.ai_exposure` (389 rows, ALREADY BUILT)

| Derived Field | Formula | Observed Range |
|---|---|---|
| `stat_res` | `MIN(11 - exposure_score, 10)` | 1–10 (mean 5.80, median 6.0) |
| `boss_ai_score` | `MAX(exposure_score, 1)` | 1–10 (mean 5.20, median 5.0) |
| `soc_code` | passthrough from Silver | 389 distinct |
| `exposure_score`, `rationale`, `category`, `occupation_title` | passthrough | — |

Status: built, DQ-signed-off, covered by `governance/eda/gold-ai-exposure-eda.md`. Row count gate 370–409 currently passing at 389.

### 2.2 Backfill into `consumable.program_career_paths` (626,406 rows)

Already wired via LEFT JOIN on `soc_code`. Populates `stat_res` and `boss_ai_score` on rows where the mapped SOC is in the 389 covered occupations. Rows where the SOC is outside the 389 receive NULL on both columns — the frontend currently renders these as "unknown AI exposure" in the Fight AI boss screen.

### 2.3 Backfill into `consumable.career_branches` (15,944 rows)

Same pattern. Branch deltas for AI resilience are computed when both the source SOC and the target SOC are in the 389 covered set.

### 2.4 MCP tool `get_ai_exposure(soc_code)` — LIVE

Reads `consumable.ai_exposure`, returns `{soc_code, occupation_title, exposure_score, stat_res, boss_ai_score, rationale, category}`. Powers:
- The **RES stat tile** on the career card
- The **Fight AI boss card** in the Gauntlet screen
- The **Gemma Take** tooltip (quotes the `rationale` verbatim)

---

## 3. Proposed Additional Gold Products / Enhancements (Ranked)

### Tier 1 — MANDATORY (auto-generate spec)

| # | Data Product | Description | Source Tables | Key Metric | Why It Matters |
|---|---|---|---|---|---|
| T1-1 | **`consumable.ai_exposure`** | 389-row shaped table with `stat_res` + `boss_ai_score` derived, rationale carry-through | `base.karpathy_ai_exposure` | `stat_res`, `boss_ai_score` | **Already built, signed off, live in MCP.** No new spec — document as the discharged Tier-1 obligation. |

**Verification criteria:** `SELECT COUNT(*) FROM consumable.ai_exposure = 389`; `stat_res BETWEEN 1 AND 10` for every row; `boss_ai_score BETWEEN 1 AND 10` for every row; `stat_res + boss_ai_score = 11` for every row; every `soc_code` is present in `consumable.occupation_profiles`. **All currently passing** per `governance/eda/gold-ai-exposure-eda.md`.

### Tier 2 — HIGH VALUE, MODERATE EFFORT (propose to user)

| # | Data Product | Description | Source Tables | Key Metric | Why It Matters |
|---|---|---|---|---|---|
| T2-1 | **`consumable.ai_exposure` + `confidence_tier` column** | Add `confidence_tier ∈ {high, medium, low}` derived from `soc_resolved_method`: direct→high (243), broad_expansion→medium (110), title_match→low (36). Currently this provenance is dropped during Silver→Gold promote. | `base.karpathy_ai_exposure` | `confidence_tier` | Lets the frontend badge "estimated from broad code" on the RES stat tile, matches the treatment already used for BEA RPP (`verification_status`) and College Scorecard (`confidence_tier`). Low-effort additive column, non-breaking. |
| T2-2 | **`consumable.ai_exposure_category_rollup`** | Pre-aggregated 25-row table: one row per Karpathy category with `mean_exposure`, `p25_exposure`, `p75_exposure`, `count_occupations`. | `base.karpathy_ai_exposure` | category-level percentiles | Enables LLM to answer "which career fields are most AI-safe?" without computing on the fly. Also powers a potential "pick by field" onboarding screen. |
| T2-3 | **`consumable.ai_exposure_with_tasks` (join to O*NET)** | Join `base.karpathy_ai_exposure.soc_code` to `base.onet_task_statements.soc_code` to expose task-level context alongside the occupation-level score. Enables the Gemma agent to quote specific at-risk tasks. | `base.karpathy_ai_exposure`, `base.onet_*` | per-SOC task list + exposure | The PRD's Fight AI boss UI calls for "specific tasks being automated" not just a number. O*NET has 798 SOCs with tasks; intersected with Karpathy's 389 matched SOCs we expect ~370 SOCs with both. |
| T2-4 | **`consumable.ai_exposure_ranked`** | Dense-ranked occupations by exposure_score within and across Karpathy categories (percentile ranks, top/bottom quartile flags). | `base.karpathy_ai_exposure` | `exposure_pctile`, `is_top_quartile`, `is_bottom_quartile` | Powers "most/least AI-exposed occupation in your field" LLM answers. Supports the reveal screen's comparative framing. |

### Tier 3 — EXPLORATORY / FUTURE

| # | Data Product | Description | Dependency | Why It Matters |
|---|---|---|---|---|
| T3-1 | **Confidence intervals on exposure_score** | Re-score each occupation K=5 times with Gemma at temperature > 0, emit mean + 95% CI. Store as `exposure_score_mean`, `exposure_score_ci_low`, `exposure_score_ci_high`. | Gemma/Ollama scoring harness (new) | Karpathy's single-shot LLM score has no confidence estimate. Adding CIs surfaces which occupations the model is certain about vs. ambivalent. Post-hackathon only. |
| T3-2 | **Time-series `ai_exposure_history`** | Store yearly re-scorings with `score_vintage` column; SCD2-like. | Multi-year Gemma re-scoring cadence | Allows "my occupation's exposure jumped from 4 to 7 since 2024" narratives. Currently the data is a static 2024 snapshot; no meaningful history exists. |
| T3-3 | **Join to Karpathy rationale topic tags** | Run Gemma topic extraction over the 342 rationales to produce a tag vocabulary (e.g., "code-generation", "document-review", "diagnostic-imaging"). Add `rationale_tags[]` column. | Gemma topic extraction pipeline | Enables the Fight AI boss to cluster students by the KIND of automation threat, not just the magnitude. |
| T3-4 | **`consumable.ai_exposure_vs_earnings`** | Join to `consumable.career_outcomes` to plot exposure_score × earnings_1yr_median. Computes a `vulnerability_index` = exposure × earnings (high-paying + high-exposed = biggest disruption risk). | `consumable.ai_exposure`, `consumable.career_outcomes` | Journalistic-strength insight for the demo narrative ("these high-paying careers are most at risk"). Low effort — two-table join. |

### Tier 4 — COVERAGE EXPANSION (see §5)

A separate track — treated as its own program below because it materially changes the source data rather than reshaping it.

---

## 4. How Gemma Uses This via MCP for the Fight AI Boss

**Current call pattern (per `src/mcp_server/futureproof_server.py` lines 51–62, 381–403, 836):**

1. Frontend passes a SOC code (derived from the user's school+major selection via CIP→SOC crosswalk).
2. Gemma invokes `get_ai_exposure(soc_code="XX-XXXX")`.
3. MCP queries `consumable.ai_exposure` and returns `{soc_code, occupation_title, exposure_score, stat_res, boss_ai_score, rationale, category}`.
4. Frontend renders:
   - `stat_res` → the fifth spoke of the pentagon chart (`PentagonChart.tsx`)
   - `boss_ai_score` → the Fight AI boss strength bar (`BossFightCard.tsx`)
   - `rationale` → the "Gemma's Take" body text under the boss (`GemmaTake.tsx`)
   - `category` → boss fight filter / grouping

**Current grounding:** The system prompt for Gemma already includes the semantic definition of `exposure_score`, `stat_res`, and `boss_ai_score`. The invariant `stat_res + boss_ai_score = 11` is documented in the tool description.

**What Gemma CANNOT do today that Tier 2 enhancements would unlock:**

| Question | Blocked By | Fix |
|---|---|---|
| "How confident is this exposure score?" | `soc_resolved_method` is not returned | T2-1 (`confidence_tier`) |
| "Which specific tasks in my job are most at risk?" | No task-level join | T2-3 (O*NET join) |
| "Is my career field more or less AI-exposed than average?" | No category aggregates | T2-2 (category rollup) |
| "How does my exposure compare to the highest-exposed occupation?" | No ranking fields | T2-4 (ranked table) |
| "What about occupations Karpathy didn't score?" (443 of 832 cases) | Coverage gap | §5 track |

**Evaluation set implication:** The eval set for the MCP zone must include AT LEAST 5 case categories for `get_ai_exposure`:
1. **Point lookup** (15 cases) — e.g., "What's the AI exposure of Financial Analysts (13-2051)?"
2. **Comparison** (10 cases) — "Compare exposure of Nurses vs Paralegals"
3. **Ranking** (8 cases) — "Top 5 most AI-exposed healthcare occupations"
4. **Trend / category** (8 cases) — "Which field has the safest average exposure?"
5. **Edge case** (9 cases) — unresolved SOC, NULL category, stat_res floor at 10, missing-coverage fallback (SOC not in 389 → graceful null)

---

## 5. Coverage Gap: 389 / 832 = 46.8%

### 5.1 The Gap in Numbers

| Table | SOCs | Coverage |
|---|---|---|
| `consumable.occupation_profiles` (BLS OOH) | 832 | baseline |
| `consumable.onet_work_profiles` (O*NET) | 798 | 95.9% of BLS |
| `consumable.ai_exposure` (Karpathy) | 389 | **46.8% of BLS** |

**Effect on the user experience:** When a student picks a school+major whose CIP→SOC crosswalk lands on one of the 443 uncovered occupations, the career card shows NULL for `stat_res` and `boss_ai_score`. The Fight AI boss card shows the "no data" fallback (already handled in `BossFightCard.tsx`). This is the single largest functional gap in the pentagon.

### 5.2 Why the Gap Exists

Karpathy scored 342 occupations chosen from a **single BLS OOH snapshot** (reportedly 2023 or earlier). The gap has three components:

1. **Non-OOH SOCs** — BLS Employment Projections covers some SOCs not in the OOH booklet; Karpathy didn't see them.
2. **Military / "All Other" occupations** — ~93 O*NET SOCs in the "All Other" / "Military" bucket that Karpathy skipped on principle.
3. **Post-2023 SOC additions** — small drift in the SOC taxonomy.

After Silver transformation, 30 of Karpathy's 342 Bronze rows are themselves stranded (`bls_match = false`): 6 major-group broad codes (XX-X000) with no BLS detailed match + 24 unresolvable null-SOC titles. These would be re-capturable if Karpathy (or Gemma) re-scored at the detailed-SOC level.

### 5.3 Mitigation Options (Ranked)

| # | Option | Effort | Coverage Gain | Confidence |
|---|---|---|---|---|
| M1 | **Gemma backfill** — run Gemma at temperature 0 on the 443 uncovered BLS SOCs using Karpathy's published rubric. Produce `exposure_score` + `rationale` in the same schema. Tag rows `source_method = 'gemma_backfill'` to distinguish from Karpathy originals. | Medium (2–3 days with Ollama E4B or OpenRouter 26B MoE) | **+443 SOCs → 832 / 832 = 100%** | Medium (Gemma ≠ GPT-4; score calibration may drift) |
| M2 | **Broad-code soft expansion** — for BLS SOCs whose 6-char prefix matches a scored Karpathy broad code that currently has `bls_match = false` (6 such), propagate the broad score with `soc_resolved_method = 'unresolved_fallback'`. | Low (1 day, pure Silver logic change) | +0 to +30 SOCs | Low-medium — we already rejected these in Silver for good reason |
| M3 | **Graceful MCP fallback** — when `get_ai_exposure(soc_code)` misses, compute a category-mean exposure from the Karpathy category the SOC belongs to (via BLS major-group → nearest Karpathy category map). Return with `source_method = 'category_mean_fallback'` + explicit caveat in rationale. | Low (MCP-only change) | Covers all 443 with low-confidence estimate | Low — hides the gap without fixing it |
| M4 | **Accept the gap** — document it, surface "no data" cleanly in UI, plan Karpathy-v2 ingestion when published. | Zero | None | N/A |
| M5 | **Hybrid: M3 now + M1 spec'd for post-hackathon** — graceful fallback in time for demo, Gemma backfill afterward. | Low now / Medium later | 100% display coverage / 100% data coverage | Staged |

**Recommendation:** **M5 (hybrid).** Ship the MCP category-mean fallback before demo day (it's a 1-day MCP-only change and materially improves the demo), and commit to the Gemma backfill spec as the headline post-hackathon deliverable for this source. The Gemma backfill is also a compelling narrative for the Kaggle submission — "Gemma scoring Gemma-adjacent tasks at zero marginal cost."

---

## 6. Cross-Entity Coverage Matrix

| Attribute | Entities Reporting | Coverage | Quality |
|---|---|---|---|
| `exposure_score` (0–10) | 389 / 832 BLS SOCs (46.8%) | **gap** | High on covered rows (mean 5.20, full 1–10 range exercised) |
| `rationale` (≥297 chars) | 389 / 389 covered rows (100%) | complete | High — all unique, grammatically complete |
| `category` (Karpathy taxonomy) | 389 / 389 covered rows (100%) | complete | Medium — Karpathy's 25 categories are project-specific, not standard BLS majors |
| `soc_resolved_method` (confidence) | 389 / 389 covered rows (100%) | complete | High — but dropped during Silver→Gold promote (T2-1 fixes this) |
| Task-level AI exposure | 0 / 798 O*NET SOCs (0%) | **missing** | Would require a separate Gemma scoring pass over 19,000+ O*NET task statements |
| Geographic AI exposure variation | 0 states (0%) | **missing** | Karpathy is occupation-only; no state × exposure data exists |
| Time-series AI exposure | 1 vintage (2024) | single snapshot | No historical scores exist |

---

## 7. External Data Opportunities

| External Source | Join Key | What It Unlocks | Effort | Priority |
|---|---|---|---|---|
| **OpenAI / OECD AI Occupational Exposure Indices** (Felten, Eloundou, Autor) | SOC code | Triangulate Karpathy's LLM-generated score with peer-reviewed academic indices. Produces a `consensus_exposure` or `exposure_disagreement` metric. | Medium — need to acquire crosswalk + handle differing SOC vintages | Medium |
| **BLS Automation Potential** (hypothetical — BLS has not published this directly; Oxford Frey & Osborne is the closest) | SOC code | Historical baseline ("Frey 2013 said 47%, Karpathy 2024 says X") | Medium | Low-medium — adds historical anchor but blurs the "Gemma-powered" narrative |
| **O*NET Work Activities** (already ingested as `base.onet_work_activities`) | SOC code | Tag each occupation with the specific activities most at risk (e.g., "generating written reports" is high-exposure regardless of occupation). Feeds T2-3 Tier 2 product. | Low — data already in pipeline | High |
| **Karpathy GitHub repo rubric + prompt templates** (referenced in `domain/sources/karpathy_ai_exposure.yaml`) | N/A — meta | Enables the Gemma backfill (M1) to use identical prompt structure, preserving score calibration. | Low — just reading a repo | **Blocker for M1 backfill** |
| **BLS Employment Projections (Matrix format)** | SOC code | Weight exposure scores by projected employment (2024→2034). A high-exposure occupation that's also shrinking is doubly at risk. Produces a `labor_market_risk_index`. | Medium — BLS matrix already partly in `raw-bls-ooh` but not the projection weighting | Medium |

---

## 8. Coverage Gaps & Risks

| Gap | Impact | Mitigation |
|---|---|---|
| 443 BLS SOCs with no Karpathy score | `stat_res` / `boss_ai_score` NULL for ~53% of career paths. Student experience degrades when their major maps to an uncovered SOC. | M5 hybrid (§5.3) |
| 30 `bls_match = false` Silver rows (6 broad codes + 24 title-unresolvable) | These 30 Bronze occupations are scored but orphaned. Their exposure_scores + rationales exist in Silver but never reach Gold. | Accept for now; revisit if Gemma backfill covers the same territory |
| 25 Karpathy categories ≠ standard BLS major groups | Any external join that expects 2-digit BLS major groups will fail without a mapping table. | Build `glossaries/karpathy_category_to_bls_major_group.yaml` as a Tier 2 dependency |
| Single-shot LLM scores (no CI) | Point estimates shown to users as if authoritative. | T3-1 (confidence intervals) post-hackathon |
| No temporal dimension | Cannot show "exposure trend over time" | T3-2 (multi-vintage scoring) post-hackathon |
| Karpathy rationales are English-only | Non-English frontend loses fidelity if translated | Out of hackathon scope |
| Rationale prompt injection risk | Rationales are served verbatim to the LLM; a crafted rationale could manipulate downstream Gemma reasoning | P1 Silver DQ rule (already covered — `rationale` content is validated length + non-null, but content-safety scanning is not enforced). Flag for adversarial-audit review. |

---

## 9. AI-Ready Considerations

**Shapes the LLM needs:**
- `exposure_score` (scalar) — for the pentagon math
- `rationale` (prose) — **the single most load-bearing field**; users quote it directly
- `confidence_tier` (enum) — **NOT currently in Gold** (T2-1)
- `category` (enum) — for grouping comparisons
- Pre-computed percentiles (T2-4) — saves the LLM from doing arithmetic over 389 rows

**Pre-aggregations that reduce LLM work:**
- Category means (T2-2)
- Percentile ranks (T2-4)
- A 25×3 matrix of category × `{mean, p25, p75}` for fast "how does my field compare" answers

**Natural language context to ship alongside the data:**
- "Higher exposure_score = more automation risk. Range 0–10."
- "`stat_res = 11 − exposure_score` (capped at 10). Shown as 'AI Resilience' stat."
- "`boss_ai_score = MAX(exposure_score, 1)`. Shown as Fight AI boss strength."
- "Karpathy's 2024 scoring pass; no updates since."
- "43.8% of BLS occupations are uncovered — return gracefully when missing."

**Grounding that belongs in the MCP system prompt (for MCP zone):**
- The inverse invariant (`stat_res + boss_ai_score = 11`)
- The coverage limitation (389/832)
- The five Karpathy rubric anchors (0 = no exposure, 10 = full displacement)
- The provenance distinction (direct / broad_expansion / title_match) after T2-1 ships

---

## 10. Chat Agent Design Considerations (Silver → Gold preliminary)

The MCP server is already live; the forward-looking notes here inform the next MCP iteration after Tier 2 Gold enhancements land.

**Expected question classes for `get_ai_exposure` and its successors:**

| Class | Example | Tool Required | Currently Works? |
|---|---|---|---|
| Point lookup | "What's the AI exposure of 13-2051?" | `get_ai_exposure` | Yes |
| Comparison | "Is a nurse or a paralegal more AI-safe?" | `get_ai_exposure` × 2 calls | Yes (two calls) |
| Ranking within field | "Top 3 most AI-exposed jobs in healthcare" | `get_ai_exposure_ranked` | **No — needs T2-4** |
| Category rollup | "Which field is most AI-safe on average?" | `get_category_exposure_rollup` | **No — needs T2-2** |
| Task-level | "Which tasks in my occupation are most automatable?" | `get_ai_exposure_with_tasks` | **No — needs T2-3** |
| Coverage edge | "What's the AI exposure of Military Careers?" | `get_ai_exposure` → graceful null | Partial — returns null, no explanation |
| Confidence edge | "How reliable is this score?" | needs `confidence_tier` | **No — needs T2-1** |
| Invariant | "If AI resilience is 7, what's the boss score?" | pure derivation, no tool call | Yes (LLM math) |

---

## 11. Recommended Spec Order

The Silver→Gold transition for Karpathy is **already functionally discharged** — the Tier-1 gold product is live. The backlog should be read as **Gold enhancement specs**, not foundational work.

1. **No-op formal closure** — emit zone-transition approval for Silver→Gold marking the existing `consumable.ai_exposure` as the discharged Tier-1 obligation. Reference this insight report.

2. **`gold-ai-exposure-confidence-tier`** (T2-1) — additive column. Non-breaking. 0.5 day.

3. **`gold-ai-exposure-category-rollup`** (T2-2) — new 25-row aggregate table. 1 day.

4. **`gold-ai-exposure-ranked`** (T2-4) — adds `exposure_pctile`, `is_top_quartile` to the existing 389-row table or as a new wide view. 1 day.

5. **`gold-ai-exposure-with-tasks`** (T2-3) — new joined view; depends on `base.onet_task_statements` being ready (it is). 2 days.

6. **`mcp-ai-exposure-fallback`** (M3 mitigation) — MCP-only change to emit category-mean fallback when the SOC is outside the 389. 1 day. **Ship before demo.**

7. **`gold-ai-exposure-vs-earnings`** (T3-4) — journalistic Gold view for demo narrative. 1 day.

8. **(Post-hackathon) `spike-gemma-ai-exposure-backfill`** (M1) — Gemma re-scores the 443 uncovered BLS SOCs. Produces `base.gemma_ai_exposure_backfill` + merges into `consumable.ai_exposure` with `source_method` tag. 2–3 days.

9. **(Post-hackathon) `gold-ai-exposure-confidence-intervals`** (T3-1) — multi-shot Gemma scoring for CI estimates.

10. **(Post-hackathon) `gold-ai-exposure-history`** (T3-2) — when a second Karpathy (or Gemma) vintage lands.

### Priority Cut-Line for Hackathon Demo Day

**Must ship:** 1 (closure), 2 (confidence_tier), 6 (MCP fallback). These three alone resolve the two most visible UX issues (NULL stat on 53% of career paths; no confidence signal on low-quality matches).

**Should ship:** 3 (category rollup), 4 (ranked), 7 (vs-earnings) — each enables a compelling demo query class.

**Nice to have:** 5 (O*NET tasks) — richest data product but the highest effort in this list.

**Out of scope for hackathon:** 8, 9, 10 (everything marked post-hackathon).

---

## Appendix A: DQ Run Note

`governance/dq-results/silver-base-karpathy-ai-exposure-20260409T202607Z.json` shows the PASS run (23/23, 100%).

`governance/dq-results/silver-base-karpathy-ai-exposure-20260409T203241Z.json` shows an earlier 17/23 FAIL run (P0 gate did NOT pass that run — 57 grain-uniqueness violations observed, which was the surfacing event that drove the broad-to-broad exact-match fix in the transformer). The subsequent PASS run confirms the fix.

This is worth flagging because the final scorecard at `governance/dq-scorecards/silver-base-karpathy-ai-exposure-scorecard.md` references the later Run ID `e830d061` as the authoritative PASS record. Any consumer reading only the scorecard sees 100% compliance; any consumer scanning the dq-results directory sees two runs and must disambiguate. **Recommendation:** document the superseded run as a known learning in the pipeline state file (already tracked in `governance/pipeline-state/silver-base-karpathy-ai-exposure-pipeline.json`).

---

*End of Insight Report.*
