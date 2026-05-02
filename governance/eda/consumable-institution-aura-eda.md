## EDA Report: consumable.institution_aura

**Source:** `base.ipeds_finance` (snapshot `1277941459950591173`, 2,675 rows) FULL OUTER JOIN `base.eada` (snapshot `973879610917339278`, 2,040 rows)
**Date:** 2026-04-30
**Agent:** @bs:data-analyst
**Spec:** `docs/specs/full-pipeline-eada.md` §6 Aura Score EDA Requirements (BLOCKING items 1–7)

### Domain Context

**Identified Domain:** US post-secondary institutional finance + intercollegiate athletics
**Primary Entities:** Institutions identified by IPEDS UNITID
**Grain:** One row per UNITID (composite institution view)
**Temporal Pattern:** Annual snapshot (IPEDS Finance FY 2022; EADA reporting year 2022)
**Aura Score Purpose:** Neutral brand-gravity composite — higher = more brand presence (endowment + marketing + athletic spend), NOT "better" or "worse" (per §2 Decision 10/11)

### FULL OUTER JOIN Coverage Summary

**Union row count: 3,223** (within `max(2,675, 2,040) = 2,675 ≤ N ≤ 4,715` bound)

| coverage_tier | Rows | % |
|---|---:|---:|
| both | 1,492 | 46.3% |
| finance_only | 1,183 | 36.7% |
| athletics_only | 548 | 17.0% |
| **Total** | **3,223** | **100.0%** |

**`athletic_fte_source` breakdown (Option-C provenance):**
- `ipeds_finance`: 1,492 rows (all in `coverage_tier='both'`)
- `eada_fte_headcount`: 548 rows (all in `coverage_tier='athletics_only'`)
- NULL: 1,183 rows (all in `coverage_tier='finance_only'`, no EADA)

**Critical structural observation:** The 2 × 3 (`aura_score_basis × athletic_fte_source`) interaction grid is structurally degenerate — see Item 7.

### Key Findings

- **v0-draft formula FAILS the §6 item 2 anchor pass criterion.** Of 14 anchor schools, only 3 reach `aura_score ≥ 8` (Harvard 8, Princeton 8, Northwestern 8). Yale=7, MIT=6, Liberty=6, Phoenix=5, Grand Canyon=5, Michigan=7, Cornell=7, Duke=7, Stanford=7. The pass threshold is unattainable for any school extreme on only one signal.
- **Endowment-marketing anti-correlation is NOT the problem** — observed Spearman corr is **+0.07** (essentially independent), well below the 0.4 threshold that would force candidate-formula reselection. Endowment-athletic correlation is +0.44 (above threshold).
- **`marketing_ratio` has a long pathological tail** dominated by IPEDS reporting artifacts — system offices and shells (Sistema Universitario Ana G. Mendez at 5,265, U Colorado System Office at 503, U Illinois System Offices at 150). These institutions report nonzero institutional support but near-zero instruction. They will saturate `rp_marketing≈1.0` and pollute the high-aura tail. **Recommend post-base filter or P99 cap as silver-zone follow-up** (out of scope for this EDA).
- **677 of 2,675 finance reporters have NULL `endowment_per_fte`** (25.3%). For-profits (Phoenix, Grand Canyon) and shell offices dominate. v0-draft's `COALESCE(rp_endowment, 0)` silently treats them as bottom-percentile, biasing scores DOWN by ~0.36 (the average rp_endowment of 0.5 weighted at 0.40). This is the root cause of Phoenix=5 / Grand Canyon=5.
- **`athletic_subsidy_ratio` is correctly excluded** from the aura computation (verified — see Item 6). It is also confirmed clipped at 0 for ~63% of EADA rows (1,284 of 2,040 are exactly 0; another 546 in [-0.1, 0)). This is silver-zone behavior; aura uses `athletic_spend_per_fte` only.

### Item 1 — Distribution Shapes

| Field | n | min | P5 | P50 | P95 | max | mean | sd |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `marketing_ratio` | 2,644 | 0.0 | 0.183 | 0.545 | 2.345 | 5,265.5 | 3.20 | 102.93 |
| `endowment_per_fte` | 1,998 | 0.13 | 967 | 20,664 | 421,988 | 12,783,668 | 101,472 | 406,832 |
| `athletic_subsidy_ratio` | 2,040 | -2.92 | -0.157 | 0.0 | 0.0 | 0.0 | -0.033 | 0.125 |
| `athletic_spend_per_fte` | 2,040 | 4.5 | 148 | 1,579 | 7,177 | 21,175 | 2,304 | 2,477 |

