# Adversarial Audit: gold-futureproof-engine

**Date:** 2026-04-09
**Auditor:** @adversarial-auditor
**Spec:** docs/specs/gold-futureproof-engine.md
**Tables:** consumable.program_career_paths (626,406 rows), consumable.career_branches (15,944 rows)
**Audit Method:** Independent warehouse queries against production Iceberg tables, source data cross-referencing, golden dataset verification, derivation formula spot-checks

---

## Risk Register

### RISK-001: Golden Dataset Chain 1 Contains Multiple Fabricated Values (CRITICAL)

The golden dataset at `governance/golden-datasets/gold-futureproof-engine-golden.json` claims to verify "ISU Business Admin -> Financial Analyst" with unitid=151801, cipcode=52.02, soc_code=13-2051. **Every major input value in this chain is wrong.**

**Fabricated values found:**

| Field | Golden Dataset Claims | Actual Warehouse Value | Discrepancy |
|-------|----------------------|----------------------|-------------|
| institution_name | "Indiana State University" | "Indiana Wesleyan University-Marion" | Wrong institution entirely. ISU is unitid=151324. |
| cip_family_earnings_rank | 0.45 | 0.7197 (for 151801) or 0.1249 (for actual ISU 151324) | Neither matches 0.45 |
| wage_percentile_overall | 0.75 | 0.879 | Off by 17% |
| grw_score_rounded | 6 | 7 | Wrong |
| market_score_rounded | 5 | 7 | Wrong |
| hmn_score_rounded | 4 | NULL (partial O*NET profile) | Not just wrong -- the value does not exist |
| burnout_score_rounded | 6 | NULL (partial O*NET profile) | Same -- fabricated from nothing |

**Additionally:** SOC 13-2051 (Financial and Investment Analysts) does not appear in the crosswalk for CIP prefix 52.02. The crosswalk maps 52.02xx to 43 SOC codes, but 13-2051 is not among them. 13-2051 maps to CIP prefixes 27.03, 30.71, and 52.03/52.08 -- not 52.02. **The entire join chain in this golden dataset entry is impossible.** No row exists at grain (151801, 52.02, 13-2051) in program_career_paths because it cannot exist.

**Verdict:** The AI agent fabricated a plausible-sounding golden dataset verification chain that is verifiably false in at least 7 dimensions. The derivation math shown in the golden dataset is internally consistent (the formulas are applied correctly to the fabricated inputs), which is exactly why this is dangerous -- it looks correct on casual review.

### RISK-002: Golden Dataset Chain 2 References Non-Existent Institution (HIGH)

Chain 2 in the golden dataset uses unitid=999999. There is no institution with unitid=999999 in career_outcomes. This golden dataset entry is untestable -- it describes expected outputs for a row that cannot exist in the pipeline output. The golden dataset DQ rule (GLD-FE-044) is DEFERRED specifically because it cannot validate these fabricated chains.

### RISK-003: Golden Dataset Chain 3 References Non-Existent Career Transition (HIGH)

Chain 3 claims to verify the career branch from SOC 15-1252 (Software Developers) to 15-1256 (Software Quality Assurance Analysts). However:

- SOC 15-1256 does not exist in occupation_profiles (0 rows)
- SOC 15-1256 does not exist in onet_work_profiles (0 rows)
- The transition pair (15-1252, 15-1256) does not exist in career_transitions (0 rows)
- No row exists for this pair in career_branches

The golden dataset claims grw=5, median_annual_wage=$98,000, hmn=3, burnout=7 for SOC 15-1256. These values are fabricated. The actual top related SOC for 15-1252 is 15-1299, not 15-1256.

### RISK-004: Match Quality Semantic Gap -- "full" Does Not Mean Full Data (MEDIUM)

16,410 rows (2.6% of total, 2.8% of "full" rows) have match_quality="full" but stat_hmn IS NULL. This occurs because match_quality is derived from whether the O*NET row *exists* (bls_soc_code IS NOT NULL after LEFT JOIN), but 24 O*NET profiles are "partial" -- the row exists with null HMN/burnout scores.

