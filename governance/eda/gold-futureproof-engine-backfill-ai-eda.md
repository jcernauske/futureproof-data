## EDA Report: gold-futureproof-engine-backfill-ai
**Source:** consumable.ai_exposure, consumable.program_career_paths, consumable.career_branches
**Date:** 2026-04-09
**Agent:** @data-analyst
**Spec:** raw-ingest-karpathy-ai-exposure (Zone 4: Backfill)

### Tables Analyzed

| Table | Row Count | Distinct SOC Codes |
|-------|----------:|-------------------:|
| consumable.ai_exposure | 389 | 389 |
| consumable.program_career_paths | 626,406 | 634 |
| consumable.career_branches | 15,944 | 798 (source), 796 (target) |

---

### Key Findings

- **SOC match rate is 57.4%, well below the expected 80-90%.** Only 340 of 634 distinct SOC codes in program_career_paths match ai_exposure. The shortfall is structural: Karpathy scored 342 BLS OOH occupations, but the crosswalk maps Scorecard programs to a broader set of SOC codes (634 distinct), many of which are detailed codes within groups Karpathy scored only at the broad level.
- **Education occupations (SOC group 25) are the largest gap.** Group 25 has 64 distinct SOC codes in PCP but only 14 match ai_exposure (22%). Karpathy has only the broad "Postsecondary teachers" (25-1199) but PCP contains 50+ detailed postsecondary teacher SOC codes (25-1011 through 25-1124). This single group accounts for 115,188 unmatched rows (43% of all unmatched rows).
- **stat_res and boss_ai_score are currently 100% null** as expected (placeholder fields from the original engine spec).
- **Post-backfill, stat_res will be null for 42.6% of rows** (266,551 of 626,406). This is significantly higher than the spec's expected 10-20% null rate.
- **The inverse invariant holds perfectly:** stat_res + boss_ai_score = 11 for all 389 ai_exposure rows. No exposure_score = 0 edge cases exist in the data.
- **stat_res distribution is left-skewed** (weighted by PCP rows): mean 4.4, median 4.0. Most career paths linked to Scorecard programs have moderate-to-low AI resilience (35.5% of matched rows have stat_res = 4).
- **career_branches coverage is even lower:** only 46.0% of rows get source stat_res, 45.4% get target stat_res, and only 25.7% get both (needed for delta computation).

---

### Q1: program_career_paths SOC Match to ai_exposure

| Metric | Value |
|--------|------:|
| Total PCP rows | 626,406 |
| Distinct SOC codes in PCP | 634 |
| Distinct SOC codes matched | 340 (53.6% of codes) |
| PCP rows with SOC match | 359,855 (57.4% of rows) |
| PCP rows without SOC match | 266,551 (42.6% of rows) |

**Match rate by SOC major group (top gaps):**

| SOC Group | Description | Codes | Matched | Code% | Rows | Matched Rows | Row% |
|-----------|-------------|------:|--------:|------:|-----:|-------------:|-----:|
| 25 | Education | 64 | 14 | 22% | 154,298 | 39,110 | 25% |
| 43 | Office/Admin | 32 | 7 | 22% | 16,102 | 3,082 | 19% |
| 49 | Install/Maint | 42 | 16 | 38% | 2,902 | 544 | 19% |
| 55 | Military | 10 | 0 | 0% | 824 | 0 | 0% |
| 37 | Building/Grounds | 4 | 0 | 0% | 397 | 0 | 0% |

**Match rate by current match_quality:**

| match_quality | Total Rows | AI Matched | Match Rate |
|---------------|----------:|-----------:|-----------:|
| full | 584,051 | 353,929 | 60.6% |
| partial_no_onet | 26,149 | 5,926 | 22.7% |
| partial_no_bls | 15,376 | 0 | 0.0% |
| scorecard_only | 830 | 0 | 0.0% |

Rows with `partial_no_bls` or `scorecard_only` will never match ai_exposure because their SOC codes do not exist in BLS OOH data, which is the same source Karpathy scored.

---

### Q2: career_branches SOC Match to ai_exposure

| Metric | Value |
|--------|------:|
| Total career_branches rows | 15,944 |
| Source SOC matched | 7,342 (46.0%) |
| Target SOC matched | 7,233 (45.4%) |
| Both matched (delta computable) | 4,097 (25.7%) |

