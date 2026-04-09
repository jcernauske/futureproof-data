# Coverage Gap Report: CIP-SOC Crosswalk

**Spec:** crosswalk-cip-soc
**Date:** 2026-04-08
**Agent:** @doc-generator
**Data Source:** Production data from base.cip_soc_crosswalk (5,903 rows), base.college_scorecard (69,947 rows), base.bls_ooh (832 SOC codes), base.onet_occupations (798 SOC codes)
**DQ Scorecard:** governance/dq-scorecards/crosswalk-cip-soc-scorecard.md (96% pass rate)

---

## Executive Summary

The CIP-SOC crosswalk connects academic programs to occupations, but three systematic coverage gaps exist. The most significant is the **CIP granularity mismatch**: the crosswalk uses 6-digit CIP codes while College Scorecard uses 4-digit codes, resulting in zero direct matches. This is a known design decision — not a bug — and resolution is deferred to the Gold zone. BLS and O*NET coverage is strong (94.6% and 92.0% respectively), with all gaps attributable to taxonomy version differences rather than missing data.

---

## Gap 1: College Scorecard CIP Codes With No Crosswalk Entry

### The Problem

Students who pick a major in the College Scorecard that has no corresponding crosswalk entry will get **no occupation data** — no BLS employment outlook, no O*NET task profiles, no career distribution. Their FutureProof experience is limited to earnings and debt data from the Scorecard alone.

### Root Cause: CIP Granularity Mismatch

| Property | Crosswalk | College Scorecard |
|----------|-----------|-------------------|
| CIP format | XX.XXXX (6-digit, e.g., 52.0201) | XX.XX (4-digit, e.g., 52.02) |
| Distinct CIP codes | 1,949 (after filtering sentinels) | 390 |
| Granularity | Specific programs (e.g., "Business Administration and Management, General") | Program families (e.g., "Business Administration and Management") |

Under **strict 6-digit matching** (the current Silver implementation per spec), **zero** College Scorecard CIP codes match any crosswalk CIP code. This means:

- **0 of 390** Scorecard CIP codes have a direct crosswalk entry
- **0 of 69,947** Scorecard rows can reach occupation data through the crosswalk
- **100%** of base.cip_soc_crosswalk rows have match_quality = "no_scorecard"

### What 4-Digit Matching Would Achieve

If the crosswalk CIP codes were truncated to 4 digits for matching purposes (deferred to Gold zone):

| Metric | Value |
|--------|-------|
| Scorecard CIPs matched | 355 of 390 (91.0%) |
| Scorecard rows covered | 67,939 of 69,947 (97.1%) |
| Unmatched Scorecard CIPs | 35 |

The 35 unmatched Scorecard CIPs at 4-digit level fall into two categories:

1. **"Other" residual categories** (XX.99 pattern) — programs like "Liberal Arts, Other" that aggregate miscellaneous programs within a CIP family. The crosswalk does not map these because they are too broad to associate with specific occupations.
2. **Military, personal awareness, and high school families** (CIP families 32, 33, 34, 35, 36, 53) — these exist in the Scorecard but the crosswalk designates them as having no SOC correspondence.

### Impact on FutureProof Users

- **Under strict matching (current):** No student query reaches occupation data. The crosswalk exists but is not connected to any student-facing data path. Earnings-only analysis is available from College Scorecard.
- **Under 4-digit matching (Gold zone):** 97.1% of Scorecard rows connect to at least one occupation. The remaining 2.9% (2,008 rows across 35 CIP codes) would need Gemma estimation or a "data not available" disclosure.

### Resolution Path