The consequence: a downstream consumer filtering on match_quality="full" expecting complete pentagon data will get rows with missing HMN and burnout stats. The overall_confidence derivation compounds this -- rows with 2 stats + "full" match quality get classified as "low" confidence, which is correct, but the match_quality label is misleading.

This is not a bug in the transformer code (the logic is implemented as specified). It is a specification-level semantic gap that the AI agent did not flag during design.

### RISK-005: EDA Golden Trace Uses Different Source Values Than Golden Dataset (MEDIUM)

The EDA report traces ISU (unitid=151324) with cip_family_earnings_rank=0.125 and debt_to_earnings_annual=0.627. The golden dataset JSON uses unitid=151801 with cip_family_earnings_rank=0.45 and debt_to_earnings_annual=0.643. These are different institutions with different values, despite both claiming to be "ISU Business Admin." The EDA and the golden dataset are inconsistent with each other and with the spec (which references "Indiana State University").

### RISK-006: No Accuracy DQ Rules for Derived Stat Formulas (MEDIUM)

The chaos monkey report explicitly identifies this gap: no DQ rules verify that stat_ern is correctly derived from its formula, that boss_ceiling_score matches the spec formula, or that grw_delta equals related_grw minus source_grw. The only derivation accuracy rule is GLD-FE-023 (boss_loans = 11 - stat_roi). Range checks (1-10) catch gross errors but not subtle formula mistakes (e.g., swapped weights in ERN, wrong interpolation direction in ROI).

Auditor verification: I manually computed stat_ern and stat_roi for unitid=151324, cipcode=52.02, soc_code=11-1021 and confirmed they match the warehouse values (ERN=5, ROI=8, boss_loans=3). The formulas are correctly implemented. But this was a spot-check of 1 row out of 626,406.

### RISK-007: GLD-FE-040 Failure -- branch_has_full_data Below Threshold (LOW)

The DQ scorecard shows GLD-FE-040 failing: only 92.7% of career_branches rows have branch_has_full_data=True, below the 95% threshold. The branch_has_full_data flag itself is correctly derived (True when both related_grw and related_hmn are non-null; the consistency check shows perfect alignment). The threshold was set too tight for the actual data distribution.

### RISK-008: GLD-FE-044 Golden Dataset Rule is DEFERRED / Broken (LOW)

The golden dataset DQ rule (GLD-FE-044) returns "DEFERRED" as its threshold value, which the DQ runner cannot parse, producing a permanent P0 failure. Even if activated, the golden dataset contains fabricated values (RISK-001 through RISK-003) that would not match warehouse data, so the rule would still fail.

---

## Evidence Demands and Assessment

### RISK-001: Golden Dataset Fabrication

**Evidence demanded:** Show me the actual source data row for the golden dataset's claimed grain (unitid=151801, cipcode=52.02, soc_code=13-2051).

**Evidence provided by auditor:**
- `SELECT * FROM consumable.career_outcomes WHERE unitid=151801 AND cipcode='52.02'` returns: institution_name="Indiana Wesleyan University-Marion", cip_family_earnings_rank=0.7197, not "Indiana State University" with 0.45
- `SELECT * FROM base.cip_soc_crosswalk WHERE LEFT(cipcode,5)='52.02' AND soc_code='13-2051'` returns: 0 rows. 13-2051 is not reachable from CIP 52.02.
- `SELECT * FROM consumable.program_career_paths WHERE unitid=151801 AND cipcode='52.02' AND soc_code='13-2051'` returns: 0 rows. The pipeline correctly produces no such row.
- `SELECT * FROM consumable.onet_work_profiles WHERE bls_soc_code='13-2051'` returns: hmn_score_rounded=NULL, burnout_score_rounded=NULL

**Assessment: MISSING** -- The golden dataset, which is supposed to be the ground-truth verification artifact, is itself a hallucination. All three chains contain values that do not exist in the warehouse. This is the exact failure mode this audit was designed to catch: AI-generated verification comparing AI output to AI-generated expected values, where the expected values are fabricated.

### RISK-002 and RISK-003: Non-Existent Reference Data

**Evidence:** unitid=999999 has 0 rows in career_outcomes. SOC 15-1256 has 0 rows in occupation_profiles and onet_work_profiles. The pair (15-1252, 15-1256) has 0 rows in career_transitions.

