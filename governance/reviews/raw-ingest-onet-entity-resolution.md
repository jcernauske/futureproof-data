# Entity Resolution Assessment: raw-ingest-onet
**Date:** 2026-04-07
**Agent:** @entity-resolver
**Entity Type:** Occupation (O*NET-SOC Code)
**Resolution Strategy:** Authoritative identifier verification + cross-source SOC code bridging analysis

---

## Finding: No Entity Resolution Needed Within O*NET

O*NET-SOC codes are authoritative identifiers defined by O*NET (U.S. Department of Labor / Employment and Training Administration) as extensions of the OMB/BLS Standard Occupational Classification system. Every O*NET-SOC code is unique, stable within a release, and maps 1:1 to an occupation title and description.

**No entity resolution, fuzzy matching, or deduplication is required for this dataset.**

All 1,016 occupations use the standardized XX-XXXX.XX format with 100% format validation across all 5 present tables. Occupation titles are unique. Referential integrity across child tables is perfect (0 orphans).

---

## Verification Results

### Identifier Statistics (from full dataset per EDA)
| Metric | Value |
|--------|-------|
| Total occupations in master table | 1,016 |
| Distinct O*NET-SOC codes | 1,016 (100% unique) |
| Distinct occupation titles | 1,016 (100% unique) |
| Format validation pass rate | 100% (XX-XXXX.XX pattern) |
| Codes with .00 suffix (base BLS occupation) | 867 |
| Codes with non-.00 suffix (O*NET detail codes) | 149 |
| Distinct 6-digit BLS SOC codes derivable | 867 |
| BLS SOCs with multiple O*NET details | 76 |

### O*NET-SOC Code-to-Title Mapping: Clean
- Every O*NET-SOC code maps to exactly one occupation title. 1:1 confirmed.
- No variant spellings or ambiguous identifiers across any of the 5 tables.
- All child tables (Task Statements, Work Activities, Work Context, Related Occupations) reference codes that exist in the master Occupation Data table.

### Referential Integrity Across Tables: Clean
| Table | Distinct SOCs | All in Master? | Coverage of 1,016 |
|-------|--------------|----------------|-------------------|
| Occupation Data | 1,016 | Master table | 100% |
| Task Statements | 923 | Yes (100%) | 90.8% |
| Work Activities | 894 | Yes (100%) | 88.0% |
| Work Context | 894 | Yes (100%) | 88.0% |
| Related Occupations | 923 | Yes (100%) | 90.8% |

Zero orphan references in any direction. The coverage gap (93 and 122 occupations missing from child tables) is structural, not a data quality issue -- see "All Other / Military Gap" section below.

---

## Cross-Source SOC Code Bridging

This is the primary entity resolution concern for raw-ingest-onet. O*NET and BLS OOH both identify occupations by SOC codes, but use different formats.

### Format Comparison
| Source | Format | Example | Unique Codes |
|--------|--------|---------|-------------|
| O*NET 30.2 | XX-XXXX.XX (8-digit with 2-digit suffix) | 15-1252.00 | 1,016 |
| BLS OOH | XX-XXXX (6-digit, no suffix) | 15-1252 | ~832 |
| Derivable from O*NET (truncated) | XX-XXXX | 15-1252 | 867 |

### Bridging Classification

The 1,016 O*NET-SOC codes fall into three categories for BLS cross-referencing:

#### Category 1: Direct Match (.00 suffix) -- 867 codes
- Truncate to XX-XXXX for a 1:1 BLS join.
- Example: O*NET `15-1252.00` maps directly to BLS `15-1252`.
- Confidence: 1.0 (deterministic truncation, not fuzzy matching).

#### Category 2: Detail Split (non-.00 suffix) -- 149 codes across 76 BLS SOCs
- Multiple O*NET codes map to one BLS SOC code.
- Example: BLS `29-1229` ("Physicians, All Other") splits into O*NET `29-1229.01`, `29-1229.02`, `29-1229.03`, etc.
- These 149 codes still map to BLS by truncating to 6 digits, but the join is N:1 (multiple O*NET details to one BLS occupation).
- Silver zone must decide aggregation strategy (average, weighted average, max, etc.) when presenting at BLS granularity.
- Confidence: 1.0 for the mapping itself. Aggregation strategy is a modeling decision, not a resolution ambiguity.

#### Distribution of detail splits:
| O*NET Details per BLS SOC | Count of BLS SOCs |
|--------------------------|-------------------|
| 2 | 55 |
| 3 | 10 |
| 4 | 2 |
| 5 | 2 |
| 6+ | 7 |

#### Category 3: "All Other" / Military (.00 suffix, structurally empty) -- 93 codes
- These 93 O*NET codes (all .00 suffix) exist in Occupation Data but have zero rows in all child tables.
- They are residual SOC categories (e.g., "Managers, All Other") and Military occupations (55-xxxx).
- O*NET cannot survey these because they represent heterogeneous collections of occupations, not specific jobs.
- They will appear in BLS OOH but will have null O*NET data in cross-source joins. This is expected, not a data quality issue.
- Includes all 19 military occupations (55-xxxx.00).

### Bridging Rules for Silver Zone

1. **Derive `bls_soc_code`** by taking the first 7 characters of the O*NET-SOC code (XX-XXXX). This is deterministic, not probabilistic.
2. **Add `is_detail_code` flag:** True when suffix is not `.00`. Downstream consumers need to know when aggregation occurred.
3. **LEFT join from each source** to preserve unmatched codes on both sides. Some O*NET SOCs may not have BLS OOH data (and vice versa).
4. **For Gold zone aggregation:** When multiple O*NET detail codes roll up to one BLS SOC, use unweighted average of ratings as the default strategy. Employment-weighted averaging would be better but requires external data not currently in the pipeline.

