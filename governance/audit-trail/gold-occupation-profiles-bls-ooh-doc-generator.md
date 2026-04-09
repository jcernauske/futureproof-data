# Audit Trail: @doc-generator for gold-occupation-profiles-bls-ooh

**Spec:** gold-occupation-profiles-bls-ooh
**Agent:** @doc-generator
**Date:** 2026-04-07
**Zone:** Gold (Consumable)
**Table:** consumable.occupation_profiles

---

## Actions Taken

### 1. Data Dictionary Update

**File:** `governance/data-dictionary.json`

Added a new table entry `consumable.occupation_profiles` with all 31 columns documented. This is the second Gold (consumable) table in the data dictionary, following `consumable.career_outcomes`.

**Columns added (31 total):**

| Column | Type | Is CDE | Source |
|--------|------|--------|--------|
| record_id | VARCHAR | false | Derived (compute_grain_id, prefix 'op') |
| soc_code | VARCHAR | true | base.bls_ooh.soc_code (verbatim) |
| occupation_title | VARCHAR | true | base.bls_ooh.occupation_title (verbatim) |
| soc_major_group | VARCHAR | false | base.bls_ooh.soc_major_group (verbatim) |
| soc_major_group_name | VARCHAR | false | base.bls_ooh.soc_major_group_name (verbatim) |
| broad_occupation_flag | BOOLEAN | false | base.bls_ooh.broad_occupation_flag (verbatim) |
| catchall_flag | BOOLEAN | false | base.bls_ooh.catchall_flag (verbatim) |
| employment_current | BIGINT | true | base.bls_ooh.employment_current (verbatim) |
| employment_projected | BIGINT | false | base.bls_ooh.employment_projected (verbatim) |
| employment_change_pct | DOUBLE | true | base.bls_ooh.employment_change_pct (verbatim) |
| openings_annual_avg | BIGINT | false | base.bls_ooh.openings_annual_avg (verbatim) |
| growth_category | VARCHAR | false | base.bls_ooh.growth_category (verbatim) |
| grw_score | DOUBLE | true | Derived (piecewise linear from employment_change_pct) |
| grw_score_rounded | INTEGER | false | Derived (ROUND of grw_score) |
| median_annual_wage | DOUBLE | true | base.bls_ooh.median_annual_wage (verbatim) |
| wage_available | BOOLEAN | false | base.bls_ooh.wage_available (verbatim) |
| wage_percentile_overall | DOUBLE | true | Derived (PERCENT_RANK on median_annual_wage) |
| wage_percentile_education_tier | DOUBLE | true | Derived (PERCENT_RANK partitioned by education_code) |
| wage_tier | VARCHAR | false | Derived (bucketed from wage_percentile_overall) |
| education_code | INTEGER | false | base.bls_ooh.education_code (verbatim) |
| education_level_name | VARCHAR | false | base.bls_ooh.education_level_name (verbatim) |
| work_experience_code | INTEGER | false | base.bls_ooh.work_experience_code (verbatim) |
| training_code | INTEGER | false | base.bls_ooh.training_code (verbatim) |
| market_score | DOUBLE | true | Derived (0.6 * grw_score + 0.4 * openings_score) |
| market_score_rounded | INTEGER | false | Derived (ROUND of market_score) |
| confidence_tier | VARCHAR | false | Derived (from wage_available + flags) |
| data_completeness | DOUBLE | false | Derived (non-null core fields / 4) |
| backs_stats | VARCHAR | false | Static constant ('ERN,GRW') |
| backs_bosses | VARCHAR | false | Static constant ('Market,Ceiling') |
| source_load_date | DATE | false | base.bls_ooh.source_load_date (verbatim) |
| promoted_at | TIMESTAMP | false | Generated at promotion time |

**CDE columns (9 total):** soc_code, occupation_title, employment_current, employment_change_pct, grw_score, median_annual_wage, wage_percentile_overall, wage_percentile_education_tier, market_score

### 2. Data Contract Validation

**File:** `governance/data-contracts/consumable-occupation-profiles.yaml`

Validated the existing data contract produced by @cde-tagger. Findings:

- All 31 columns present and documented
- Column names match exactly between data contract and data dictionary
- CDE flags consistent between contract and dictionary (9 CDE columns in both)
- Quality section complete with thresholds for completeness, validity, uniqueness, volume, and consistency
- Breaking change policy defined (semantic versioning with 30-day deprecation notice)
- Consumer section documents 5 downstream consumers (pentagon stats, boss fights, Gemma, crosswalk, O*NET)
- Lineage reference points to correct transformer source

**One update made:** Set `dq_rules.total_rules` from `*pending*` to `54` (the actual count from `governance/dq-rules/gold-occupation-profiles-bls-ooh.json`).

### 3. Cross-Reference Verification

Verified consistency across governance artifacts:

| Artifact | Column Count | Match |
|----------|-------------|-------|
| Physical model | 31 | Yes |
| Logical model | 31 | Yes |
| Data contract | 31 | Yes |
| Data dictionary | 31 | Yes |
| Lineage (output schema) | 31 | Yes |

- Business term references (BT-015 through BT-054) verified against `governance/business-glossary.json`
- DQ rule IDs (GLD-OP-001 through GLD-OP-054) verified against `governance/dq-rules/gold-occupation-profiles-bls-ooh.json`
- Lineage file path verified: `governance/lineage/gold-occupation-profiles-bls-ooh-20260407T230000Z.json`
- DQ scorecard confirms 52/53 rules passing (98%)

---

## Judgment Calls and Interpretation Decisions

1. **occupation_title CDE designation:** The data contract and CDE tagger designated occupation_title as a CDE. The data dictionary entry follows this designation with the rationale that it is the primary display label consumed by all user-facing components. This is a judgment call — in the Silver zone, occupation_title was not flagged as CDE. The Gold zone designation reflects its elevated importance as a consumable field.

2. **DQ rule cross-references:** Not every column has a directly mapped DQ rule. For example, work_experience_code and training_code have no Gold-specific DQ rules because they are simple pass-through fields validated in Silver. The dictionary entries reflect this (empty dq_rules arrays) rather than inventing rule references.

3. **employment_projected CDE status:** The CDE tagger flagged employment_projected as CDE in the physical model but not in the data contract. The data dictionary follows the data contract (not CDE) because employment_projected is not independently consumed in the Gold layer — the derived grw_score carries the analytical signal. This is consistent with the contract's reasoning.

4. **openings_annual_avg CDE status:** Similarly, openings_annual_avg is flagged as CDE in the physical model but not the contract. The dictionary follows the contract because openings_annual_avg contributes to market_score (which IS a CDE) but is not independently consumed as a critical business metric.

---

## Files Modified

| File | Action |
|------|--------|
| `governance/data-dictionary.json` | Added `consumable.occupation_profiles` table entry (31 columns) |
| `governance/data-contracts/consumable-occupation-profiles.yaml` | Updated `dq_rules.total_rules` from `*pending*` to `54` |
| `governance/audit-trail/gold-occupation-profiles-bls-ooh-doc-generator.md` | Created (this file) |