**Assessment: MISSING** -- These golden dataset entries are untestable. They describe scenarios that cannot occur in the pipeline. A golden dataset must reference real data.

### RISK-004: Match Quality Semantic Gap

**Evidence:** `SELECT COUNT(*) FROM pcp WHERE match_quality='full' AND stat_hmn IS NULL` returns 16,410. The code at line 294 (`CASE WHEN onet.bls_soc_code IS NOT NULL THEN TRUE ELSE FALSE END AS has_onet`) checks for row existence, not data completeness.

**Assessment: WEAK** -- The spec defines match_quality based on join success (row exists), which is what the code implements. But the spec does not acknowledge that a "successful" O*NET join can still produce null scores. The EDA identifies this (finding 10, anomaly row 6) but the spec was not updated. A downstream consumer relying on match_quality="full" to mean "all occupation data available" would be misled.

### RISK-006: No Derivation Accuracy Rules

**Evidence:** Chaos monkey report, section "Potential Blind Spots," item 2. DQ rules file (`governance/dq-rules/gold-futureproof-engine.json`) has no rules checking stat_ern = ROUND(1 + 9 * (0.6 * cip_family_earnings_rank + 0.4 * wage_percentile_overall)), or boss_ceiling_score = ROUND(10 - 9 * wage_percentile_education_tier), or that delta calculations are correct.

**Auditor spot-check:** I verified 1 row manually and 5 delta calculations. All matched. But this covers <0.001% of data.

**Assessment: WEAK** -- The chaos monkey identified this gap but classified it as P2. For a pipeline where the core value proposition is the derived stats, formula correctness should be P1 at minimum. The only reason I can confirm the formulas work is that I independently recalculated values -- there is no automated rule that would catch a regression.

---

## Controls That Work Well

1. **Grain uniqueness**: 626,406 rows, 626,406 distinct grains. Zero duplicates. The dedup logic works correctly despite 47.8% of pre-dedup grain tuples having duplicates. GLD-FE-001 and GLD-FE-032 validate this. **Assessment: STRONG**

2. **Null propagation**: Zero violations across all null-propagation invariants (ERN null when earnings null, ROI null when DTE null, loans null when ROI null, loans = 11 - ROI when both present). GLD-FE-023, GLD-FE-024, GLD-FE-025, GLD-FE-029 all pass. **Assessment: STRONG**

3. **CIP prefix join coverage**: 91.0% of distinct CIPs matched, 97.1% of rows covered. Matches EDA predictions exactly. Unmatched CIPs are XX.99/XX.00 catch-all categories as expected. GLD-FE-004 and GLD-FE-005 validate this. **Assessment: STRONG**

4. **Stats_available_count and bosses_available_count accuracy**: Zero mismatches when cross-checked against actual non-null stat counts. **Assessment: STRONG**

5. **Overall confidence derivation**: Zero violations of confidence tier criteria. **Assessment: STRONG**

6. **Stat and boss score ranges**: All values in [1, 10] when non-null. Stat_res and boss_ai are 100% null as expected. **Assessment: STRONG**

7. **Career branches delta correctness**: All 5 spot-checked deltas (grw, hmn, wage) are arithmetically correct. branch_has_full_data flag perfectly aligns with actual null patterns (14,786 True all have both related_grw and related_hmn; 1,158 False all have at least one missing). **Assessment: STRONG**

8. **Referential integrity**: All SOC codes trace to crosswalk, all unitids trace to career_outcomes. GLD-FE-030, GLD-FE-031, GLD-FE-043 all pass. **Assessment: STRONG**

9. **Chaos monkey hardening**: 42/45 rules fired across 5 cycles at escalating corruption rates. 93.3% detection rate. 3 silent rules are distribution-level guards with intentional margin. **Assessment: STRONG**

---

## Recommendations

### BLOCKING (Must Fix Before Staff Review)

**B1. Rebuild the golden dataset with verifiable values.**

All three verification chains in `governance/golden-datasets/gold-futureproof-engine-golden.json` reference data that does not exist in the warehouse. The golden dataset must be rebuilt using:

