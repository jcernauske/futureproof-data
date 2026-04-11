# Audit Trail: Entity Resolution — raw-ingest-karpathy-ai-exposure
**Date:** 2026-04-09
**Agent:** @entity-resolver
**Spec:** raw-ingest-karpathy-ai-exposure
**Entity Type:** BLS Occupation (SOC Code + Karpathy Slug)
**Zone:** Bronze (assessment only — resolution deferred to Silver)

---

## Entity Resolution Complexity Assessment

**Complexity: LOW-MEDIUM**

This is a small (342 rows), single-grain dataset keyed by Karpathy slug. Entity resolution is straightforward in principle — occupations are identified by slug in the source, and the companion `occupations.csv` provides SOC codes for most rows. The complexity arises from three SOC coverage gaps that must be resolved in Silver zone.

---

## Entity Types Identified

### Primary Entity: BLS Occupation

| Attribute | Value |
|-----------|-------|
| Entity type | Occupation |
| Source identifier | `slug` (kebab-case, e.g., "financial-analysts") |
| Canonical identifier | `soc_code` (BLS SOC 2018, format XX-XXXX) |
| Grain | One row per slug |
| Total entities | 342 |
| Identifier uniqueness | 342 unique slugs (confirmed — zero duplicates) |

### Identifier Coverage Breakdown

| SOC Status | Count | Percentage | Resolution Strategy |
|------------|-------|------------|-------------------|
| Direct detailed SOC (XX-XXXX, not ending in 0) | 240 | 70.2% | ID-based resolution — confidence 1.0 |
| Broad/roll-up SOC (ending in 0) | 50 | 14.6% | Propagation to detailed codes in Silver — confidence 0.85 |
| Null SOC | 52 | 15.2% | Title-match against BLS OOH in Silver — confidence 0.7-0.9 |

**Note on broad code count:** The raw data contains 50 SOC codes ending in 0. The EDA report and domain context document 46 as "broad codes." The discrepancy of 4 likely represents codes that happen to end in 0 but are valid detailed occupations in the BLS OOH (i.e., they have direct matches in our `base.bls_ooh` table and do not require expansion). This should be validated during Silver zone processing by checking each code against the BLS OOH reference table. The resolution strategy is the same regardless: match against BLS OOH first (direct match), then treat unmatched codes ending in 0 as broad codes requiring prefix-based propagation.

---

## Decision Log

### Decision 1: No entity resolution required at Bronze zone
- **Rationale:** Bronze zone ingests raw data as-is. The slug is the Bronze grain, and SOC codes are carried forward from source without modification. Entity resolution (mapping slug to canonical SOC) is a Silver zone responsibility per the spec.
- **Confidence:** 1.0
- **Method:** Pipeline zone architecture (Bronze = faithful raw capture)

### Decision 2: Three-tier SOC resolution strategy for Silver zone
- **Rationale:** The 342 occupations fall into three resolution tiers based on SOC coverage quality. Each tier requires a different resolution method in Silver:
  - **Tier 1 (240 rows, 70.2%):** Direct SOC code match. These have valid XX-XXXX codes that should match BLS OOH directly. Resolution confidence 1.0.
  - **Tier 2 (50 rows, 14.6%):** SOC codes ending in 0 (broad/roll-up codes). These represent occupation groups rather than specific occupations. Silver should propagate the Karpathy exposure score from the broad code to all detailed codes (XX-XXXX) sharing the same prefix. User confirmed this approach. Resolution confidence 0.85 (assumes uniform exposure within the group).
  - **Tier 3 (52 rows, 15.2%):** Null SOC code. Silver should attempt case-insensitive title match against `base.bls_ooh.occupation_title`, then fuzzy match for non-exact hits. Resolution confidence varies (0.9 for exact title match, 0.7-0.8 for fuzzy match).
- **Confidence:** 0.95
- **Method:** Domain analysis informed by EDA report and domain context document

### Decision 3: Null SOC concentration is category-dependent
- **Rationale:** Null SOC codes are not randomly distributed. They concentrate in specific BLS categories: transportation-and-material-moving (54.5% null), installation-maintenance-and-repair (33.3%), production (31.3%), and computer-and-information-technology (30.0%). This pattern suggests these categories contain combined occupation groups in Karpathy's source that correspond to multiple individual SOC codes in BLS OOH. Silver zone title matching should be aware that these may be many-to-one relationships (one Karpathy slug covering multiple BLS detailed occupations).
- **Confidence:** 0.9
- **Method:** EDA category analysis

### Decision 4: No entity lifecycle events present
- **Rationale:** This is a static, single-snapshot dataset. No name changes, mergers, splits, or reclassifications exist within the source data. The SOC taxonomy version (2018) matches our existing BLS OOH pipeline, so no cross-vintage reconciliation is needed. The perfect wage alignment ($0 difference across 241 comparable rows) confirms data vintage consistency.
- **Confidence:** 1.0
- **Method:** Cross-validation with BLS OOH data