### Important: This is NOT Entity Resolution

The O*NET-to-BLS mapping is a deterministic string operation (truncation), not a fuzzy match or probabilistic resolution. No confidence scoring, no ambiguity, no candidate ranking. The only entity-resolution-like consideration is the N:1 aggregation decision for the 76 split BLS SOCs, and that is a modeling decision for @semantic-modeler, not a resolution decision for @entity-resolver.

---

## Coverage Gap Analysis: 93 Structurally Empty Occupations

### What They Are
All 93 are base codes (.00 suffix) that fall into two groups:
1. **"All Other" residual categories** (74 codes) -- e.g., "Managers, All Other" (11-9199.00). These catch-all SOC codes represent occupations not individually classified within a minor group.
2. **Military occupations** (19 codes) -- all 55-xxxx.00 codes. O*NET does not survey military positions.

### Impact on Cross-Source Joins
- These occupations WILL appear in BLS OOH (BLS publishes projections for "All Other" categories).
- Cross-source joins between O*NET and BLS will have null O*NET data for these 93 occupations.
- Gold zone occupation profiles should mark them as "No detailed O*NET data available -- this is a residual or military occupation category."

### This is NOT a Resolution Problem
These 93 occupations are not ambiguous, unresolved, or mismatched. They are structurally empty by design. No resolution action is needed. The Silver zone should handle this via LEFT JOIN behavior and a `has_onet_data` flag.

---

## 29 Partial-Data Occupations

An additional 29 occupations (beyond the 93) have Task Statements and Related Occupations but no Work Activities or Work Context. Total with incomplete profiles: 122 of 1,016 (12.0%).

These are likely recently added or recently reclassified occupations where full survey data has not yet been collected. Examples include "Web and Digital Interface Designers" (15-1255.00) and "Crematory Operators" (39-4012.00).

**Resolution impact:** None. These occupations have valid O*NET-SOC codes with correct referential integrity. The data gap is a completeness issue, not an identity issue. Silver zone should flag these with a `data_completeness` indicator: "full" (894), "partial" (29), or "none" (93).

---

## SOC Taxonomy Lifecycle Considerations

### SOC Version History
| Version | Year | Notes |
|---------|------|-------|
| SOC 2010 | 2010 | Previous version; some historical O*NET data may reference this |
| SOC 2018 | 2018 | Current version; used by O*NET 30.2, BLS OOH, and College Scorecard crosswalks |
| SOC 2028 | ~2028 | Anticipated next revision; will require migration planning |

### SOC 2028 Migration Risk
When SOC 2028 is released, O*NET-SOC codes may change. This will require:
1. A SOC 2018-to-2028 crosswalk (BLS will publish one)
2. Entity lifecycle events (mergers, splits, reclassifications) logged in the entity registry
3. O*NET will release a new database version aligned with SOC 2028

**Current risk: LOW.** SOC 2018 is stable through ~2028. No action needed now. This is consistent with the assessment documented in the BLS OOH entity resolution report.

---

## Cross-Source Taxonomy Summary

This is the third and final primary data source for FutureProof. The complete cross-source taxonomy landscape is now:

```
College Scorecard (CIP 2020)
        |
        | CIP-to-SOC Crosswalk (many-to-many, variable confidence)
        v
BLS OOH (SOC 2018, XX-XXXX)
        |
        | Deterministic truncation (1:1 or N:1)
        |
O*NET 30.2 (SOC 2018, XX-XXXX.XX)
```

| Link | Method | Confidence | Complexity |
|------|--------|-----------|------------|
| O*NET to BLS OOH | Truncate O*NET code to 6 digits | 1.0 | Trivial (deterministic) |
| College Scorecard to BLS OOH | CIP-SOC crosswalk table | 0.6-1.0 (variable) | Moderate (many-to-many, requires reference table) |
| College Scorecard to O*NET | Via BLS OOH (chain of above two links) | Variable | Moderate (two-hop join) |

---

## Entity Registry

No entity registry entries are needed at the Raw zone for O*NET. The O*NET-SOC code is an authoritative identifier that requires no resolution. Consistent with the BLS OOH decision, entity registry creation is deferred to the Silver zone when cross-source joins are implemented.

When the Silver zone spec is executed, the entity registry should include:
1. Each canonical occupation keyed by 6-digit BLS SOC code
2. All associated O*NET detail codes for each BLS SOC
3. CIP-to-SOC crosswalk mappings with confidence scores
4. Coverage flags: `has_bls_data`, `has_onet_data`, `onet_data_completeness`

---

## Recommendations

1. **Preserve full O*NET-SOC codes (XX-XXXX.XX) in Bronze.** Do not truncate to 6 digits at ingest. Silver zone handles the mapping.
2. **Do not attempt name-based matching.** O*NET occupation titles are display labels, not identifiers. The SOC code is authoritative.
3. **Plan for N:1 aggregation in Silver zone** for the 76 BLS SOCs with multiple O*NET detail codes. Document the aggregation method used.
4. **Mark the 93 "All Other"/Military occupations** with a structural-gap flag, not a data-quality-failure flag.
5. **Track the 29 partial-data occupations** across O*NET releases. If this count grows significantly, it may indicate a systemic issue with O*NET survey coverage.
6. **Monitor for SOC 2028 announcement** and plan migration when the crosswalk is published.

---

## Resolution Status: PASS -- No Action Required