- Chain 1: Use the actual Indiana State University (unitid=151324, cipcode=52.02) and a SOC code that actually appears in the crosswalk for CIP 52.02 (e.g., 11-1021 General and Operations Managers). Populate source_inputs with values queried from the actual warehouse tables.
- Chain 2: Use a real unitid with high debt_to_earnings_annual (query career_outcomes for DTE > 3.0 to find one).
- Chain 3: Use a real career transition pair from career_transitions. The actual best_index=1 related SOC for 15-1252 is 15-1299.

After rebuilding, activate GLD-FE-044 with a parseable threshold and verify it passes.

**B2. Fix GLD-FE-044 threshold.**

The rule currently has `result = 'DEFERRED'` as its threshold, which the DQ runner cannot parse. Once the golden dataset is rebuilt, update the threshold to a numeric check (e.g., `result_count = 0`).

### HIGH PRIORITY (Should Fix Before Staff Review)

**H1. Add derivation accuracy DQ rules (at least P1).**

Add rules that spot-check formula correctness:
- `stats_available_count = (stat_ern IS NOT NULL)::int + ... ` (already passing, but should be an explicit rule)
- `boss_ceiling_score = ROUND(10.0 - 9.0 * wage_percentile_education_tier)` for a sample
- `grw_delta = related_grw - source_grw` when both non-null (career_branches)

The chaos monkey recommended these as P2. I recommend P1 given that derived stats are the core product.

**H2. Document the match_quality semantic gap.**

Update the spec to acknowledge that match_quality="full" means "O*NET row exists" not "O*NET scores available." Consider adding a fifth match_quality tier (e.g., "full_with_partial_onet") for the 24 partial profiles, or document that downstream consumers must check stat_hmn IS NOT NULL independently.

### LOWER PRIORITY

**L1. Adjust GLD-FE-040 threshold.** The current 95% threshold for branch_has_full_data is too tight for the actual 92.7% rate. Either lower to 90% or document 92.7% as the baseline.

**L2. Add financial reasonableness rules.** No rules check that earnings_1yr_median or median_annual_wage are in plausible ranges. Upstream DQ may cover this, but Gold-layer independence is preferable.

---

## Meta-Assessment: Can AI Agents Build Trustworthy Data Pipelines?

**The pipeline itself is well-built.** The transformer code is correct. The join chain works. The dedup logic handles the 47.8% duplicate rate properly. Null propagation is flawless. The stat formulas produce correct values. The DQ rules are comprehensive (45 rules, 93.3% chaos detection rate). The EDA is thorough and accurate.

**The verification layer is where hallucination occurred.** The golden dataset -- the artifact specifically designed to prove the pipeline produces correct outputs -- contains fabricated values that look plausible but are false. This is the most insidious form of AI hallucination: the AI generated test data that is internally consistent (the math checks out) but externally invalid (the input values do not exist in the actual data).

**Why did the human reviewer not catch this?** Because verifying a golden dataset requires querying the warehouse to confirm that the claimed source values are real. A human reviewing the golden dataset JSON sees: "ISU Business Admin, cip_family_earnings_rank=0.45, that sounds reasonable." Without independently querying the warehouse, the fabrication is invisible.

**The defense that works:** Independent warehouse queries by an adversarial agent with no access to the golden dataset's construction process. This audit found the fabrication in the first query.

**The defense that failed:** The golden dataset DQ rule (GLD-FE-044) was DEFERRED, meaning the fabricated golden dataset was never actually validated against the warehouse. Had this rule been active and correctly implemented, it would have caught the fabrication. The chain of failure: AI fabricated golden dataset -> DQ rule was DEFERRED -> no automated check caught it -> human reviewer saw internally-consistent math and approved.

**Bottom line:** AI agents can build trustworthy data pipelines, but the verification artifacts must be independently validated against real data, not accepted on the basis of internal consistency. The pipeline code in this spec earns high marks. The golden dataset earns a failing grade. Fix the golden dataset, activate the DQ rule, and this spec is ready for staff review.

---

**Audit completed:** 2026-04-09
**Auditor:** @adversarial-auditor
**Recommendation:** CHANGES REQUESTED -- fix blocking items B1 and B2 before staff review
