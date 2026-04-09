# Entity Resolution Assessment: silver-base-bls-ooh
**Date:** 2026-04-07
**Agent:** @entity-resolver
**Entity Type:** Occupation (SOC Code)
**Resolution Strategy:** ID-based resolution (authoritative federal identifier)
**Zone:** Silver

---

## Finding: No Active Entity Resolution Required

This is a single-source Silver transformation of BLS Employment Projections data. SOC codes are authoritative federal identifiers maintained by the Bureau of Labor Statistics under the SOC 2018 taxonomy. No fuzzy matching, deduplication, or cross-source resolution is performed in this spec.

Cross-source entity resolution (CIP-to-SOC mapping via the NCES crosswalk) is scoped to a separate Silver crosswalk spec, not this one. This assessment documents the entity resolution characteristics of `base.bls_ooh` to inform that downstream work.

---

## Entity Identifier Quality

### SOC Code Uniqueness and Format
| Metric | Value | Status |
|--------|-------|--------|
| Total rows | 832 | -- |
| Distinct SOC codes | 832 | PASS: 100% unique, grain holds |
| SOC code format (XX-XXXX) | 832 of 832 valid | PASS: zero violations |
| Null SOC codes | 0 | PASS |
| SOC code-to-title mapping | 1:1 | PASS: no ambiguity |
| SOC major groups represented | 22 of 22 | PASS: full coverage |

**Resolution confidence: 1.0** -- exact ID match. SOC codes are stable, well-formed, and unambiguous within this dataset.

---

## Entity Subpopulations Affecting Downstream Resolution

### 1. Broad Occupation Codes (7 rows)

Seven SOC codes represent rolled-up/broad occupations rather than detailed occupations. The transformer flags these via `broad_occupation_flag = True` using a hardcoded list (not pattern matching, per spec rationale).

| SOC Code | Title | Downstream Impact |
|----------|-------|-------------------|
| 13-1020 | Buyers and purchasing agents | Maps to 13-1021 + 13-1022 in O*NET |
| 13-2020 | Property appraisers and assessors | Maps to 13-2021 + 13-2022 + 13-2023 in O*NET |
| 29-2010 | Clinical laboratory technologists and technicians | Maps to multiple O*NET detailed codes |
| 31-1120 | Home health and personal care aides | Maps to multiple O*NET detailed codes |
| 39-7010 | Tour and travel guides | Maps to 39-7011 + 39-7012 in O*NET |
| 47-4090 | Miscellaneous construction and related workers | Broad + miscellaneous; weakest crosswalk signal |
| 51-2090 | Miscellaneous assemblers and fabricators | Broad + miscellaneous; weakest crosswalk signal |

**Entity resolution implications:**
- These codes exist in BLS data at the broad level (XX-XX20, XX-XX90, etc.) but O*NET uses detailed codes (XX-XXXX.XX). A direct SOC-to-SOC join will miss these unless the crosswalk handles parent-child fan-out.
- CIP-SOC crosswalk matches through broad codes should carry lower confidence (recommend 0.8 max vs. 1.0 for detailed codes).
- Gold zone stat computation should annotate results derived from broad codes so users understand the aggregation level.

**No overlap with catchall categories.** None of the 7 broad codes contain "all other" in their titles. The two flags are independent, as confirmed by the Silver EDA.

### 2. Catchall Categories (70 rows)

The Silver EDA corrected the spec's original count from 46 to 70 rows. All 70 titles contain the case-insensitive substring "all other." These are legitimate BLS residual categories representing occupations not individually classified within a minor group.

**Entity resolution implications:**
- Catchall SOC codes (e.g., 11-9199 "Managers, all other") have valid CIP-SOC crosswalk mappings but the mapping is inherently imprecise -- a graduate mapped to "Managers, all other" could be in any of dozens of specific management roles.
- Career guidance generated from catchall mappings should carry a lower confidence tier. Recommend crosswalk confidence cap of 0.7 for catchall SOC codes.
- Catchall codes are not resolvable to more specific occupations without additional data (e.g., O*NET task-level data does not help here because the catchall is the most detailed level BLS publishes).

### 3. Null-Wage Occupations (23 rows)

Twenty-three occupations have null `median_annual_wage`, flagged via `wage_available = False`. These are primarily physicians/surgeons (14 rows) and performers (5 rows).