The career_branches table references the full O*NET/BLS SOC universe (798 distinct source codes), which is much broader than Karpathy's 389. Only about a quarter of branch pairs will have a computable stat_res_delta.

---

### Q3: Current stat_res/boss_ai_score Null Rate

| Field | Null Count | Null Rate |
|-------|----------:|---------:|
| stat_res | 626,406 | 100.0% |
| boss_ai_score | 626,406 | 100.0% |

Confirmed: both fields are entirely null as expected from the placeholder implementation.

**Current stats_available_count distribution:**

| stats_available_count | Rows | Percentage |
|----------------------:|-----:|-----------:|
| 0 | 1,301 | 0.2% |
| 1 | 33,545 | 5.4% |
| 2 | 333,769 | 53.3% |
| 3 | 45,398 | 7.2% |
| 4 | 212,393 | 33.9% |

---

### Q4: Predicted Post-Backfill Null Rate

| Field | Current Null | Post-Backfill Null | Change |
|-------|------------:|--------------------|-------:|
| stat_res | 626,406 (100%) | 266,551 (42.6%) | -57.4% filled |
| boss_ai_score | 626,406 (100%) | 266,551 (42.6%) | -57.4% filled |

**Why 42.6% remain null:** The 294 unmatched SOC codes fall into three categories:
1. **Detailed education SOCs** (25-1011, 25-1021, etc.) -- Karpathy scored only broad "Postsecondary teachers" (25-1199). 50+ detailed teacher codes are unmatched. This is the single largest gap.
2. **Detailed codes within broad Karpathy groups** -- The Silver broad-expansion step expanded some broad codes to detailed, but many detailed codes in the crosswalk have no corresponding Karpathy entry.
3. **SOC codes outside Karpathy's 342 BLS OOH occupations** -- military (55-xxxx), some niche maintenance/cleaning codes.

---

### Q5: Distribution of stat_res and boss_ai_score Values

**stat_res distribution across ai_exposure (389 occupations):**

| stat_res | Occupations | Meaning |
|---------:|------------:|---------|
| 1 | 1 | Minimal resilience |
| 2 | 33 | Very low resilience |
| 3 | 29 | Low resilience |
| 4 | 71 | Below average |
| 5 | 45 | Moderate |
| 6 | 52 | Above average |
| 7 | 45 | Good resilience |
| 8 | 61 | High resilience |
| 9 | 41 | Very high resilience |
| 10 | 11 | Maximum resilience |

**Weighted stat_res distribution (across 359,855 matched PCP rows):**

| stat_res | PCP Rows | Percentage |
|---------:|---------:|-----------:|
| 1 | 633 | 0.2% |
| 2 | 55,342 | 15.4% |
| 3 | 41,895 | 11.6% |
| 4 | 127,667 | 35.5% |
| 5 | 45,620 | 12.7% |
| 6 | 38,343 | 10.7% |
| 7 | 32,208 | 9.0% |
| 8 | 13,038 | 3.6% |
| 9 | 4,020 | 1.1% |
| 10 | 1,089 | 0.3% |

**Summary stats (PCP-weighted):** Min=1, Max=10, Mean=4.4, Median=4.0, StdDev=1.71

The distribution is left-skewed -- most program-career paths map to occupations with moderate-to-high AI exposure (low resilience). The dominant value (stat_res=4, exposure=7) accounts for 35.5% of matched rows, driven by the 71 occupations at exposure=7 being highly represented in the crosswalk.

**boss_ai_score** is the mirror image (boss_ai = 11 - stat_res), so 35.5% of matched rows will have boss_ai=7.

---

### Q6: stats_available_count Change (4 to 5 for matched rows)

**Predicted post-backfill stats_available_count:**

| stats_available_count | Current | Post-Backfill | Change |
|----------------------:|--------:|--------------:|-------:|
| 0 | 1,301 (0.2%) | 1,301 (0.2%) | unchanged |
| 1 | 33,545 (5.4%) | 25,764 (4.1%) | -7,781 |
| 2 | 333,769 (53.3%) | 146,953 (23.5%) | -186,816 |
| 3 | 45,398 (7.2%) | 216,632 (34.6%) | +171,234 |
| 4 | 212,393 (33.9%) | 101,642 (16.2%) | -110,751 |
| 5 | 0 (0.0%) | 134,114 (21.4%) | +134,114 |

