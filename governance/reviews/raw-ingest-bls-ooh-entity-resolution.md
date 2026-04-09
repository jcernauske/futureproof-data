# Entity Resolution Assessment: raw-ingest-bls-ooh
**Date:** 2026-04-07
**Agent:** @entity-resolver
**Entity Type:** Occupation (SOC Code)
**Resolution Strategy:** Not required -- authoritative federal identifier present

---

## Finding: No Entity Resolution Needed

SOC (Standard Occupational Classification) codes are authoritative identifiers defined by the Office of Management and Budget and maintained by the Bureau of Labor Statistics. SOC 2018 is the current taxonomy containing 867 detailed occupations organized into 23 major groups. Each detailed occupation has a unique XX-XXXX code that is stable within a taxonomy version.

**No entity resolution, fuzzy matching, or deduplication is required for this dataset.**

---

## Verification Results

### Identifier Statistics (from 10-row sample; re-validate on full ~832-row dataset)
| Metric | Value |
|--------|-------|
| Total rows (after summary filtering) | 10 |
| Distinct SOC codes | 10 |
| Distinct occupation titles | 10 |
| Summary rows filtered | 1 (SOC 11-0000) |

### SOC Code-to-Title Mapping: Clean
- **Same SOC code with different titles:** 0 cases
- Every SOC code maps to exactly one occupation_title. 1:1 relationship confirmed.

### Title-to-SOC Code Mapping: Clean
- **Same title with different SOC codes:** 0 cases
- No ambiguity in this sample. In the full dataset, occupation titles are expected to remain unique because BLS defines exactly one title per detailed SOC code.

### Format Validation
- All 10 SOC codes match the `^\d{2}-\d{4}$` pattern (XX-XXXX format).
- No trailing decimals, missing hyphens, or other format anomalies.
- The hyphen is part of the canonical format and must be preserved (unlike CIP codes which required dot insertion).

### Summary SOC Codes (Filtered)
- SOC codes ending in "0000" (e.g., 11-0000 "Management occupations") are major group aggregates, not detailed occupations.
- The ingestor correctly filters these. They should never appear in the processed dataset.
- This is not an entity resolution issue -- it is a grain-level filtering decision handled by the ingestor.

---

## SOC Taxonomy Lifecycle Considerations

### SOC Version History
| Version | Year | Notes |
|---------|------|-------|
| SOC 2010 | 2010 | Previous version; O*NET historical data may reference this |
| SOC 2018 | 2018 | Current version; used by this dataset and current O*NET releases |
| SOC 2028 | ~2028 | Anticipated next revision; will require migration planning |

### SOC 2028 Migration Risk
When SOC 2028 is released (expected ~2028), occupations may be added, removed, merged, split, or reclassified. This will require:
1. A SOC 2018 to SOC 2028 crosswalk (BLS will publish one)
2. Entity lifecycle events logged for affected occupations
3. Updates to the entity registry with new/changed canonical IDs

**Current risk: LOW.** The SOC 2018 taxonomy is stable through 2028. No action needed now, but this should be flagged as a future maintenance item.

---

## Cross-Source Linking Strategy for Silver Zone

This is the primary value of this entity resolution assessment. While SOC codes are unambiguous within BLS data, the FutureProof pipeline must link across three taxonomies:

### Taxonomy Landscape
| Source | Taxonomy | Key Field | Format | Relationship |
|--------|----------|-----------|--------|-------------|
| College Scorecard | CIP 2020 | cipcode | XX.XXXX (4-digit in raw) | Programs (what you study) |
| BLS OOH | SOC 2018 | soc_code | XX-XXXX | Occupations (what job you get) |
| O*NET (future) | SOC 2018 | soc_code | XX-XXXX | Occupations (task-level detail) |

### Link 1: BLS OOH to O*NET (Direct Join)
- **Method:** Exact SOC code match
- **Confidence:** 1.0
- **Complexity:** Trivial -- same taxonomy, same version (SOC 2018)
- **Join key:** `bls_ooh.soc_code = onet.soc_code`
- **Risk:** O*NET may include SOC detail codes (XX-XXXX.XX) that extend beyond the 6-character BLS codes. Silver zone should join on the first 7 characters (XX-XXXX) to handle this.

### Link 2: College Scorecard to BLS OOH (CIP-to-SOC Crosswalk)
- **Method:** Many-to-many crosswalk via NCES/BLS CIP-SOC Crosswalk table
- **Confidence:** Variable (0.6-1.0 depending on mapping specificity)
- **Complexity:** Moderate -- requires crosswalk reference table ingestion
- **Join path:** `college_scorecard.cipcode -> crosswalk.cip_code -> crosswalk.soc_code -> bls_ooh.soc_code`

#### CIP-to-SOC Crosswalk Requirements
1. **Crosswalk source:** NCES CIP-SOC Crosswalk (https://nces.ed.gov/ipeds/cipcode/)
2. **Relationship:** Many-to-many. One CIP code can map to multiple SOC codes (e.g., Business Administration graduates become managers, analysts, consultants). One SOC code can be reached from multiple CIP codes.
3. **CIP format normalization:** College Scorecard raw CIP codes are 4-digit ("5202"). Must be normalized to XX.XXXX format ("52.02") before crosswalk matching. This normalization is already documented as a Silver zone requirement.
4. **Confidence tiers for crosswalk matches:**
   - **1.0** -- Direct CIP-to-SOC mapping exists in crosswalk at detailed level
   - **0.7** -- CIP family (2-digit prefix) maps to SOC major group
   - **0.6** -- Heuristic mapping based on program/occupation name similarity
5. **Unmatched programs:** Some CIP codes (e.g., Liberal Arts, General Studies) have no clean SOC mapping. These must be retained with null SOC linkage, not dropped.
6. **Unmatched occupations:** Some SOC codes may have no CIP mapping (e.g., occupations that do not require formal education). These are valid occupations that simply do not link back to college programs.

### Link Summary Diagram
```
College Scorecard (CIP)
        |
        | CIP-to-SOC Crosswalk (many-to-many)
        v
BLS OOH (SOC) <---> O*NET (SOC)  [direct join]
```

---

## Entity Registry Entry

No entity registry update is needed at the Raw zone. The SOC code is an authoritative identifier that requires no resolution. When the Silver zone spec is implemented, the entity registry should be created with entries for:
1. Each canonical occupation (keyed by SOC code)
2. CIP-to-SOC crosswalk mappings with confidence scores
3. Any SOC codes that appear in one source but not another

---

## Recommendations

1. **Use soc_code as the primary foreign key** for all occupation-level joins and lookups. It is stable, unique, and authoritative within SOC 2018.
2. **Do not attempt name-based matching** for occupation identity. occupation_title is a display label, not an identifier. BLS may adjust title wording between releases while keeping the same SOC code.
3. **Track SOC code-to-title mapping across data refreshes** to detect title changes (cosmetic) vs. code changes (structural).
4. **Ingest the CIP-to-SOC crosswalk as a reference table** in the Silver zone. This is the critical bridge between education and occupation data.
5. **Plan for O*NET SOC detail codes** (XX-XXXX.XX format) by joining on the 7-character prefix when integrating O*NET data.
6. **Monitor for SOC 2028 announcement** and plan migration when crosswalk is published.

---

## Resolution Status: PASS -- No Action Required