### Decision 5: Slug is a source-only identifier, not a canonical entity ID
- **Rationale:** The Karpathy slug (e.g., "financial-analysts") is a project-specific kebab-case identifier derived from BLS occupation titles. It is NOT a standard taxonomy code and should NOT be used as a canonical entity identifier downstream. It serves as the Bronze grain and a provenance field in Silver, but the canonical identifier for cross-source integration is the SOC code. The slug should be retained in Silver for traceability but never used as a join key beyond the Karpathy source.
- **Confidence:** 1.0
- **Method:** Domain knowledge (SOC is the federal standard for occupation identification)

### Decision 6: No duplicate SOC codes in source data
- **Rationale:** Where SOC codes are present (290 rows), all are unique. Zero duplicate SOC codes exist in the raw data. This means no deduplication logic is needed at Bronze, and the spec's Silver dedup rule (take the row with highest `num_jobs_2024`) is defensive code for an edge case that does not currently exist.
- **Confidence:** 1.0
- **Method:** Data verification

### Decision 7: Broad code propagation may introduce SOC duplicates in Silver
- **Rationale:** When Silver propagates exposure scores from broad codes to detailed codes, one Karpathy row may produce multiple Silver rows (one per detailed SOC under the broad prefix). This is expected and desired (maximizes coverage), but the Silver grain must be `soc_code` (not `slug`), and the propagated rows should carry the parent slug and a `soc_resolved_method = 'broad_propagation'` flag.
- **Confidence:** 0.9
- **Method:** Domain analysis of SOC hierarchy structure

---

## Entity Resolution Report

### Resolved Entities (Bronze Assessment)

At Bronze zone, no resolution is performed. Assessment of resolution readiness:

| Category | Count | Resolution Method (Silver) | Expected Confidence | Notes |
|----------|-------|---------------------------|-------------------|-------|
| Direct SOC match | 240 | ID-based (exact SOC lookup) | 1.0 | Straightforward join to BLS OOH |
| Broad SOC code | 50 | Prefix-based propagation | 0.85 | One score applied to multiple detailed occupations |
| Null SOC | 52 | Title match (exact then fuzzy) | 0.7-0.9 | Concentrated in 4 categories |

### Lifecycle Events Discovered

None. Static dataset, single vintage, no temporal dimension.

### Unresolved / Flagged for Review

| Category | Count | Issue | Recommendation |
|----------|-------|-------|----------------|
| Null SOC — transportation | ~12 | Combined occupation groups with no SOC | Title-match in Silver; accept unresolved rows as non-joinable |
| Null SOC — installation/repair | ~4 | Combined occupation groups with no SOC | Same as above |
| Null SOC — production | ~5 | Combined occupation groups with no SOC | Same as above |
| Null SOC — computer/IT | ~3 | Combined occupation groups with no SOC | Same as above |
| Null SOC — other categories | ~28 | Various reasons for missing SOC | Title-match in Silver |
| Military row | 1 | Null SOC, null wage, null employment — structurally incomplete | Allow; known BLS edge case |
| Broad code count discrepancy | 4 | 50 codes end in 0 vs. 46 reported as broad in EDA | Validate against BLS OOH in Silver; 4 may be valid detailed codes |

### Resolution Statistics

- Total entities assessed: 342
- Ready for direct resolution (Tier 1): 240 (70.2%)
- Require broad code propagation (Tier 2): 50 (14.6%)
- Require title-based resolution (Tier 3): 52 (15.2%)
- Entity lifecycle events: 0
- Flagged for manual review: 1 (military row)
- Cross-source validation: PASS (wage alignment perfect, SOC vintage consistent)

---

## Recommendations for Silver Zone

1. **SOC resolution order:** Process Tier 1 (direct match) first, then Tier 2 (broad propagation), then Tier 3 (title match). This maximizes coverage with highest-confidence matches first.
2. **Track resolution method:** Every Silver row must carry `soc_resolved_method` indicating how the SOC was determined: "direct", "broad_propagation", or "title_match" (or "unresolved" for failures).
3. **Broad code validation:** Before propagating broad codes, verify each of the 50 codes ending in 0 against `base.bls_ooh.soc_code`. If a code has a direct match, treat it as Tier 1 (not broad). This will clarify the 46-vs-50 discrepancy.
4. **Title match approach:** Use case-insensitive exact match first, then normalized fuzzy match (removing articles, standardizing abbreviations). Flag any fuzzy match with confidence below 0.7 for manual review.
5. **Coverage target:** After all three resolution tiers, the domain context estimates 595 of 832 BLS OOH occupations (71.5%) will have AI exposure scores. This is sufficient for hackathon MVP.

---

## Artifacts Produced
- This audit trail document

## References
- Spec: `docs/specs/raw-ingest-karpathy-ai-exposure.md`
- EDA: `governance/eda/raw-karpathy-ai-exposure-eda.md` (referenced via audit trail)
- Domain context: `governance/domain-context.md` (Karpathy AI Exposure section)
- Prior entity resolution (BLS OOH): `governance/audit-trail/raw-ingest-bls-ooh-entity-resolution.md`
- Raw data: `data/raw/karpathy_cache/occupations.csv`, `data/raw/karpathy_cache/scores.json`