Key observations:
- **134,114 rows (21.4%) will achieve the full 5/5 stat pentagon** -- these are rows that currently have stats_available=4 and match ai_exposure.
- **The modal value shifts from 2 to 3** -- the largest group moves from "2 stats" to "3 stats" as the AI stat fills in.
- **Rows with stats_available=0 are unchanged** -- these 1,301 rows have no stats at all (scorecard_only match quality with null earnings data).

**Predicted post-backfill bosses_available_count:**

| bosses_available_count | Rows | Percentage |
|-----------------------:|-----:|-----------:|
| 0 | 1,301 | 0.2% |
| 1 | 11,298 | 1.8% |
| 2 | 22,209 | 3.5% |
| 3 | 165,288 | 26.4% |
| 4 | 292,196 | 46.6% |
| 5 | 134,114 | 21.4% |

---

### ai_exposure Data Quality

| Check | Result |
|-------|--------|
| Row count | 389 (expected ~342 + broad code expansions) |
| Inverse invariant (stat_res + boss_ai = 11) | 389/389 PASS |
| exposure_score = 0 edge case | 0 rows (no edge case in data) |
| stat_res range 1-10 | PASS |
| boss_ai_score range 1-10 | PASS |
| soc_code uniqueness | 389 distinct = 389 rows PASS |
| Null soc_code | 0 (all filtered at Gold) |

**Category distribution (top 5):**

| Category | Count |
|----------|------:|
| healthcare | 56 |
| life-physical-and-social-science | 38 |
| architecture-and-engineering | 33 |
| management | 27 |
| construction-and-extraction | 24 |

---

### Recommendations for @dq-rule-writer

1. **Adjust expected AI match rate from 80-90% to 55-60%.** The spec overestimated because it assumed Karpathy's 342 occupations would cover most crosswalk SOC codes. In reality, the crosswalk maps to 634 distinct SOC codes, many of which are detailed codes Karpathy did not score individually.

2. **stat_res null rate post-backfill should be 40-45%**, not 10-20%. DQ rules should accept this range.

3. **stats_available_count=5 should be 20-22% of rows** (the rows achieving full pentagon).

4. **stats_available_count=4 should DROP from 33.9% to ~16%** (the rows that had 4 stats but don't match ai_exposure keep 4; the ones that do match move to 5).

5. **career_branches stat_res_delta will be null for ~74% of rows** (only 25.7% have both source and target matched). The DQ rule for delta completeness should accept this.

6. **Consider a follow-up broad-code propagation** in the backfill logic: if PCP has SOC 25-1011 (Business Teachers, Postsecondary) and ai_exposure has 25-1199 (Postsecondary Teachers, broad), propagating the broad score to the detailed codes would increase coverage from 57% to potentially 70%+. This is a design decision, not a DQ finding.

### Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|-------|----------|---------|
| SOC match rate | Coverage gap | 294 unmatched codes | Medium | 53.6% code match vs 80-90% expected. Education SOC group 25 is the primary gap (50 unmatched detailed teacher codes). |
| stat_res distribution skew | Distribution | 127,667 rows at stat_res=4 | Info | 35.5% of matched rows concentrate at one value. Driven by 71 occupations at exposure=7 being heavily crosswalk-linked. |
| career_branches delta coverage | Coverage gap | 11,847 rows no delta | Medium | Only 25.7% of branches can compute stat_res_delta. Most branch pairs involve at least one SOC outside Karpathy's set. |

---

### Edge Cases for DQ Thresholds

| Observation | Count | Percentage | Recommendation |
|-------------|-------|------------|----------------|
| PCP rows with no AI match | 266,551 | 42.6% | Accept 40-45% null rate for stat_res. Warn if > 50%. |
| PCP rows achieving 5/5 pentagon | 134,114 | 21.4% | Accept 20-25% full pentagon rate. |
| career_branches with both SOCs matched | 4,097 | 25.7% | Accept 25-30% delta coverage. |
| career_branches with neither SOC matched | 4,768 | 29.9% | Accept. These are O*NET-only occupations outside Karpathy scope. |
| ai_exposure duplicate occupation_title | ~5 rows | ~1.3% | Normal: broad expansion produces multiple SOC codes per occupation title. |
| stat_res = 1 (minimum resilience) | 1 occ / 633 PCP rows | 0.2% | Rare extreme. Only 1 occupation scores exposure=10. |