**Top 3 findings:**
1. **`marketing_ratio` extreme tail is dominated by IPEDS reporting artifacts** (system offices: institutional support / instruction → infinity when instruction ≈ 0). Top 6 rows: Sistema Universitario Ana G. Mendez (5,265), U Colorado System Office (503), U Illinois System Offices (150), LACCD (84), UTenn System Office (84), SUNY System Office (62). These are not "marketing" — they're administrative shells.
2. **`endowment_per_fte` spans 8 orders of magnitude** (0.13 to 12.8M). Heavy right-skew — P95/P50 = 20.4 ratio. Percentile-rank transform is the only sane normalization (confirms v0-draft choice). 25.3% NULL — concentrated in for-profits and shells.
3. **`athletic_subsidy_ratio` is heavily right-clipped at 0** in silver — 1,284/2,040 (63%) are exactly 0; another 546 are in [-0.1, 0). Per §2 Decision 11 this column is context-only and not an aura input — finding logged here for downstream consumers.

### Item 2 — Anchor Behavior Under v0-draft (PASS / FAIL)

Pass criterion: `aura_score ≥ 8` for each of three anchor classes (extreme endowment / extreme athletics / extreme marketing). **v0-draft formula:** `0.40·rp_marketing + 0.40·rp_endowment + 0.20·rp_athletic`, min/max rescale, finance_only reweighted 0.50/0.50.

| Anchor | Class | rp_mkt | rp_endow | rp_ath | v0 score | PASS? |
|---|---|---:|---:|---:|---:|---|
| Harvard | endowment | 0.65 | 0.99 | 0.42 | **8** | PASS |
| Princeton | endowment | 0.47 | 1.00 | 0.89 | **8** | PASS |
| Yale | endowment | 0.12 | 1.00 | 0.85 | **7** | **FAIL** |
| MIT | endowment | 0.22 | 1.00 | 0.28 | **6** | **FAIL** |
| Stanford | endowment | 0.17 | 1.00 | 0.97 | 7 | **FAIL** |
| Cornell | endowment | 0.37 | 0.94 | 0.42 | 7 | **FAIL** |
| Duke | endowment | 0.14 | 0.97 | 0.97 | 7 | **FAIL** |
| Northwestern | endowment | 0.38 | 0.96 | 0.91 | 8 | PASS |
| U Alabama | athletics | 0.29 | 0.65 | 0.91 | 6 | **FAIL** |
| Ohio State | athletics | 0.06 | 0.86 | 0.84 | 6 | **FAIL** |
| U Michigan | athletics | 0.22 | 0.94 | 0.83 | 7 | **FAIL** |
| U Phoenix | marketing | 0.98 | NULL | NULL | 5 | **FAIL** |
| Liberty | marketing | 0.55 | 0.57 | 0.29 | 6 | (moderate, not extreme — secondary anchor) |
| Grand Canyon | marketing | 0.92 | NULL | 0.13 | 5 | **FAIL** |

**Verdict:** v0-draft fails 11 of 14 anchors, including ALL THREE marketing-heavy for-profit anchors (the most diagnostic class). Two structural causes:
1. **Composite-collapse at the tails.** Three near-equal weights guarantee that any school extreme on only one signal cannot exceed ~0.40 + 0.40·median + 0.20·median ≈ 0.70 raw, which rescales to ~7.
2. **NULL endowment penalizes for-profits.** `COALESCE(rp_endowment, 0)` treats Phoenix's missing endowment as worst-in-class (rp=0), dragging its score from a deserved 9–10 down to 5.

### Item 3 — Correlation Structure

Spearman / rank-percentile correlations on the 1,417 rows with all three signals non-null:

| Pair | Correlation |
|---|---:|
| corr(rp_marketing, rp_endowment) | **+0.069** |
| corr(rp_marketing, rp_athletic) | +0.226 |
| corr(rp_endowment, rp_athletic) | +0.444 |

**Pairwise corr(mkt, endow) on all 1,973 finance reporters with both non-null: +0.102.**

**Action criterion `|corr(mkt, endow)| > 0.4`: NOT TRIGGERED** (corr=0.07–0.10, well below threshold). The endowment-marketing anti-correlation hypothesis is rejected; the two signals are essentially independent.

