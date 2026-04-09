# Audit Trail: Business Glossary -- silver-base-bls-ooh

**Date:** 2026-04-07
**Agent:** @data-steward
**Mode:** Greenfield
**Domain:** U.S. Labor Market -- Occupation-Level Employment Projections
**Spec:** docs/specs/silver-base-bls-ooh.md

---

## Business Term Proposals: silver-base-bls-ooh

### New Terms Proposed

| Term ID | Term | Source | Category | Status |
|---------|------|--------|----------|--------|
| BT-027 | SOC Code | external-standard | classification | AUTO-APPROVED |
| BT-028 | Occupation Title | external-standard | entity | AUTO-APPROVED |
| BT-029 | SOC Major Group | domain-standard | classification | AUTO-APPROVED |
| BT-030 | SOC Major Group Name | domain-standard | classification | AUTO-APPROVED |
| BT-031 | Employment Current | external-standard | measurement | AUTO-APPROVED |
| BT-032 | Employment Projected | external-standard | measurement | AUTO-APPROVED |
| BT-033 | Employment Change | external-standard | measurement | AUTO-APPROVED |
| BT-034 | Employment Change Percent | external-standard | measurement | AUTO-APPROVED |
| BT-035 | Annual Average Openings | external-standard | measurement | AUTO-APPROVED |
| BT-036 | Median Annual Wage (Occupation) | external-standard | measurement | AUTO-APPROVED |
| BT-037 | Median Wage Capped | domain-standard | classification | AUTO-APPROVED |
| BT-038 | Education Code (BLS) | domain-standard | classification | AUTO-APPROVED |
| BT-039 | Education Level Name | domain-standard | classification | AUTO-APPROVED |
| BT-040 | Broad Occupation Flag | project-specific | derived | PROPOSED |
| BT-041 | Growth Category | project-specific | derived | PROPOSED |
| BT-042 | Wage Available | project-specific | derived | PROPOSED |
| BT-043 | Catchall Flag | project-specific | derived | PROPOSED |
| BT-044 | Work Experience Code (BLS) | domain-standard | classification | AUTO-APPROVED |
| BT-045 | Training Code (BLS) | domain-standard | classification | AUTO-APPROVED |
| BT-046 | Projection Cycle | external-standard | temporal | AUTO-APPROVED |

### Existing Terms Updated (used_in_models extended)

| Term ID | Term | Change |
|---------|------|--------|
| BT-015 | Record ID | Added "silver-base-bls-ooh" to used_in_models |
| BT-016 | Source Load Date | Added "silver-base-bls-ooh" to used_in_models |
| BT-017 | Ingestion Timestamp | Added "silver-base-bls-ooh" to used_in_models |

### Ambiguities Found

None. All BLS terminology is well-defined in domain context and EDA reports. No conflicting definitions detected across specs.

---

## Source Attribution

### External Standard Terms (Auto-Approved: 9 terms)

BT-027 (SOC Code), BT-028 (Occupation Title), BT-031-035 (employment metrics), BT-036 (Median Annual Wage), BT-046 (Projection Cycle) -- all sourced from the BLS Employment Projections program (Table 1.7) and the SOC 2018 taxonomy maintained by OMB. These are authoritative federal statistical definitions. No human approval required.

### Domain Standard Terms (Auto-Approved: 7 terms)

BT-029 (SOC Major Group), BT-030 (SOC Major Group Name), BT-037 (Median Wage Capped), BT-038 (Education Code), BT-039 (Education Level Name), BT-044 (Work Experience Code), BT-045 (Training Code) -- all sourced from BLS classification systems that are widely accepted domain standards. The integer code schemes (education 1-8, experience 1-3, training 1-6) are BLS-defined encodings specific to the Employment Projections data tables. Auto-approved as domain standards.

### Project-Specific Terms (Requires Human Approval: 4 terms)

- **BT-040 (Broad Occupation Flag):** Pipeline-derived flag identifying 7 rolled-up SOC codes. The concept of "broad vs. detailed" is from SOC, but the specific flag and the hardcoded list of 7 codes are project inventions.
- **BT-041 (Growth Category):** Pipeline-derived bucketing of employment_change_pct into 6 tiers. The thresholds are informed by BLS convention but the specific bucket definitions are project-specific.
- **BT-042 (Wage Available):** Pipeline-derived convenience flag. A simple null-check wrapper with no independent business meaning beyond filtering.
- **BT-043 (Catchall Flag):** Pipeline-derived flag based on "all other" substring matching. The concept of residual categories is BLS standard, but the flag and its downstream confidence implications are project-specific.

All 4 project-specific terms are in PROPOSED status and require human approval per REQUIRE_HUMAN_APPROVAL = true.

---

## Decision Rationale

1. **SOC Code as classification, not entity:** SOC Code is classified as "classification" (not "entity") because it is a taxonomy code, analogous to how CIP Code (BT-003) is classified. The entity is the occupation itself, which SOC code classifies.

2. **Separate terms for code and name pairs:** Following the pattern established for CIP Family (BT-005) and CIP Family Name (BT-006), SOC Major Group and SOC Major Group Name are separate terms because they serve distinct purposes (join key vs. display label).

3. **Education/Experience/Training as domain-standard:** The integer encoding schemes (1-8, 1-3, 1-6) are specific to BLS Employment Projections data tables but are used consistently across all BLS EP publications. They are not project inventions -- they are BLS classifications. Classified as domain-standard rather than project-specific.

4. **Median Wage Capped as domain-standard:** The top-coding practice and $239,200 threshold are BLS OES methodology, not a project invention. The flag is a direct representation of a BLS data characteristic.

5. **Reuse of existing BT-015, BT-016, BT-017:** Record ID, Source Load Date, and Ingestion Timestamp are pipeline infrastructure concepts already defined for the College Scorecard Silver table. Their definitions are general enough to apply to the BLS OOH Silver table without modification -- only the used_in_models list needed updating.
