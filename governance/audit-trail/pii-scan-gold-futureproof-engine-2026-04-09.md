## PII Scan Report: gold-futureproof-engine
**Date:** 2026-04-09
**Agent:** @pii-scanner
**Spec:** docs/specs/gold-futureproof-engine.md
**Domain:** Education / Career Guidance
**Tables Scanned:** consumable.program_career_paths (626,406 rows), consumable.career_branches (15,944 rows)
**Total Records Scanned:** 642,350
**PII Instances Found:** 0

### Scan Methodology

1. Read spec to identify all fields and their provenance.
2. Read governance/domain-context.md PII Expectations sections for all four upstream sources (College Scorecard, BLS OOH, O*NET, CIP-SOC crosswalk). All confirm zero PII.
3. Examined schemas of both Gold tables (40 fields in program_career_paths, 24 fields in career_branches).
4. Inspected sample data rows from both tables.
5. Ran regex-based pattern scans across all string fields for SSN patterns (XXX-XX-XXXX) and email patterns. Zero matches.
6. Reviewed institution_name field (the highest-risk text field) for personal name indicators. All values are institution names (universities, colleges), not personal names.

### Findings

| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|-------------------|
| -- | -- | -- | -- | -- | -- | -- |

**No PII detected in either table.**

### Field-by-Field Assessment

**consumable.program_career_paths (40 fields):**

| Field | Assessment | Rationale |
|-------|-----------|-----------|
| record_id | Not PII | Synthetic hash identifier (e.g., "pcp-90f1cb23391bf58c") |
| unitid | Not PII (Level 1 - Public) | IPEDS institution ID, public federal identifier. 2,550 distinct institutions. |
| institution_name | Not PII (Level 1 - Public) | University/college names, not personal names. Public institutions. |
| cipcode | Not PII | CIP classification code (e.g., "01.00"). Federal taxonomy code. |
| program_name | Not PII | Academic program names (e.g., "Agriculture, General."). Federal taxonomy labels. |
| cip_family / cip_family_name | Not PII | CIP taxonomy groupings. |
| soc_code | Not PII | SOC occupation classification code. Federal taxonomy code. |
| occupation_title / soc_major_group_name | Not PII | Occupation labels from BLS (e.g., "Animal scientists"). Not personal names. |
| stat_ern through stat_hmn | Not PII | Derived integer scores (1-10 scale). Aggregate statistics. |
| boss_* scores | Not PII | Derived integer scores. Aggregate statistics. |
| earnings_*, debt_* | Not PII | Median aggregates across student cohorts. FERPA-protected at source via suppression rules. Not individual financial records. |
| confidence_tier_program | Not PII | Categorical label. |
| median_annual_wage | Not PII | Occupation-level median from BLS. National aggregate. |
| growth_category / employment_current / education_level_name | Not PII | Occupation-level aggregates from BLS. |
| top_5_activities / top_human_activities / burnout_drivers | Not PII | JSON arrays of work activity descriptions from O*NET. Occupation-level aggregates. |
| time_pressure / work_hours | Not PII | O*NET occupation-level context scores. |
| match_quality / stats_available_count / bosses_available_count / overall_confidence | Not PII | Derived data quality metadata. |
| promoted_at | Not PII | Pipeline execution timestamp. |

**consumable.career_branches (24 fields):**

All fields are occupation codes, occupation titles, integer scores, wage aggregates, deltas, and metadata. No personal identifiers of any kind. Same assessment pattern as above -- all values are occupation-level aggregates from federal statistical agencies.

### Summary by Sensitivity

| Level | Count | Fields Affected |
|-------|-------|----------------|
| Level 1 (Public) | 3 | unitid, institution_name (public IPEDS data), all SOC/CIP codes and labels |
| Level 2 (Internal) | 0 | -- |
| Level 3 (Confidential) | 0 | -- |
| Level 4 (Restricted) | 0 | -- |

Note: unitid and institution_name are classified Level 1 (Public) because they are federally published IPEDS identifiers. They require no special handling.

### False Positive Candidates

| Field | Detected As | Why It Is Likely False | Recommendation |
|-------|------------|----------------------|----------------|
| institution_name | Could resemble personal names (e.g., "Abraham Lincoln University", "Albert Einstein College of Medicine") | These are INSTITUTION names, not personal names. Named after historical figures, not data subjects. Public entities. | No action needed. |
| occupation_title | Could resemble personal names | These are occupation labels (e.g., "Chief Executives", "Animal scientists"), not individual names. From BLS SOC taxonomy. | No action needed. |

### Regulatory Implications

No PII-related regulations apply to this data product:

- **FERPA:** Not applicable at this layer. Individual student records were already suppressed by the Department of Education before publication. This pipeline only consumes aggregated statistics.
- **HIPAA:** Not applicable. No health records.
- **CCPA/GDPR:** Not applicable. No personal data of any individual.
- **PCI DSS:** Not applicable. No payment or financial account data.

All source data originates from U.S. federal statistical agencies (Department of Education, Bureau of Labor Statistics, Department of Labor/ETA) and is published as public aggregate statistics.

### Recommendations

1. **No PII remediation required.** Confirm zero PII findings and skip PII remediation steps.
2. **No column masking, RLS, or encryption needed** for @policy-engineer.
3. **No access restrictions** beyond standard pipeline access controls.
4. **Spec concurrence:** The spec correctly identified @pii-scanner as conditionally skippable with justification "All source data is aggregated public statistics." This scan confirms that assessment.

### Justification

governance/domain-context.md PII sections for all four upstream sources (College Scorecard, BLS OOH, O*NET, CIP-SOC crosswalk) unanimously confirm no personal data. This Gold product joins those sources without introducing any new PII. All 642,350 rows contain only institutional identifiers, federal taxonomy codes, and aggregate statistical measures. Pattern-based scanning across all string fields found zero matches for SSN, email, or phone number formats.