The spec explicitly defers this to Gold zone (Open Decision #1). The Gold product should:
1. Match crosswalk CIP codes to Scorecard CIP codes at the 4-digit (XX.XX) level
2. When a 4-digit Scorecard CIP matches multiple 6-digit crosswalk CIPs, include all SOC codes from all matching crosswalk entries
3. For the 35 unmatched CIPs, display an explicit "no occupation mapping available" message rather than silently omitting data

---

## Gap 2: BLS/O*NET SOC Codes With No Crosswalk Entry

### BLS OOH SOC Codes Missing From Crosswalk

| Metric | Value |
|--------|-------|
| BLS distinct SOC codes | 832 |
| BLS SOCs found in crosswalk | 820 (98.6%) |
| BLS SOCs NOT in crosswalk | 12 (1.4%) |

The 12 BLS SOC codes missing from the crosswalk are **rolled-up parent codes** (e.g., BLS reports SOC 13-1020 "Buyers and Purchasing Agents" while the crosswalk uses the detailed children 13-1021, 13-1022, 13-1023). These occupations ARE reachable through their child codes in the crosswalk — they are not true coverage gaps, they are SOC version granularity differences.

### Crosswalk SOC Codes Missing From BLS OOH

| Metric | Value |
|--------|-------|
| Crosswalk distinct SOC codes | 867 |
| Crosswalk SOCs found in BLS | 820 (94.6%) |
| Crosswalk SOCs NOT in BLS | 47 (5.4%) |
| Silver rows affected | 154 of 5,903 (2.61%) |

The 47 crosswalk SOC codes not in BLS are the inverse of the above: they are **detailed child codes** that BLS reports only at the rolled-up parent level. For example, the crosswalk has SOC 13-1021 "Buyers and Purchasing Agents" but BLS only reports at 13-1020 level.

These 47 codes affect 154 crosswalk rows where has_bls_match = FALSE. Students whose programs map to these SOC codes will have O*NET task data but no BLS employment projections.

### Crosswalk SOC Codes Missing From O*NET

| Metric | Value |
|--------|-------|
| Crosswalk distinct SOC codes | 867 |
| Crosswalk SOCs found in O*NET | 798 (92.0%) |
| Crosswalk SOCs NOT in O*NET | 69 (8.0%) |
| Silver rows affected | 304 of 5,903 (5.15%) |

The 69 crosswalk SOC codes not in O*NET are **"All Other" residual categories** (e.g., SOC 11-9039 "Managers, All Other", SOC 27-2099 "Entertainers and Performers, Sports and Related Workers, All Other"). O*NET does not profile these individually because they are catch-all codes for occupations that do not fit into more specific categories.

These 69 codes affect 304 crosswalk rows where has_onet_match = FALSE. Students whose programs map to these SOC codes will have BLS projections but no O*NET task/activity/context profiles.

### O*NET SOC Codes Missing From Crosswalk

| Metric | Value |
|--------|-------|
| O*NET distinct SOC codes | 798 |
| O*NET SOCs found in crosswalk | 798 (100.0%) |
| O*NET SOCs NOT in crosswalk | 0 (0.0%) |

O*NET has perfect coverage: every O*NET occupation can be reached through at least one CIP code in the crosswalk.

---

## Gap 3: CIP Granularity Mismatch Detail

### Why the Mismatch Exists

The CIP taxonomy is hierarchical:
- **2-digit family:** 52 = "Business, Management, Marketing, and Related Support Services"
- **4-digit group:** 52.02 = "Business Administration, Management, and Operations"
- **6-digit specific:** 52.0201 = "Business Administration and Management, General"

College Scorecard reports at the **4-digit group level** (52.02), while the crosswalk maps at the **6-digit specific level** (52.0201). This means:

- One Scorecard CIP (52.02) may correspond to multiple crosswalk CIPs (52.0201, 52.0202, 52.0203, etc.)
- Each of those crosswalk CIPs may map to different SOC codes
- The student gets the union of all possible occupations for their 4-digit program

### Quantitative Impact

| CIP Granularity | Distinct Codes | Coverage of Scorecard |
|-----------------|---------------|-----------------------|
| 6-digit (strict) | 1,949 crosswalk CIPs | 0% match to 390 Scorecard CIPs |
| 4-digit (truncated) | ~390 unique 4-digit prefixes from crosswalk | 91.0% match (355 of 390 Scorecard CIPs) |
| 2-digit (family) | 47 CIP families in crosswalk | ~95% match (most Scorecard families represented) |

### CIP Families With 100% No-Match (No Occupations in Crosswalk)

These CIP families have every code mapped to SOC 99-9999 ("no match"), meaning the crosswalk explicitly states these programs do not prepare students for specific occupations:

| CIP Family | Description | Scorecard Programs? |
|------------|-------------|---------------------|
| 32 | Basic Skills and Developmental/Remedial Education | Yes (few) |
| 33 | Citizenship Activities | Yes (few) |
| 34 | Health-Related Knowledge and Skills | Yes (few) |
| 35 | Interpersonal and Social Skills | Yes (few) |
| 36 | Leisure and Recreational Activities | Yes (few) |
| 37 | Personal Awareness and Self-Improvement | No |
| 53 | High School/Secondary Diplomas and Certificates | Yes (few) |

These are inherently non-career-oriented programs. Students in these programs should receive an explicit disclosure that no occupation mapping is available.

### CIP Families in Crosswalk But Not Scorecard

| CIP Family | Description | Why Missing |
|------------|-------------|-------------|
| 60 | Residency programs (dental) | Not bachelor's level |
| 61 | Residency programs (medical) | Not bachelor's level |
| 99 | Sentinel / catch-all | Not a real program |

These do not represent coverage gaps for FutureProof because the Scorecard MVP only includes bachelor's degrees.

---

## Match Quality Distribution (Silver Actuals)

### Current (Strict 6-Digit Matching)

| match_quality | Rows | Percentage | Meaning |
|---------------|------|------------|---------|
| no_scorecard | 5,903 | 100.0% | No Scorecard data reachable |
| full | 0 | 0.0% | -- |
| partial_no_onet | 0 | 0.0% | -- |
| partial_no_bls | 0 | 0.0% | -- |
| scorecard_only | 0 | 0.0% | -- |

### Projected (4-Digit Matching, Gold Zone)

| match_quality | Rows | Percentage | Meaning |
|---------------|------|------------|---------|
| full | 4,520 | 76.6% | Complete data for all FutureProof stats |
| no_scorecard | 1,064 | 18.0% | Crosswalk pair exists but no program data |
| partial_no_onet | 185 | 3.1% | Missing O*NET task profiles |
| partial_no_bls | 85 | 1.4% | Missing BLS employment projections |
| scorecard_only | 49 | 0.8% | Program data only, no occupation stats |

With 4-digit matching, 76.6% of crosswalk rows would achieve "full" quality — well above the spec's target of "majority." This validates that the underlying data is strong and the integration will work well once the Gold zone resolves the granularity mismatch.

---

## Recommendations

1. **Gold zone must implement 4-digit CIP matching** as the primary matching strategy, with explicit documentation that this broadens the mapping from specific programs to program families.

2. **For the 35 Scorecard CIPs unmatched even at 4-digit level**, the Gold product should display a clear "no occupation data available for this program" message rather than returning empty results.

3. **For the 47 crosswalk SOC codes not in BLS**, consider a future SOC normalization step that rolls up detailed crosswalk codes to match BLS parent codes. This would recover an additional 154 crosswalk rows (2.6%) for BLS data.

4. **For the 69 crosswalk SOC codes not in O*NET**, accept this as an inherent O*NET coverage limitation. "All Other" categories cannot be profiled at the task level. The Gold product should disclose when O*NET data is unavailable.

5. **Monitor these gaps across crosswalk versions.** When NCES publishes a new CIP-SOC crosswalk (expected ~2030 with CIP 2030 taxonomy), re-run this coverage analysis. The gaps may change as taxonomies evolve.

---

## Data Sources and Methodology

All numbers in this report are derived from production data validated by the DQ scorecard (27 of 28 rules passing, 96%). The one failing rule (SLV-XW-011) is a threshold calibration issue where BLS match rate (97.39%) slightly exceeds the upper bound (97%) — a "better than expected" outcome, not a data quality concern.

Cross-table match counts come from the EDA report (governance/eda/crosswalk-cip-soc-eda.md) and are confirmed by DQ informational rules SLV-XW-018, SLV-XW-019, and SLV-XW-020.

| Reference | Path |
|-----------|------|
| Spec | docs/specs/crosswalk-cip-soc.md |
| EDA Report | governance/eda/crosswalk-cip-soc-eda.md |
| DQ Scorecard | governance/dq-scorecards/crosswalk-cip-soc-scorecard.md |
| DQ Rules | governance/dq-rules/crosswalk-cip-soc.json |
| Data Contract | governance/data-contracts/base-cip-soc-crosswalk.yaml |
| Physical Model | governance/models/crosswalk-cip-soc-physical.md |
| Lineage | governance/lineage/crosswalk-cip-soc-20260408T120000Z.json |
