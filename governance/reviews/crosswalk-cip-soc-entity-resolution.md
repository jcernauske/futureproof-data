# Entity Resolution Assessment: crosswalk-cip-soc

**Date:** 2026-04-08
**Agent:** @entity-resolver
**Spec:** docs/specs/crosswalk-cip-soc.md
**Decision:** SKIP CONFIRMED

## Assessment

Entity resolution is not required for the CIP-SOC crosswalk dataset. The spec's recommendation to skip this step is correct.

### Rationale

1. **Authoritative taxonomy codes, not entity names.** Both CIP codes (XX.XXXX) and SOC codes (XX-XXXX) are government-assigned deterministic identifiers maintained by NCES and BLS respectively. They are not derived from free-text input, user entry, or any source that would introduce ambiguity.

2. **No fuzzy matching scenarios.** The crosswalk file is a single authoritative source published by NCES/BLS. There are no multiple source systems providing conflicting representations of the same entity. Each CIP-SOC pair is either present in the crosswalk or it is not.

3. **No entity lifecycle complexity.** The crosswalk is versioned at the taxonomy level (CIP 2020 x SOC 2018). Within a single version, codes do not change, merge, split, or get reclassified. When taxonomy versions change (approximately every 10 years), the entire crosswalk is republished as a new version -- that is a separate ingest, not an entity resolution problem.

4. **Join semantics are exact match.** The Silver transformation joins crosswalk CIP codes to `base.college_scorecard.cipcode` and crosswalk SOC codes to `base.bls_ooh.soc_code` and `base.onet_occupations.bls_soc_code`. All joins use exact string equality on standardized code formats. No normalization, deduplication, or confidence scoring is needed.

5. **Coverage gaps are not resolution gaps.** The spec explicitly notes that some CIP codes lack SOC matches (coded as 99-9999, filtered out in Silver) and some codes may not match downstream tables. These are coverage gaps by design, not entity ambiguity. The spec handles them through `has_scorecard_match`, `has_bls_match`, `has_onet_match` flags and `match_quality` derivation.

### What would change this assessment

Entity resolution would become relevant if:
- The project needed to bridge across taxonomy versions (e.g., CIP 2010 codes to CIP 2020 codes)
- Source systems used non-standard or truncated code formats requiring normalization beyond simple validation
- The crosswalk were assembled from multiple conflicting sources rather than a single authoritative publication

None of these conditions apply to this spec.

## Resolution Statistics

- Total entities processed: 0
- Exact matches: N/A
- Fuzzy matches: N/A
- Flagged for review: 0
- Entity registry updates: None required
