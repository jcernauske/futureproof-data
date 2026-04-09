## Audit Trail: EDA for crosswalk-cip-soc

**Date:** 2026-04-08
**Agent:** @data-analyst
**Spec:** docs/specs/crosswalk-cip-soc.md
**Pipeline Step:** 7 (EDA on Bronze data + Silver match analysis)

### What Was Analyzed

- CIP2020_SOC2018_Crosswalk.xlsx downloaded from NCES (428,901 bytes)
- Primary sheet: CIP-SOC (6,097 rows, 4 columns)
- Cross-table match analysis against: base.college_scorecard, base.bls_ooh, base.onet_occupations

### Key Findings

1. **6,097 rows, zero duplicates, zero nulls, 100% format compliance** -- clean authoritative government data
2. **194 no-match rows (3.18%)** with SOC 99-9999 to be filtered in Silver
3. **CRITICAL: CIP granularity mismatch** -- crosswalk uses 6-digit (XX.XXXX), Scorecard uses 4-digit (XX.XX). Zero direct joins. 91% match at 4-digit level.
4. **94.6% BLS SOC match rate** -- 47 mismatches are version granularity differences, not coverage gaps
5. **92.0% O*NET SOC match rate** -- 69 missing codes are "All Other" residual categories
6. **Row count (6,097) exceeds spec estimate (3,000-5,000)** -- DQ thresholds need adjustment

### Domain Discovery

- Crosswalk is a many-to-many relationship: median 3 SOCs per CIP, median 2 CIPs per SOC
- Highly skewed: postsecondary teacher SOCs absorb hundreds of CIPs (max 337)
- 7 CIP families (military, personal awareness, high school) have 100% no-match rates
- SOC group 25 (Education) dominates with 30% of valid rows

### Threshold Recommendations

- Row count: 5,500-6,500 (not 3,000-5,000)
- has_scorecard_match: 0% TRUE with strict 6-digit matching (not 60-90%)
- has_bls_match: 94-96% TRUE
- has_onet_match: 90-94% TRUE
- No-match filter: exactly 194 rows excluded
- Grain uniqueness: zero duplicates enforced
- Format validation: 100% on both CIP and SOC patterns

### Artifacts Produced

- `governance/eda/crosswalk-cip-soc-eda.md` -- full EDA report
- `governance/audit-trail/crosswalk-cip-soc-eda-2026-04-08.md` -- this file