**Entity resolution implications:**
- These occupations resolve cleanly by SOC code -- the entity identity is not in question.
- However, the null wages create a downstream data completeness issue: when the CIP-SOC crosswalk maps a medical program (e.g., CIP 51.1201 "Medicine") to physician SOC codes, the ERN stat will be null despite physicians being high earners.
- This is not an entity resolution problem but should be noted in the crosswalk confidence model as a data availability limitation.

---

## Cross-Source Resolution Strategy (Informational)

This section documents the entity resolution landscape for downstream specs. No resolution is performed here.

### Taxonomy Linkage Map
```
College Scorecard (CIP XX.XXXX)
        |
        | CIP-to-SOC Crosswalk (many-to-many, separate spec)
        v
BLS OOH (SOC XX-XXXX)  <--->  O*NET (SOC XX-XXXX.XX)
  [this spec]                   [direct join on 7-char prefix]
```

### SOC Code Readiness for Downstream Joins

| Join Target | Method | Confidence | Notes |
|-------------|--------|------------|-------|
| O*NET detailed codes | Exact match on `soc_code` = left 7 chars of O*NET code | 1.0 for detailed codes; 0.8 for broad codes | O*NET uses XX-XXXX.XX; join on XX-XXXX prefix. 7 broad codes need parent-child fan-out. |
| CIP-SOC Crosswalk | Exact match on `soc_code` | 1.0 for detailed; 0.7 for catchall; 0.8 for broad | Many-to-many relationship. Confidence varies by entity subpopulation. |
| Future SOC 2028 data | Crosswalk required | TBD | SOC 2028 expected ~2028. BLS will publish a 2018-to-2028 crosswalk. Low current risk. |

### Recommended Confidence Tiers for Crosswalk Spec

| SOC Code Category | Count | Recommended Max Crosswalk Confidence | Rationale |
|-------------------|-------|--------------------------------------|-----------|
| Detailed occupation (neither broad nor catchall) | 755 | 1.0 | Clean 1:1 mapping, specific occupation |
| Broad occupation (`broad_occupation_flag`) | 7 | 0.8 | Maps to multiple O*NET children; aggregated stats |
| Catchall category (`catchall_flag`) | 70 | 0.7 | Heterogeneous residual category; weak signal for career guidance |

---

## Transformer Implementation Review

The transformer at `src/silver/bls_ooh_transformer.py` correctly implements entity handling:

1. **SOC code validation** -- regex `^\d{2}-\d{4}$` enforced; invalid codes raise `ValueError` (hard failure, not silent skip). Correct.
2. **Broad occupation detection** -- hardcoded `frozenset` of 7 codes, not pattern matching. Correct per spec rationale.
3. **Catchall detection** -- case-insensitive substring match `"all other" in occupation_title.lower()`. Correct; matches the EDA-validated count of 70.
4. **SOC major group derivation** -- first 2 characters of `soc_code`, validated against 22-entry lookup. Unknown groups raise `ValueError`. Correct.
5. **Record ID** -- deterministic `compute_grain_id` on `soc_code` with `ooh` prefix. Correct for grain integrity.

No entity resolution logic is needed in the transformer. The flags (`broad_occupation_flag`, `catchall_flag`, `wage_available`) correctly prepare the data for downstream resolution decisions.

---

## Resolution Statistics

| Metric | Value |
|--------|-------|
| Total entities assessed | 832 |
| Resolution method | ID-based (authoritative SOC code) |
| Resolution confidence | 1.0 (all rows) |
| Entities requiring fuzzy matching | 0 |
| Entities flagged for human review | 0 |
| Broad occupation codes (downstream flag) | 7 |
| Catchall categories (downstream flag) | 70 |
| Null-wage entities (data completeness flag) | 23 |
| Lifecycle events discovered | 0 (single snapshot) |

---

## Resolution Status: PASS -- No Action Required

Entity resolution is not required for this single-source Silver transformation. SOC codes are authoritative, unique, well-formed, and unambiguous. The transformer correctly flags the three entity subpopulations (broad, catchall, null-wage) that will affect downstream cross-source resolution confidence.

The entity registry will be created when the CIP-SOC crosswalk spec is implemented, at which point the confidence tiers documented here should be applied.