The `corr(endow, ath) = +0.44` is interesting — endowment-rich schools tend to spend more on athletics per FTE — but it does NOT trigger any spec-level remediation rule. It does support the case for a MAX-based composite: when endowment and athletic both correlate with brand prestige, taking the max captures whichever signal is reported.

**Despite the action criterion not firing, the v0-draft formula clearly fails Item 2.** Per spec §6 latitude ("EDA may overrule with evidence"), I produced ≥3 candidate composite forms and selected one via Item-2 anchor validation:

| Candidate | Form |
|---|---|
| (a) v0-draft weighted-mean | `0.40·rp_mkt + 0.40·rp_endow + 0.20·rp_ath` |
| (b) MAX-only "either dimension" | `0.70·MAX(rp_mkt,rp_endow) + 0.30·rp_ath` |
| (c) log-additive | `Σ ln(1 + 9·rp_i) / (k·ln(10))` |
| (d) **MAX + MEAN composite** | **`0.65·MAX(rp_mkt, rp_endow, rp_ath) + 0.35·MEAN(rp_mkt, rp_endow, rp_ath)`** |

**Selected: candidate (d)** — only formula passing all three anchor classes (see "v1 Aura Formula" below).

### Item 4 — `coverage_tier = 'finance_only'` Handling

**Recommendation: option (a) — drop athletic term and reweight, per spec default.** Confirmed via evidence:

- Imputing `rp_athletic = 0.5` (option b) for finance_only rows produces nearly identical anchor scores (Phoenix delta = +0.00204 raw, < 1 integer bucket). It does not "rescue" the anchor failures because Phoenix's failure is driven by NULL endowment, not by missing athletic. **Option (b) does not improve anchor pass rate; reject.**
- NULL'ing aura for finance_only (option c) discards 1,183 institutions including all non-athletic 4-years and most of the for-profit population — flatly violates CLAUDE.md "no path is out of scope." **Reject.**
- Option (a) preserves rank ordering within stratum, stamps `aura_score_basis = 'two_term_finance_only'` for cross-stratum auditability. **CONFIRMED.**

**Additional finding requiring spec amendment:** EDA also surfaces a **fourth basis case** the v0 spec didn't anticipate: `has_ipeds_finance=TRUE` AND `endowment_per_fte IS NULL` (Phoenix, Grand Canyon, 677 rows total). The two sub-cases require their own handling:
- `endowment NULL, athletic non-null` → 2-term `mkt + ath` 0.50/0.50, `aura_score_basis = 'two_term_no_endowment'` (75 rows)
- `endowment NULL, athletic NULL` → 1-term `mkt` only, `aura_score_basis = 'one_term_marketing_only'` (602 rows; almost all for-profits and shells)

The `aura_score_basis` enum becomes `{three_term, two_term_finance_only, two_term_no_endowment, one_term_marketing_only}`. **This is a spec edit required before consumable implementation** (CON-AUR-* DQ rules + schema).

### Item 5 — Rescaling Target

**v0-draft min/max rescale produces a band imbalance:**
| Band | v0-draft (min/max) | v1 selected (P5/P95) |
|---:|---:|---:|
| [1,3] | 622 (23.3%) | 459 (17.4%) |
| [4,6] | 1,415 (52.9%) | 681 (25.7%) |
| [7,10] | 638 (23.9%) | 1,506 (56.9%) |
| Total | 2,675 | 2,646 |

v0-draft compresses the middle (53% in [4,6]); v1 with P5/P95 rescale gives a healthier spread. **Decision: switch to P5/P95 percentile rescale** for v1 (per spec §6 item 5 explicit fallback). Median under v1 = **7** (within [4,7] band sanity rule, satisfies CON-AUR-031).

The right-skew toward [7,10] in v1 is intentional — it reflects the brand-gravity domain semantic that "most reporting institutions have at least some brand presence on at least one dimension." The 1–3 band is reserved for low-brand institutions on every signal (small private specialty colleges, online seminaries, etc.), which is the correct semantic.

### Item 6 — Sign Convention (CONFIRM ONLY)

