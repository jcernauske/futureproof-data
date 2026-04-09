# Entity Resolution Assessment: gold-career-outcomes-college-scorecard
**Date:** 2026-04-06
**Agent:** @entity-resolver
**Spec:** docs/specs/gold-career-outcomes-college-scorecard.md
**Prior Assessments:**
- governance/reviews/raw-ingest-college-scorecard-entity-resolution.md (2026-04-05)
- governance/reviews/silver-base-college-scorecard-entity-resolution.md (2026-04-06)

---

## Finding: No Entity Resolution Required

This Gold spec operates on a single data source (`base.college_scorecard` from the Silver zone). All entity identifiers are authoritative federal codes inherited from Silver with no modifications at the Gold layer. No entity resolution, fuzzy matching, cross-source reconciliation, or identity disambiguation is needed.

---

## Assessment Basis

### Data Flow
- **Source:** `base.college_scorecard` (Silver zone, 69,947 rows)
- **Target:** `consumable.career_outcomes` (Gold zone)
- **Entity identity transformation at Gold layer:** None. Identity fields (unitid, cipcode, credlev, institution_name, program_name, cip_family, cip_family_name, credential_level) are carried forward from Silver without modification.

### Spec Designation
The Gold spec explicitly marks @entity-resolver as SKIP in its "Conditionally Skippable Agents" table (line 179-184), with justification: "Single-source data, no cross-source entity matching needed yet (no BLS/O*NET integration in this spec)."

The pre-implementation governance review (2026-04-06) validated this skip decision as "PASS -- justified. No second data source exists yet."

---

## Entity-by-Entity Assessment

### 1. Institution (UNITID)

| Aspect | Assessment |
|--------|-----------|
| Identifier | UNITID -- 6-digit IPEDS identifier |
| Authority | NCES/IPEDS (federal standard) |
| Gold-layer changes | None. Carried from Silver as-is. |
| Resolution needed | **No** |

### 2. Academic Program (CIPCODE)

| Aspect | Assessment |
|--------|-----------|
| Identifier | CIPCODE -- CIP code in XX.XX format (normalized in Silver) |
| Authority | NCES CIP taxonomy (federal standard) |
| Gold-layer changes | None. Carried from Silver as-is. |
| Resolution needed | **No** |

### 3. CIP Family (cip_family)

| Aspect | Assessment |
|--------|-----------|
| Identifier | cip_family -- 2-digit CIP family code |
| Authority | Derived from CIPCODE (first 2 digits) |
| Gold-layer changes | None. Carried from Silver. Used as partition key for window functions (percentile bands, earnings rank). |
| Resolution needed | **No** |

**Note:** CIP family is used as a grouping key for derived fields (percentile bands, earnings rank) but is not an entity requiring resolution. The grouping is deterministic based on the authoritative CIP code.

### 4. Institution-Program Grain (UNITID x CIPCODE x CREDLEV)

| Aspect | Assessment |
|--------|-----------|
| Identifier | Composite grain: unitid + cipcode + credlev |
| Gold-layer changes | Used to compute `record_id` via `compute_grain_id()` with prefix 'co'. This is a deterministic hash, not an entity resolution operation. |
| Resolution needed | **No** |

---

## New Derived Fields: Not Entity Resolution Concerns

The Gold spec introduces derived fields (percentile bands, debt-to-earnings ratio, confidence tier, earnings rank, program value index). These are computed metrics, not entity identifiers. They do not introduce new entities or create entity resolution needs.

---

## Entity Registry Impact

No entries are needed in `governance/entity-registry.json` for this spec. The assessment from the Silver layer remains current: both UNITID and CIPCODE are externally governed identifiers with no project-specific resolution logic. The Gold layer adds no new entity types.

---

## Consistency with Prior Assessments

This assessment is consistent with the chain of prior entity resolution reviews:

| Zone | Assessment | Conclusion |
|------|-----------|------------|
| Raw (2026-04-05) | No resolution needed | UNITID and CIPCODE are authoritative federal IDs |
| Silver (2026-04-06) | No resolution needed | Silver adds format normalization (CIP dot insertion) only |
| Gold (2026-04-06) | No resolution needed | Gold carries identity fields from Silver without modification |

The entity identity story is unchanged across all three zones for College Scorecard data.

---

## Future Integration: When Entity Resolution Will Be Required

The Gold spec's "Future Integration Notes" (lines 235-239) identify the trigger for entity resolution work:

| Future Event | Entity Resolution Impact |
|-------------|------------------------|
| BLS Occupational Outlook Handbook integration | SOC codes introduced. SOC-to-institution mapping may need resolution if employer/geography data is included. |
| O*NET Task-Level Data integration | SOC codes shared with BLS. Same resolution strategy applies. |
| CIP-to-SOC Crosswalk implementation | **Primary trigger.** Maps CIP codes (this dataset) to SOC codes (BLS/O*NET). The crosswalk is a many-to-many mapping maintained by NCES/BLS. This is a taxonomy mapping operation, not fuzzy entity resolution, but it will require @entity-resolver to validate that CIP codes in the crosswalk match the CIP codes in `base.college_scorecard` and that SOC codes match the BLS/O*NET sources. |
| Multi-year snapshot support | Lifecycle events (institution closure, program discontinuation, name changes) will need tracking across refreshes. Currently deferred per single-snapshot MVP. |

**Recommendation:** When the second Gold spec (`gold-career-projections`) is drafted to combine College Scorecard with BLS/O*NET data, @entity-resolver should be a required (non-skippable) agent in that spec's workflow to handle CIP-to-SOC crosswalk validation and any SOC-level entity reconciliation.

---

## Resolution Status: PASS -- No Action Required

No entity resolution logic, fuzzy matching, confidence scoring, or manual review workflow is needed for `gold-career-outcomes-college-scorecard`. This is a single-source Gold table where all entity identifiers are authoritative federal codes carried forward from Silver without modification. The assessment documents future integration points where entity resolution will become necessary.
