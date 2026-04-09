# Entity Resolution Assessment: silver-base-college-scorecard
**Date:** 2026-04-06
**Agent:** @entity-resolver
**Spec:** docs/specs/silver-base-college-scorecard.md
**Prior Assessment:** governance/reviews/raw-ingest-college-scorecard-entity-resolution.md (2026-04-05)

---

## Finding: No Entity Resolution Required

Both primary entity identifiers in `base.college_scorecard` are authoritative federal codes managed by the National Center for Education Statistics (NCES). No fuzzy matching, deduplication, or cross-reference resolution is needed.

---

## Entity-by-Entity Assessment

### 1. Institution (UNITID)

| Aspect | Assessment |
|--------|-----------|
| Identifier | UNITID — 6-digit IPEDS identifier |
| Authority | NCES/IPEDS (federal standard) |
| Stability | Stable across years; assigned once per institution |
| Uniqueness | 2,559 distinct values; each maps to exactly one INSTNM in this snapshot |
| Resolution needed | **No** |

**Rationale:** UNITID is the authoritative federal identifier for U.S. postsecondary institutions. It is assigned by NCES and is stable across reporting cycles. The Bronze-zone assessment (2026-04-05) confirmed zero cases of the same UNITID mapping to different names. The 15 institution names that map to multiple UNITIDs represent genuinely distinct institutions (multi-campus systems or unrelated institutions sharing a name) — this is correct data, not a resolution problem.

### 2. Academic Program (CIPCODE)

| Aspect | Assessment |
|--------|-----------|
| Identifier | CIPCODE — Classification of Instructional Programs code |
| Authority | NCES CIP taxonomy (federal standard) |
| Stability | Stable within taxonomy version; updates occur on ~10-year cycles (current: CIP 2020) |
| Uniqueness | 390 distinct codes across 69,947 rows |
| Resolution needed | **No** |

**Rationale:** CIP codes are a standardized federal taxonomy with no ambiguity. The Silver transformation normalizes the storage format from 4-digit ("5202") to the canonical XX.XXXX format ("52.02") by inserting a dot separator at position 2. This is a format normalization handled by the transformer, not an entity resolution concern. The CIP-to-CIPDESC mapping is 1:1 in this dataset.

### 3. Institution-Program Grain (UNITID x CIPCODE x CREDLEV)

| Aspect | Assessment |
|--------|-----------|
| Identifier | Composite: unitid + cipcode + credlev |
| Uniqueness | 69,947 combinations; zero duplicates confirmed in EDA |
| Resolution needed | **No** |

**Rationale:** The grain is fully determined by three authoritative identifiers. The spec enforces grain integrity via `compute_grain_id()` with dedup grain fields `[unitid, cipcode, credlev]`. No resolution logic is needed at the grain level.

---

## Entity Lifecycle Considerations

The domain context identifies five lifecycle event types. None require active resolution in this Silver base table:

| Event Type | Resolution Action | Status |
|-----------|-------------------|--------|
| Institution closure | Detect via UNITID disappearance across refreshes | Not applicable to single-snapshot MVP |
| Program discontinuation | Detect via CIP absence for a UNITID across refreshes | Not applicable to single-snapshot MVP |
| Institution name change | Track UNITID-to-INSTNM mapping across refreshes | Not applicable to single-snapshot MVP |
| Program reclassification | CIP taxonomy updates (~10-year cycle) | No action needed; current data uses CIP 2020 |
| Privacy suppression change | Cohort-driven; fields flip between null and populated | Not an entity identity issue |

When multi-snapshot refresh support is added, lifecycle tracking should be revisited as a separate spec concern. For the current MVP (single snapshot, full-table replace), no lifecycle-driven resolution is required.

---

## Entity Registry Impact

No entries are needed in `governance/entity-registry.json` for this spec. Both UNITID and CIPCODE are externally governed identifiers with no project-specific resolution logic.

If future specs introduce entities that require resolution (e.g., employer names from BLS data, or SOC codes from the CIP-to-SOC crosswalk), the entity registry will be initialized at that time.

---

## Consistency with Bronze Assessment

This assessment is consistent with the Bronze-zone entity resolution review (2026-04-05), which concluded "PASS — No Action Required." The Silver zone inherits the same clean identifier properties and adds only format normalization (CIP dot insertion), which does not affect entity identity.

---

## Resolution Status: PASS — No Action Required

No entity resolution logic, fuzzy matching, confidence scoring, or manual review workflow is needed for `silver-base-college-scorecard`. Both primary identifiers are authoritative federal codes that can be used as-is.