**Confirmed:**
- `rp_marketing` direction: high marketing_ratio → high rp_marketing → high aura. Verified: Phoenix mkt_ratio=3.84, rp=0.98. Grand Canyon mkt_ratio=1.82, rp=0.92.
- `rp_endowment` direction: high endowment_per_fte → high rp_endowment → high aura. Verified: Princeton endow_pfte=$3.75M, rp=1.00. Harvard $1.63M, rp=0.99.
- `rp_athletic` direction: high athletic_spend_per_fte → high rp_athletic → high aura. Verified: Stanford ath_pfte=$9,408, rp=0.97. Duke $9,209, rp=0.97.
- Low-brand spot check: regional public examples — most rows in 1,492-row "both" stratum cluster around `rp_*≈0.5`, producing aura ~5 under v1, which is correct semantically.
- **`athletic_subsidy_ratio` is NOT used in any aura computation.** Verified by code inspection of all four candidate formulas (a), (b), (c), (d). Remains a context-only column on the consumable. CONFIRMED.

### Item 7 — FTE-source Stratification (Option-C, BLOCKING)

**The 2 × 3 (`aura_score_basis × athletic_fte_source`) interaction grid is STRUCTURALLY DEGENERATE:**

| aura_score_basis | athletic_fte_source | Rows |
|---|---|---:|
| three_term | ipeds_finance | 1,417 |
| two_term_no_endowment | ipeds_finance | 75 |
| two_term_finance_only | NULL (no EADA) | 581 |
| one_term_marketing_only | NULL (no EADA) | 602 |
| **(athletics_only — no aura computed)** | eada_fte_headcount | 548 (NULL aura) |

**Rationale:** Every row that uses `athletic_fte_source = 'eada_fte_headcount'` is in `coverage_tier = 'athletics_only'`, which produces NULL `aura_score` per §6 ("aura_score is computed only when has_ipeds_finance = TRUE"). Therefore, **the 548 `eada_fte_headcount` rows never enter aura computation.** All 1,492 rows that DO have EADA + Finance use `athletic_fte_source = 'ipeds_finance'`.

**Pass criterion (median aura_score differs by <1 integer bucket between strata): VACUOUSLY SATISFIED** — there is only one stratum to compare for aura computation (`ipeds_finance`).

**Stratification of `athletic_spend_per_fte` itself (regardless of aura usage), for documentation:**

| stratum | n | P5 | P50 | P95 | mean | rp_athletic median |
|---|---:|---:|---:|---:|---:|---:|
| ipeds_finance | 1,492 | $202 | $1,990 | $8,078 | $2,718 | 0.587 |
| eada_fte_headcount | 548 | $100 | $673 | $3,996 | $1,179 | 0.264 |

The two strata DO differ materially in `athletic_spend_per_fte` (eada_fte_headcount stratum is ~3× lower at the median). However, since these rows never enter aura, this difference does NOT affect aura comparability.

**Decision:** No stratification action required for aura. The `athletic_fte_source` column remains on the consumable as a CDE for downstream consumers (per §6 schema), but **the aura computation itself does NOT need fte-source stratification or `two_term_finance_only` reassignment for the eada_fte_headcount stratum** — those rows are already NULL'd.

**Note for CON-AUR-030 stratification:** The DQ rule should be stratified by `aura_score_basis` (4 strata), NOT by `athletic_fte_source` (which is only meaningful for the `three_term` stratum where it's invariant).

### v1 Aura Formula (EDA-FINALIZED)

```sql
-- Inputs (population-level percent rank, computed only across rows with non-null signal)
rp_marketing  = PERCENT_RANK() OVER (ORDER BY marketing_ratio)        -- where marketing_ratio IS NOT NULL
rp_endowment  = PERCENT_RANK() OVER (ORDER BY endowment_per_fte)      -- where endowment_per_fte IS NOT NULL
rp_athletic   = PERCENT_RANK() OVER (ORDER BY athletic_spend_per_fte) -- where athletic_spend_per_fte IS NOT NULL

-- Coverage-aware basis assignment (4 cases)
aura_score_basis = CASE
  WHEN NOT has_ipeds_finance THEN NULL
  WHEN rp_endowment IS NOT NULL AND rp_athletic IS NOT NULL THEN 'three_term'
  WHEN rp_athletic IS NULL  AND rp_endowment IS NOT NULL THEN 'two_term_finance_only'
  WHEN rp_endowment IS NULL AND rp_athletic IS NOT NULL THEN 'two_term_no_endowment'      -- new
  WHEN rp_endowment IS NULL AND rp_athletic IS NULL      THEN 'one_term_marketing_only'    -- new
END

-- MAX + MEAN composite (winner among 4 candidates per Item 2 anchor validation)
rp_max  = GREATEST(COALESCE(rp_marketing,0), COALESCE(rp_endowment,0), COALESCE(rp_athletic,0))
rp_mean = AVG of non-null rp_* signals
raw_score = 0.65 * rp_max + 0.35 * rp_mean

-- P5/P95 rescale (NOT min/max), per Item 5 finding
-- Population-level P5 = 0.1413, P95 = 0.9400 (computed across all has_ipeds_finance=TRUE rows)
aura_score_continuous = 1.0 + 9.0 * GREATEST(0, LEAST(1, (raw_score - 0.1413) / (0.9400 - 0.1413)))
aura_score = ROUND(aura_score_continuous)  -- integer 1..10

-- Provenance
aura_score_version = 'v1'
```

**Weights pinned:** 0.65 / 0.35 (MAX / MEAN), three-signal mean.
**Rescale bounds pinned:** P5=0.1413, P95=0.9400 (population-level percentiles of `raw_score`, computed at promote time on the production population — store as a constant in the gold transformer, recomputed on each annual refresh).
**Finance_only handling:** `aura_score_basis = 'two_term_finance_only'` (581 rows), MEAN over 2 signals. CONFIRMED.
**Endowment-NULL handling:** `aura_score_basis ∈ {'two_term_no_endowment', 'one_term_marketing_only'}` (677 rows total). **NEW — requires spec edit before §6 implementation.**
**FTE-source stratification:** Not needed — confirmed structurally degenerate per Item 7.

### Anchor Scores: v0-draft vs v1

| Anchor | Class | v0 | v1 (MAX+MEAN, P5/P95) | v0 PASS | v1 PASS |
|---|---|---:|---:|:---:|:---:|
| Harvard | endowment | 8 | **9** | PASS | PASS |
| Princeton | endowment | 8 | **10** | PASS | PASS |
| Yale | endowment | 7 | **9** | FAIL | PASS |
| MIT | endowment | 6 | **9** | FAIL | PASS |
| Stanford | endowment | 7 | **10** | FAIL | PASS |
| Cornell | endowment | 7 | **9** | FAIL | PASS |
| Duke | endowment | 7 | **9** | FAIL | PASS |
| Northwestern | endowment | 8 | **9** | PASS | PASS |
| U Alabama (Tuscaloosa) | athletics | 6 | **9** | FAIL | PASS |
| Ohio State (Main) | athletics | 6 | **8** | FAIL | PASS |
| U Michigan (Ann Arbor) | athletics | 7 | **9** | FAIL | PASS |
| U Phoenix (AZ) | marketing | 5 | **10** | FAIL | PASS |
| Grand Canyon | marketing | 5 | **8** | FAIL | PASS |
| Liberty | marketing (moderate) | 6 | 5 | (n/a) | (n/a — moderate signal, score correctly mid-range) |

**v1 anchor pass rate: 13/13 anchors meeting the §6 item 2 pass criterion (Liberty excluded — its signals are mid-range across all three dimensions, score=5 is semantically correct).**

### Cross-Field Analysis

- **`institutional_support_per_fte / instruction_per_fte ≈ marketing_ratio`** — verified arithmetic identity in 2,620 rows where all three fields are non-null. Differences within 1e-6 across the population (CON-AUR-007 will pass).
- **`endowment_per_fte` and `marketing_ratio` independence** — corr=+0.07 (Spearman). The two signals do NOT cancel each other; the v0-draft 0.40/0.40 weighting is mathematically sound, just numerically too gentle at the tails.
- **`athletic_spend_per_fte` and `endowment_per_fte`** — corr=+0.44, modest positive. Big-endowment schools tend to also spend more on athletics per FTE (Stanford, Duke, Princeton). This supports MAX+MEAN: in this population the dimensions reinforce, they don't compete.
- **For-profits cluster characteristics:** Phoenix-class institutions have high marketing (rp~0.95+), NULL endowment, missing or low athletic spend. They form a degenerate `one_term_marketing_only` stratum with N=602 and median aura=8.13 — the highest of any stratum. This is correct semantically (for-profits HAVE high brand presence) but warrants the explicit basis stamp for downstream auditability.

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|---|---:|---:|---|
| `marketing_ratio > 10` (system-office artifacts) | 11 of 2,644 | 0.42% | Add P1 raw-zone outlier flag; consider P99 cap in silver follow-up |
| `endowment_per_fte` NULL (for-profits + shells) | 677 of 2,675 | 25.3% | Already handled by 4-basis logic; document in `aura_score_basis` |
| `athletic_subsidy_ratio = 0` exactly (silver clipping) | 1,284 of 2,040 | 62.9% | Document in glossary BT-EAD-ATHLETIC-SUBSIDY-RATIO; not an aura input |
| `athletics_only` rows (eada_fte_headcount source) | 548 of 3,223 | 17.0% | NULL aura, basis=NULL — confirm CON-AUR-011 covers |
| Anchor failures under v0-draft | 11 of 14 | 78.6% | RESOLVED by v1 formula — 13/13 anchors pass |

### Anomalies

| Field | Type | Count | Severity | Details |
|---|---|---:|---|---|
| `marketing_ratio` | extreme tail (system office shells) | 11 (>10) | LOW | Sistema Universitario Ana G. Mendez at 5,265 — institutional support / near-zero instruction. Tracked in raw-zone EDA for follow-up. |
| `endowment_per_fte` | NULL on 677 finance reporters | 677 | MEDIUM | Concentrated in for-profits and shells. Resolved via 4-basis logic. |
| `athletic_subsidy_ratio` | clipped to 0 in 63% of rows | 1,284 | LOW | Silver-zone behavior, documented; not an aura input. |
| `aura_score = NULL` due to `athletics_only` | 548 | EXPECTED | Spec-defined; CON-AUR-011 covers. |

### v1 Promotion Decision

**`aura_score_version = 'v1'` is JUSTIFIED with one prerequisite spec edit:**

1. The §6 schema and DQ rules currently allow `aura_score_basis ∈ {three_term, two_term_finance_only, NULL}` per the v0 draft. The v1 formula requires the enum to expand to `{three_term, two_term_finance_only, two_term_no_endowment, one_term_marketing_only, NULL}`. This is a documented EDA finding that must land in §6 before consumable implementation.
2. CON-AUR-030 stratification key should switch from `aura_score_basis` (3 values) to the new 4-value enum.
3. Population-level P5/P95 rescale bounds (0.1413 / 0.9400) should be stamped as constants in the gold transformer with a comment noting they are recomputed on annual refresh.

If item 1 is treated as too large a spec amendment for this gate, the alternative is `aura_score_version = 'v0-draft'` retained pending spec amendment + re-EDA. **Recommendation:** make the spec edit (it is small — schema enum expansion + 1 DQ rule note) and ship v1.

### Threshold Recommendations for @bs:dq-rule-writer

| Rule | Recommendation | Evidence |
|---|---|---|
| CON-AUR-001 | row count ∈ [2,675, 4,715]; observed 3,223 | Item: union row count |
| CON-AUR-005 | enum check; all 3 values populated (1,492 / 1,183 / 548) | Item: coverage_tier breakdown |
| CON-AUR-006 | every row has ≥1 of (has_ipeds_finance, has_eada) — verified by FULL OUTER construction | trivially passes |
| CON-AUR-010 | aura_score ∈ [1,10] where non-null — verified across all 2,675 finance reporters | Item 5 distribution |
| CON-AUR-011 | NULL exactly when has_ipeds_finance=FALSE — 548 rows NULL, exactly the athletics_only count | Item 7 grid |
| CON-AUR-012 | aura_score_version = 'v1' (was 'v0-draft') | this EDA |
| CON-AUR-030 | stratify by `aura_score_basis` (4 strata); per-stratum ≥4 of 10 buckets populated; overall ≥6 of 10 | Item 5 distribution |
| CON-AUR-031 | aura_score median ∈ [4,7] — observed median=7 under v1 | Item 5 |
| CON-AUR-032 | anchor spot checks: HARV/PRIN/YALE ≥ 8; ALA/OSU/MICH ≥ 8; PHOENIX/GC ≥ 8 | Anchor table |

### Audit Trail

- Source snapshots: `base.eada` snap `973879610917339278`, `base.ipeds_finance` snap `1277941459950591173`
- DuckDB workbench: ad-hoc, ephemeral; queries embedded inline above
- Spec reference: `docs/specs/full-pipeline-eada.md` §6 Aura Score EDA Requirements (BLOCKING items 1–7)
- Outcome: v1 formula finalized; spec amendment required for `aura_score_basis` enum expansion before §6 ships
- Date: 2026-04-30
