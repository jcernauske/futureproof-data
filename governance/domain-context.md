# Domain Context: Higher Education Outcomes
**Date:** 2026-04-05
**Agent:** @domain-context
**Based On:** governance/eda/raw-college-scorecard-eda.md (2026-04-05)
**Data Sources:** college_scorecard (U.S. Department of Education College Scorecard — Field of Study), bls_ooh (Bureau of Labor Statistics — Employment Projections / Occupational Outlook Handbook), onet (O*NET 30.2 Database — Task-Level Occupation Data)
**Confidence:** High

---

## Revision History

| Date | What Changed | Reason |
|------|-------------|--------|
| 2026-04-05 | Initial version | First domain context synthesis from EDA report |
| 2026-04-07 | Added BLS OOH section | Second data source — BLS Employment Projections (SOC-coded occupations) |
| 2026-04-07 | Added O*NET section | Third data source — O*NET 30.2 task/activity/context/pathway data. Documents missing Career Changers/Starters files, scale type system, 93 "All Other"/Military gap, and SOC code format bridging to BLS. |

---

## Domain Identification
**Domain:** Higher Education Outcomes
**Sub-domain:** Program-Level Career Outcomes (College Scorecard Field of Study)
**Description:** This data captures the labor market outcomes of bachelor's degree graduates from U.S. postsecondary institutions, organized by institution and academic program (Classification of Instructional Programs code). Each row represents a specific bachelor's degree program at a specific institution, with median earnings (1-year and 2-year post-completion), median student debt, and program completion counts. The data is published by the U.S. Department of Education as part of the College Scorecard initiative, which aims to provide transparency on higher education costs and outcomes to help students and families make informed enrollment decisions.

---

## Domain Vocabulary

### Core Terms
| Term | Definition | Source | Notes for @data-steward |
|------|-----------|--------|------------------------|
| UNITID | A unique 6-digit identifier assigned to every postsecondary institution by the Integrated Postsecondary Education Data System (IPEDS). Stable across years. | NCES/IPEDS (external standard) | Auto-approve. IPEDS is the authoritative federal database for postsecondary institutions. |
| CIPCODE | A Classification of Instructional Programs code that categorizes academic programs. Standard format is XX.XXXX (2-digit family + 4-digit detail). In this dataset, stored as 4-digit without dot separator. | NCES CIP taxonomy (external standard) | Auto-approve. Reference: https://nces.ed.gov/ipeds/cipcode/ |
| CREDLEV | An integer code indicating the credential level of the program. Values: 1=Undergraduate Certificate, 2=Associate's, 3=Bachelor's, 4=Post-baccalaureate Certificate, 5=Master's, 6=Doctoral, 7=First Professional, 8=Graduate Certificate. This dataset is filtered to CREDLEV=3 only. | College Scorecard data dictionary (external standard) | Auto-approve. Only value 3 present in this MVP dataset. |
| INSTNM | The official institution name as reported to IPEDS. | IPEDS (external standard) | Auto-approve. Note: 10 names map to multiple UNITIDs (multi-campus systems). |
| CIPDESC | The human-readable description corresponding to a CIP code. | NCES CIP taxonomy (external standard) | Auto-approve. 1:1 mapping with CIPCODE. |
| CREDDESC | The human-readable description of the credential level (e.g., "Bachelor's Degree"). | College Scorecard data dictionary (external standard) | Auto-approve. Redundant with CREDLEV in this MVP (only one value). |
| Privacy Suppression | The Department of Education's practice of replacing outcome data with null/PrivacySuppressed when program cohort sizes are too small to protect student privacy. The effective threshold is approximately 30 completers (programs with 30+ completers have 88.7% earnings availability vs. under 11% for programs with fewer than 10). | Department of Education disclosure rules | Propose as project-specific term — the concept is domain-standard but the threshold details are data-observed. |
| Median Earnings (High Estimate) | The upper bound of a confidence interval for median earnings of graduates working and not enrolled in further education, measured at 1 year and 2 years after completion. These are NOT longitudinal tracking of the same individuals — the 1yr and 2yr figures come from different cohort measurement windows. | College Scorecard methodology | Propose — important nuance that 1yr and 2yr are not the same cohort tracked over time. |
| IPEDS Completions Count | The number of students completing a program as reported to IPEDS. IPEDSCOUNT1 and IPEDSCOUNT2 represent two different measurement windows (first and second major). Highly correlated (r=0.984). | IPEDS (external standard) | Auto-approve the term; propose note about the two measurement windows. |
| Median Debt at Separation | The median cumulative federal loan debt of students who completed a program. Includes all student groups evaluated. | College Scorecard methodology | Propose — "separation" means completion or withdrawal, though this dataset focuses on completers. |
| MD_EARN_WNE | Median earnings of graduates working and not enrolled — an institution-level metric that does NOT populate in the Field of Study file. 100% null in this dataset. | College Scorecard data dictionary | Propose with CRITICAL note: this field is structurally empty at field-of-study grain. See Edge Cases. |

### Taxonomy/Classification Systems
| System | Description | Authority | Coverage in Data |
|--------|-------------|-----------|-----------------|
| CIP (Classification of Instructional Programs) | A taxonomy of academic programs used by all U.S. postsecondary institutions for federal reporting. Organized in 2-digit families (e.g., 52=Business) with 4-digit detail codes. Current version: CIP 2020. | National Center for Education Statistics (NCES) | 390 distinct codes observed across 69,947 rows. Covers all bachelor's-level programs reported to IPEDS. |
| CREDLEV (Credential Level) | Integer classification of credential types in the College Scorecard. Values 1-8 covering certificates through doctoral degrees. | U.S. Department of Education | Only value 3 (Bachelor's Degree) present — filtered during ingestion per MVP scope. |
| IPEDS ID (UNITID) | 6-digit institutional identifiers from the Integrated Postsecondary Education Data System. Assigned by NCES to every Title IV institution. | NCES/IPEDS | 2,559 distinct institutions. All values in expected 6-digit range (100,654-497,268). |
| SOC (Standard Occupational Classification) | NOT in this dataset. Classification of occupations used by BLS. Relevant because the Silver zone will need the CIP-to-SOC crosswalk to link programs to occupations. | Bureau of Labor Statistics (BLS) | 0% — not present. Required for Silver zone integration with BLS OOH and O*NET sources. |

### Enumerated Values with Business Meaning
| Field | Values | Meaning |
|-------|--------|---------|
| credlev | 3 | Bachelor's Degree (only value in this MVP dataset). Full range: 1=UG Cert, 2=Associate's, 3=Bachelor's, 4=Post-Bacc Cert, 5=Master's, 6=Doctoral, 7=First Professional, 8=Grad Cert. |
| creddesc | "Bachelor's Degree" | Human-readable label for credlev=3. |
| source_method | "bulk_csv_download" | Metadata: data was fetched via bulk CSV download from the Department of Education. |
| cipcode (2-digit families) | 01=Agriculture, 03=Natural Resources, 04=Architecture, 05=Area Studies, 09=Communication, 10=Communications Tech, 11=Computer Science, 13=Education, 14=Engineering, 15=Engineering Tech, 16=Foreign Languages, 19=Family Sciences, 22=Legal Studies, 23=English, 24=Liberal Arts, 25=Library Science, 26=Biology, 27=Math, 28=Military Science, 29=Military Tech, 30=Interdisciplinary, 31=Parks/Recreation, 38=Philosophy/Religion, 39=Theology, 40=Physical Sciences, 42=Psychology, 43=Security/Law Enforcement, 44=Public Administration, 45=Social Sciences, 46=Construction, 47=Mechanic/Repair, 49=Transportation, 50=Visual/Performing Arts, 51=Health, 52=Business, 54=History | Top 5 by row count: 52-Business (8,402), 51-Health (5,455), 50-Arts (5,254), 45-Social Sciences (5,153), 13-Education (3,742). |

---

## Entity Types

### Primary Entities
| Entity Type | Identifier Field(s) | Example | Notes for @entity-resolver |
|-------------|---------------------|---------|---------------------------|
| Institution | unitid | 110635 (Stanford University) | ID-based resolution. UNITID is stable and authoritative. No resolution needed — use UNITID as-is. Multi-campus institutions share the same name but have distinct UNITIDs (10 such cases observed). |
| Academic Program | cipcode | "5202" (Business Administration) | Code-based resolution. CIP codes are standardized but stored in non-standard 4-digit format. Silver zone must insert dot separator for crosswalk matching. |
| Institution-Program (Grain Entity) | unitid + cipcode + credlev | UNITID=110635, CIP=5202, CREDLEV=3 | This is the grain of the dataset. Each row represents one program at one institution at one credential level. 69,947 unique combinations. Zero duplicates. |

### Entity Lifecycle Events
| Event Type | How It Appears in Data | Frequency |
|-----------|----------------------|-----------|
| Institution closure | UNITID disappears from future data refreshes | Rare. Cannot be detected in a single snapshot. Track across refreshes. |
| Program discontinuation | CIP code no longer appears for a UNITID in future refreshes | Uncommon. Cannot be detected in a single snapshot. |
| Institution name change | INSTNM changes for the same UNITID across refreshes | Rare. 1:1 UNITID-to-name mapping in current snapshot is clean. |
| Program reclassification | CIP code changes (e.g., due to CIP taxonomy updates) | Very rare. CIP taxonomy updates occur on ~10-year cycles (last update: CIP 2020). |
| Privacy suppression change | Earnings/debt fields change from null to populated (or vice versa) as cohort sizes change | Common across refreshes. Programs crossing the ~30-completer threshold will gain or lose outcome data. |

---

## Temporal Patterns

### Valid Time
| Pattern | Description | Notes for @temporal-modeler |
|---------|-------------|---------------------------|
| Point-in-time snapshot | This is a single load of "Most Recent Cohorts" data. All 69,947 rows share the same ingested_at timestamp (2026-04-06 02:34:20). There is no time-series dimension within this dataset. | Model as a snapshot table, not a slowly changing dimension (yet). If future refreshes are ingested, consider SCD Type 2 on the institution-program grain to track changes over time. |
| Cohort lag | Earnings data reflects outcomes 1-2 years after degree completion. The "most recent cohorts" label means the measurement window is approximately 2-4 years before the data release date. | Important context for users: earnings data is NOT current — it reflects graduates from approximately 2022-2024 completing, measured in 2024-2025. |
| Measurement windows (1yr vs 2yr) | earn_mdn_hi_1yr and earn_mdn_hi_2yr come from different cohort measurement windows, NOT the same individuals tracked over time. This explains why 44.2% of rows with both values show 2yr < 1yr — it is not an anomaly. | Do NOT model these as a time series. They are parallel measurements from different cohorts. Downstream users must understand this or they will draw incorrect conclusions about earnings trajectories. |

### Amendment/Correction Patterns
| Pattern | Description | Frequency |
|---------|-------------|-----------|
| Annual data refresh | The Department of Education releases updated "Most Recent Cohorts" data annually. Each release replaces the prior year's snapshot entirely. | Annual. The FutureProof pipeline should handle this as a full-table replace, not incremental append. |
| Mid-cycle corrections | The Department occasionally re-releases corrected data within a cycle. | Rare. No mechanism in the current pipeline to detect corrections vs. regular updates. |

---

## Data Quality Considerations

### Known Edge Cases
| Edge Case | Description | Impact | Notes for @dq-rule-writer |
|-----------|-------------|--------|--------------------------|
| md_earn_wne is 100% null | This field is entirely empty across all 69,947 rows. Investigation indicates this metric (median earnings, working and not enrolled) is an INSTITUTION-level field that does not populate in the Field of Study file. The Field of Study file uses earn_mdn_hi_1yr and earn_mdn_hi_2yr instead. | CRITICAL. This field will never have data at this grain. | Do NOT write completeness or range rules for md_earn_wne. Document as structurally empty. Consider dropping in Silver zone transformation. |
| 4-character CIP codes (missing dot) | All CIP codes are stored as "NNNN" (e.g., "5202") instead of the standard "XX.XXXX" format (e.g., "52.02"). This is the source CSV format, not an ingestor bug. | MEDIUM. Blocks CIP-to-SOC crosswalk matching in Silver zone. | Write a format validation rule: cipcode must match `^\d{4}$`. Silver zone must transform to standard format by inserting dot at position 2. |
| Privacy suppression drives 60-64% null rates | Earnings and debt fields are null for 60-64% of rows due to Department of Education privacy rules. Programs with < ~30 completers are suppressed. | Expected. Not a data quality issue — it is by design. | Set null thresholds at 65-70% (with headroom). Alert if null rates exceed these thresholds, as that could indicate a source change. Do NOT treat high null rates as failures. |
| Zero-completion programs | 8,685 rows (12.4%) have ipedscount1=0. These are programs that existed but had no completions in the measurement window. Some (10.7%) still have earnings data from prior-year completers. | Expected. Programs can exist without completions in a given window. | Allow ipedscount1=0 as valid. Consider flagging programs with earnings data but zero completions as noteworthy (not invalid). |
| 2yr earnings < 1yr earnings (44.2%) | Nearly half of rows with both values show 2-year earnings below 1-year earnings. This is NOT an error — different cohort measurement windows, not longitudinal tracking. | Expected. Would confuse naive users. | Do NOT write a rule that flags 2yr < 1yr as an anomaly. Document this pattern prominently for downstream consumers. |
| Multi-campus institutions | 10 institution names map to multiple UNITIDs (e.g., Stevens-Henager College has 6 campus UNITIDs). Each campus is a distinct entity. | Expected. UNITID is the authoritative identifier, not institution name. | Rules should use UNITID for uniqueness, not INSTNM. Name-based dedup would incorrectly merge distinct campuses. |
| Extreme earnings outliers | 14 rows with earnings < $10k (likely grad-school-bound programs), 62 rows > $100k (elite CS/engineering programs). | Valid edge cases at both ends. | Flag but do not reject. Low earnings likely indicate programs where graduates continue to graduate education rather than entering the workforce. |
| Extreme debt outliers | 22 rows with debt > $50k, concentrated at for-profit institutions (Purdue Global, DeVry, Keiser). Max = $57,500. | Valid but notable. For-profit institution debt is a known policy concern. | Flag for review but do not reject. Consider a soft rule that annotates for-profit institution debt patterns. |

### Domain-Specific Validity Rules
| Rule | Description | Source |
|------|-------------|--------|
| CREDLEV must equal 3 | This dataset is filtered to bachelor's degrees only. Any non-3 value indicates an ingestor filter failure. | MVP scope definition + ingestor CREDLEV=3 filter. |
| UNITID must be a 6-digit positive integer | IPEDS IDs are assigned in the 6-digit range (100,000-999,999). | NCES IPEDS specification. |
| CIP code must be a valid 4-digit string | All CIP codes in this dataset are 4 characters. Leading zeros are significant (e.g., "0100" for Agriculture). | Source data format observation (69,947 rows verified). |
| CIP code must exist in CIP 2020 taxonomy | Every observed CIP code should correspond to a valid CIP 2020 classification. | NCES CIP 2020 taxonomy. Referential integrity check for Silver zone. |
| Earnings values must be positive when present | Median earnings cannot be negative or zero. Observed range: $4,880-$161,723. | Economic domain logic — earnings of employed graduates must be positive. |
| Debt values must be positive when present | Median debt cannot be negative or zero. Observed range: $2,750-$57,500. | Financial domain logic — cumulative loan debt must be positive. |
| Completions counts must be non-negative when present | IPEDS completions are counts (0 or higher). | Count semantics — cannot have negative completions. |
| Grain uniqueness: unitid x cipcode x credlev | No two rows should share the same institution-program-credential combination. Current: 0 duplicates. | Data grain definition. Any duplicate is a pipeline bug. |

---

## Regulatory & Compliance Context

### Applicable Regulations
| Regulation | Relevance | Key Requirements | Notes for @bcbs239-auditor |
|-----------|-----------|-----------------|---------------------------|
| FERPA (Family Educational Rights and Privacy Act) | Primary. FERPA is the reason privacy suppression exists in this data. The Department of Education suppresses outcome data for small cohorts to prevent re-identification of individual students. | 1. Individual student records must not be identifiable. 2. Cohort data below minimum thresholds must be suppressed. 3. The Department applies suppression before publication — we receive already-suppressed data. | This data is ALREADY compliant. The null values in earnings/debt fields ARE the FERPA compliance mechanism. No additional FERPA action needed by the pipeline — do not attempt to fill in suppressed values. |
| Higher Education Act (HEA) | Background. The College Scorecard exists under HEA requirements for institutional transparency. The data is a public resource, not restricted. | 1. Data is publicly available — no access restrictions. 2. Published for consumer protection (student decision-making). 3. Institutional participation in Title IV programs is the eligibility criterion. | No access control requirements. This is intentionally public data. Assess for data lineage and provenance tracking only. |
| Gainful Employment (GE) Rules | Related. GE rules use similar earnings and debt metrics to evaluate career-training programs. While this dataset covers all bachelor's programs (not just GE-eligible), the metrics (debt-to-earnings ratios) are conceptually related. | 1. Debt-to-earnings ratios used for program eligibility. 2. Threshold: annual loan payment should not exceed 8% of total earnings or 20% of discretionary income. | Not directly applicable to this pipeline, but the debt and earnings fields in this data could be used to compute GE-like ratios. Consider as a Gold zone data product opportunity. |

### PII Expectations
| PII Type | Expected? | Sensitivity | Notes for @pii-scanner |
|----------|-----------|-------------|----------------------|
| Personal names | No | N/A | This data contains INSTITUTION names, not personal names. No student, faculty, or staff names are present. |
| Student identifiers | No | N/A | All data is at the program-aggregate level. No individual student records, SSNs, or student IDs. |
| Health records | No | N/A | Not applicable to this domain. |
| Financial PII | No | N/A | Earnings and debt figures are MEDIAN AGGREGATES across cohorts, not individual financial records. |
| Location data | No | N/A | Institution names imply locations but no addresses, coordinates, or ZIP codes are present. |
| Contact information | No | N/A | No email addresses, phone numbers, or other contact details. |

**Summary for @pii-scanner:** This dataset contains NO PII. All values are institutional identifiers, program codes, and aggregate statistical measures. Privacy is protected at the source by the Department of Education's suppression rules (FERPA). The pipeline should confirm zero PII findings and skip PII remediation steps. Justification: "governance/domain-context.md PII section confirms no personal data — all fields are institutional/aggregate."

---

## External Data Opportunities
| External Source | What It Adds | Join Key | Notes for @insight-manager |
|----------------|-------------|----------|---------------------------|
| BLS Occupational Outlook Handbook (OOH) | Occupation descriptions, projected job growth rates, typical education requirements, median pay by occupation. Enables the core FutureProof question: "If I study X, what career outcomes can I expect?" | CIP-to-SOC crosswalk (CIP code -> SOC code) | HIGH VALUE. This is the planned second data source per manifest.yaml. Requires Silver zone CIP-to-SOC crosswalk implementation. |
| O*NET | Task-level occupation data, work activities, skills, knowledge, abilities, technology tools. Enables AI exposure analysis and detailed career guidance. | SOC code (via CIP-to-SOC crosswalk from College Scorecard) | HIGH VALUE. Third planned data source per manifest.yaml. Joins to BLS OOH via SOC code. Together with OOH, enables full education-to-career mapping. |
| NCES CIP-SOC Crosswalk Table | Official mapping between CIP education program codes and SOC occupation codes. Published jointly by NCES and BLS. Many-to-many relationship. | cipcode (CIP) -> SOC code | CRITICAL DEPENDENCY. Required for Silver zone integration. Must be ingested as a reference table. Download: https://nces.ed.gov/ipeds/cipcode/ |
| IPEDS Institutional Characteristics | Institutional type (public/private/for-profit), sector, degree-granting status, Carnegie classification, state, region, urbanization. | unitid | MEDIUM VALUE. Enables institution-type segmentation of outcomes (e.g., "Do for-profit institutions have worse debt-to-earnings ratios?"). Could be a Silver zone enrichment. |
| IPEDS 12-Month Enrollment | Total enrollment by institution, race/ethnicity, gender. | unitid | LOW-MEDIUM VALUE. Adds context on institution size and demographics. |
| Census Bureau ACS (American Community Survey) | Regional earnings data, cost of living indices. | Geographic crosswalk (institution state/region) | LOW VALUE for MVP. Would allow normalizing earnings by regional cost of living. Adds complexity. |

---

## Concept Mapping Guidance

### Source Codes to Business Concepts
| Source Code Pattern | Maps To | Confidence | Notes for @cde-tagger |
|--------------------|---------|------------|----------------------|
| cipcode (4-digit) | Academic Program Classification | Exact (after format normalization) | CIP is a well-defined federal taxonomy. Every code maps to exactly one program description. Silver zone must insert dot to get XX.XXXX format before crosswalk matching. |
| credlev (integer 1-8) | Credential Level Classification | Exact | CREDLEV is a simple enumeration. Value 3 = Bachelor's Degree. Only one value present in MVP data. |
| unitid (6-digit integer) | Institution Identity | Exact | UNITID is the authoritative IPEDS identifier. No ambiguity. |
| earn_mdn_hi_1yr, earn_mdn_hi_2yr | Post-Completion Earnings | Domain knowledge | These represent cohort-level median earnings estimates at different time horizons. Map to a "Graduate Earnings" business concept. |
| debt_all_stgp_eval_mdn | Student Debt at Completion | Domain knowledge | Maps to a "Program Debt" or "Graduate Debt" business concept. |
| ipedscount1, ipedscount2 | Program Completions Volume | Domain knowledge | Maps to a "Program Size" or "Completions Count" business concept. The two fields represent different measurement windows. |

### Known Mapping Ambiguities
| Source Code | Candidates | Recommended | Rationale |
|------------|-----------|-------------|-----------|
| md_earn_wne | Median Earnings (institution-level) vs. Median Earnings (program-level) | DROP from Silver zone | This field is 100% null at the field-of-study grain. It populates only in the institution-level College Scorecard file. The program-level earnings are captured by earn_mdn_hi_1yr and earn_mdn_hi_2yr. |
| ipedscount1 vs. ipedscount2 | First-major completions vs. Second-major completions | Retain both with clear labels | They represent different measurement windows. Highly correlated (r=0.984) but not identical. 25,256 rows have count2 > count1. Both are useful for understanding program size. |
| earn_mdn_hi_1yr vs. earn_mdn_hi_2yr | Short-term vs. medium-term earnings | Retain both — they are NOT longitudinal | Users will assume 2yr > 1yr (career progression). This is wrong 44.2% of the time because they are different cohorts. Both must be retained with prominent documentation. |

---

## Canonical Concept Map

This section is the PRIMARY INPUT for the ConceptNormalizer. It defines the target business concepts that raw classification codes should normalize to.

**Status:** PROPOSED (Unconfirmed)
**Source:** Agent-proposed based on domain knowledge of U.S. higher education data and CIP/SOC taxonomy systems.

> **User Said:** (Automated pipeline run — no user interview conducted. See "Unanswered Interview Questions" section below.)
> **Agent Action:** Proposed canonical concept map based on CIP taxonomy structure and College Scorecard methodology. All mappings are PROPOSED and require confirmation before Gold zone implementation.

### Target Business Concepts
| # | Business Concept | Plain English Name | Expected Source Codes | Category | Priority |
|---|-----------------|-------------------|----------------------|----------|-----------|
| 1 | Academic Program | The field of study (major) a student pursues | CIP codes (390 distinct in this dataset) | Program Classification | CORE |
| 2 | Program Family | The broad discipline area (2-digit CIP family) | CIP 2-digit prefix (e.g., 52=Business, 51=Health) | Program Classification | CORE |
| 3 | Institution | The postsecondary school offering the program | UNITID (2,559 distinct) | Entity | CORE |
| 4 | Credential Level | The type of degree or certificate | CREDLEV code (only 3 in MVP) | Program Classification | CORE |
| 5 | Graduate Earnings (1yr) | Median earnings of graduates 1 year after completion | earn_mdn_hi_1yr | Outcome Metric | CORE |
| 6 | Graduate Earnings (2yr) | Median earnings of graduates 2 years after completion | earn_mdn_hi_2yr | Outcome Metric | CORE |
| 7 | Program Debt | Median student loan debt at program completion | debt_all_stgp_eval_mdn | Outcome Metric | CORE |
| 8 | Program Size | Number of students completing the program | ipedscount1, ipedscount2 | Volume Metric | CORE |
| 9 | Debt-to-Earnings Ratio | Computed: median debt / median earnings. Key metric for program value assessment. | Derived from debt_all_stgp_eval_mdn / earn_mdn_hi_1yr (or 2yr) | Derived Metric | EXTENDED |
| 10 | Occupation | The career a graduate enters (via CIP-to-SOC crosswalk) | SOC codes (from crosswalk, not in raw data) | Career Outcome | EXTENDED |
| 11 | Institution Type | Public, private nonprofit, or for-profit classification | Not in raw data — requires IPEDS Institutional Characteristics join | Institution Classification | OPTIONAL |
| 12 | Earnings Availability | Whether outcome data is available or privacy-suppressed | Derived: non-null status of earnings fields | Data Quality Indicator | OPTIONAL |

### CIP-to-SOC Crosswalk (Silver Zone Implementation)

The most critical concept mapping for this domain is the **CIP-to-SOC crosswalk**, which links academic programs (CIP codes) to occupations (SOC codes). This is a many-to-many relationship: one CIP code can lead to multiple occupations, and one occupation can be reached from multiple programs.

**Implementation requirements:**
1. **CIP code format normalization:** Transform 4-digit codes to XX.XXXX format by inserting a dot at position 2 (e.g., "5202" -> "52.02"). This MUST happen before crosswalk matching.
2. **Crosswalk table ingestion:** Download the official NCES CIP-SOC crosswalk table and ingest as a reference dimension in the Silver zone.
3. **Join strategy:** Left join from College Scorecard programs to crosswalk to preserve programs that have no SOC mapping (some academic programs, like Liberal Arts, do not map cleanly to specific occupations).
4. **Confidence scoring:** Exact CIP-to-SOC matches get confidence 1.0. Matches via CIP family (2-digit prefix only) get lower confidence (0.7).

### Concept-to-Code Mapping Rules

```json
{
  "domain": "higher_education_outcomes",
  "taxonomy": "CIP_2020",
  "tiers": {
    "exact": {
      "description": "4-digit CIP code maps to specific program description",
      "confidence": 1.0,
      "example": "5202 -> Business Administration and Management"
    },
    "prefix": {
      "description": "2-digit CIP family maps to broad discipline area",
      "confidence": 0.7,
      "example": "52 -> Business, Management, Marketing, and Related"
    },
    "pattern": {
      "description": "Not applicable — CIP codes are not pattern-based",
      "confidence": null,
      "example": null
    },
    "heuristic": {
      "description": "CIP-to-SOC crosswalk mapping (many-to-many with varying specificity)",
      "confidence": 0.6,
      "example": "CIP 5202 -> SOC 11-1021 (General and Operations Managers) via crosswalk"
    }
  }
}
```

### Collision Resolution Rules

When multiple source codes or metrics map to the same business concept for the same entity-period, apply these rules:

| Collision Scenario | Resolution | Rationale |
|-------------------|------------|-----------|
| Multiple CIP codes for the same institution | No collision — each is a distinct program (separate grain rows) | The grain is unitid x cipcode x credlev. Each row is unique by definition. |
| ipedscount1 vs. ipedscount2 for program size | Prefer ipedscount1 as the primary completions measure; retain ipedscount2 as supplementary | ipedscount1 represents first-major completions, which is the more commonly cited figure. |
| earn_mdn_hi_1yr vs. earn_mdn_hi_2yr for earnings | Prefer earn_mdn_hi_2yr (more data: 27,681 non-null vs. 25,196) but retain both | 2yr has lower null rate and slightly longer post-completion window. Neither is definitively "better." |
| Multiple SOC codes for one CIP code (via crosswalk) | Retain all mappings with crosswalk-sourced confidence scores | The CIP-to-SOC relationship is genuinely many-to-many. Do not force a single occupation per program. |

---

## Unanswered Interview Questions (Automated Pipeline Run)

This section documents EDA-informed interview questions that would normally be asked of the user via the domain interview protocol. Since this is an automated pipeline run, all questions are flagged as unanswered. **Each unanswered question creates a mandatory DQ rule requirement** — @dq-rule-writer must write a defensive rule to cover the uncertainty.

### Question 1: CIP Code Format Normalization
**Question:** "The EDA found all 69,947 CIP codes are in 4-digit format (e.g., '5202') instead of the standard XX.XXXX format (e.g., '52.02'). Is this expected? Should we normalize to XX.XXXX in the Silver zone?"
**Status:** UNANSWERED — requires follow-up
**Agent Assumption:** Yes, normalize to XX.XXXX in Silver zone. The 4-digit format is the source CSV's storage convention. The dot must be inserted for CIP-to-SOC crosswalk matching and for conformance with the NCES CIP standard.
**Mandatory DQ Rule:** Validate that all raw CIP codes match `^\d{4}$` pattern. Alert if any codes deviate from this format (could indicate source change).

### Question 2: md_earn_wne Field Disposition
**Question:** "md_earn_wne (Median Earnings, Working and Not Enrolled) is 100% null across all 69,947 rows. Our investigation suggests this metric only populates in the institution-level College Scorecard file, not the field-of-study file. Should we (a) drop this column in Silver, (b) keep it as a placeholder for future data, or (c) investigate the source CSV headers?"
**Status:** UNANSWERED — requires follow-up
**Agent Assumption:** Drop this column in the Silver zone transformation. The field-of-study file uses earn_mdn_hi_1yr and earn_mdn_hi_2yr as its earnings metrics instead.
**Mandatory DQ Rule:** Do NOT write completeness rules for md_earn_wne. Write a sentinel rule that alerts if this field ever becomes non-null (would indicate a source schema change requiring pipeline review).

### Question 3: Minimum Cohort Size for Meaningful Earnings Data
**Question:** "The EDA shows that programs with ipedscount1 < 30 have under 11% earnings availability due to privacy suppression. What's the minimum cohort size you consider meaningful for analysis? Should we flag or exclude programs below a certain threshold in the Gold zone?"
**Status:** UNANSWERED — requires follow-up
**Agent Assumption:** Use 30 as the minimum cohort threshold for "reliable" earnings data, based on the observed privacy suppression pattern. Programs below 30 completers are retained but flagged as "low-confidence outcome data."
**Mandatory DQ Rule:** Write a rule that annotates rows where ipedscount1 < 30 as having "privacy-suppressed or low-confidence outcomes." This is informational, not a rejection.

### Question 4: Institutional Completeness Check
**Question:** "Are there specific institutions that should ALWAYS be present in this dataset as a completeness check? For example, should we verify that all Ivy League schools, all state flagship universities, or all institutions above a certain size threshold are present?"
**Status:** UNANSWERED — requires follow-up
**Agent Assumption:** No specific institution list is mandated. Use row count and distinct institution count as proxy completeness checks (current: 2,559 institutions, threshold 2,200-3,000).
**Mandatory DQ Rule:** Write a rule checking distinct institution count (unitid) is between 2,200 and 3,000. This provides a coarse completeness check without requiring a specific institution list.

### Question 5: Earnings Temporal Relationship
**Question:** "44.2% of rows where both earn_mdn_hi_1yr and earn_mdn_hi_2yr are present show 2-year earnings BELOW 1-year earnings. The EDA concludes this is expected because they come from different cohort measurement windows, not longitudinal tracking. Do you agree with this interpretation, or should we investigate further?"
**Status:** UNANSWERED — requires follow-up
**Agent Assumption:** The EDA interpretation is correct. These are "high estimate" medians from different cohort windows. The 2yr < 1yr pattern is NOT an anomaly and should NOT be flagged as a DQ issue.
**Mandatory DQ Rule:** Do NOT write a rule that rejects or flags 2yr < 1yr. Write a documentation-only rule that records the percentage of rows where 2yr < 1yr for monitoring across data refreshes (alert if this percentage changes dramatically, e.g., outside 35-55% range).

### Question 6: Data Refresh Cadence and Handling
**Question:** "The College Scorecard data is released annually. When we ingest a new release, should we (a) replace the entire table, (b) append as a new snapshot with a version/release column, or (c) implement SCD Type 2 to track changes? This affects temporal modeling."
**Status:** UNANSWERED — requires follow-up
**Agent Assumption:** Full table replace for MVP (simplest approach). The "Most Recent Cohorts" file is designed to be a complete replacement. Consider SCD Type 2 in a future iteration if tracking year-over-year changes becomes a requirement.
**Mandatory DQ Rule:** Write a freshness rule that checks load_date is within 400 days of the current date (annual release + buffer). Alert if data is stale.

### Question 7: Target User Questions for MCP Server
**Question:** "What are the primary questions you want the MCP server to answer? For example: 'What is the median earnings for CS graduates from Stanford?' or 'Which programs have the best debt-to-earnings ratios?' or 'What are the highest-paying bachelor's degrees nationally?'"
**Status:** UNANSWERED — requires follow-up
**Agent Assumption:** Based on the FutureProof project description ("AI career guidance"), the primary user questions are likely:
1. "What are the earnings outcomes for [program] at [institution]?"
2. "Which programs at [institution] have the best earnings?"
3. "What is the average debt for [program] graduates?"
4. "Which institutions produce the highest-earning [program] graduates?"
5. "What is the debt-to-earnings ratio for [program]?"
**Mandatory DQ Rule:** No specific rule — but @mcp-engineer should design the MCP server to handle these question patterns.

---

## Assumptions (User-Deferred)

All assumptions below were made by @domain-context in the absence of user input. Each carries MEDIUM confidence unless otherwise noted. The @principal-data-architect will review these at the bronze-to-silver zone transition.

| # | Assumption | Basis | Confidence | Risk if Wrong |
|---|-----------|-------|------------|---------------|
| 1 | md_earn_wne should be dropped in Silver zone | 100% null in field-of-study file; institution-level metric | HIGH | Low — field has no data. Worst case: we add it back if source changes. |
| 2 | CIP codes should be normalized to XX.XXXX in Silver | Required for CIP-to-SOC crosswalk matching | HIGH | Low — this is the standard format. |
| 3 | Privacy suppression threshold is ~30 completers | Observed 88.7% availability above 30 vs. <11% below 10 | MEDIUM | Medium — the actual threshold may differ. DQ rules use flexible thresholds. |
| 4 | Full table replace strategy for annual refreshes | "Most Recent Cohorts" is a complete snapshot | MEDIUM | Medium — may lose historical tracking. Revisit if year-over-year analysis is needed. |
| 5 | 2yr < 1yr earnings is not an anomaly | Different cohort measurement windows | HIGH | Low — well-documented in College Scorecard methodology. |
| 6 | No PII exists in this dataset | All fields are institutional/aggregate | HIGH | Very low — FERPA suppression already applied by Department of Education. |
| 7 | Canonical concept list covers the core use case | Based on FutureProof project description | MEDIUM | Medium — user may want different or additional concepts. Concept map is PROPOSED. |

---

## AI-Ready Considerations
| Consideration | Recommendation | Notes for @mcp-engineer |
|--------------|---------------|------------------------|
| Primary user questions | "What are the earnings/debt outcomes for [program] at [institution]?" "Which programs have the best outcomes?" "Compare [program A] vs. [program B]." | Support program lookup by name (cipdesc) and code (cipcode), institution lookup by name (instnm) and ID (unitid). |
| Context an LLM needs | The LLM must know that: (1) null earnings = privacy suppression, not missing data; (2) 1yr and 2yr earnings are different cohorts, not longitudinal; (3) low earnings may mean grad school, not bad outcomes; (4) for-profit institutions have higher debt patterns. | Include this as grounding context in every MCP response. Without it, the LLM will misinterpret nulls and earnings patterns. |
| Disambiguation | Institution names are not unique (10 names map to multiple campuses). CIP descriptions are more user-friendly than codes. | Always display institution name + state/campus identifier (may need IPEDS enrichment). Always display program description alongside CIP code. |
| Privacy-suppressed programs | 52.7% of rows have ALL outcome fields null. These programs exist but have no reportable outcomes. | Decide whether to include these in MCP responses. Option A: exclude and note "outcome data not available for this program." Option B: include with explicit "data suppressed for privacy" label. Recommend Option B for transparency. |
| Debt-to-earnings ratio | A derived metric (debt / earnings) is the single most actionable number for students deciding between programs. | Pre-compute in Gold zone. Handle nulls gracefully — if either component is null, the ratio is null. |
| Comparison queries | Users will want to compare programs across institutions or compare institutions for the same program. | Index by both cipcode and unitid for fast lookups. Support ranked lists ("top 10 programs by earnings"). |
| Data freshness disclosure | Earnings data reflects graduates from ~2-4 years ago. Users should be told this. | Include data vintage in MCP metadata. "This data reflects outcomes for students who completed their degrees approximately 2-4 years ago." |

---

## Confidence Notes

**High confidence:**
- Domain identification (Higher Education Outcomes / College Scorecard) — unambiguous from source URL, field names, and data patterns
- FERPA applicability and privacy suppression explanation
- CIP code format issue (4-digit vs. XX.XXXX) — 100% consistent, well-understood
- md_earn_wne being an institution-level field — consistent with College Scorecard documentation
- No PII in this dataset — all aggregate/institutional data
- Grain definition (unitid x cipcode x credlev) — confirmed by zero duplicates

**Medium confidence:**
- Privacy suppression threshold (~30 completers) — inferred from data patterns, not from official documentation of the exact threshold
- Canonical concept map — proposed by agent, not confirmed by user
- MCP question patterns — assumed from project description, not validated with users
- ipedscount1 vs. ipedscount2 measurement window distinction — known to be different but exact definitions not verified against data dictionary

**Low confidence / Needs human validation:**
- Data refresh handling strategy (full replace vs. SCD) — depends on future requirements not yet specified
- Minimum cohort size for "meaningful" analysis — a judgment call that depends on use case
- Which institutions should always be present — no reference list provided
- Whether md_earn_wne should be completely dropped vs. retained as a placeholder

---
---

# Domain Context: BLS Occupational Outlook Handbook (Employment Projections)
**Date:** 2026-04-07
**Agent:** @domain-context
**Based On:** governance/eda/raw-bls-ooh-eda.md (2026-04-07)
**Data Sources:** bls_ooh (Bureau of Labor Statistics, Employment Projections program — Table 1.7)
**Confidence:** High
**Cross-Reference:** This is the SECOND of three FutureProof data sources. See College Scorecard section above for the first. SOC codes in this dataset bridge to O*NET (future, direct SOC join) and College Scorecard (via CIP-to-SOC crosswalk in Silver zone).

---

## Domain Identification
**Domain:** U.S. Labor Market — Occupation-Level Employment Projections
**Sub-domain:** BLS Employment Projections (Occupational Outlook Handbook structured data)
**Description:** This data captures the Bureau of Labor Statistics' occupation-level employment projections, wages, and education/training requirements for approximately 832 detailed occupations classified under the SOC 2018 taxonomy. Each row represents a single detailed occupation with its current employment, 10-year projected employment, growth rate, annual job openings, median wage, and entry-level education/experience/training requirements. The data is the structured backbone of the Occupational Outlook Handbook and is released on a biennial projection cycle (current cycle: 2023-2033). In the FutureProof pipeline, this data answers the "what career outcomes can I expect?" side of the equation by providing occupation-level salary, growth, and requirements that join to education programs via the CIP-to-SOC crosswalk.

---

## Domain Vocabulary

### Core Terms
| Term | Definition | Source | Notes for @data-steward |
|------|-----------|--------|------------------------|
| SOC Code | Standard Occupational Classification code in XX-XXXX format (2-digit major group + 4-digit detail). The primary taxonomy for classifying U.S. occupations across all federal statistical agencies. | BLS/OMB SOC 2018 (external standard) | Auto-approve. Reference: https://www.bls.gov/soc/2018/ |
| SOC 2018 | The current version of the Standard Occupational Classification system, adopted in 2018. Contains 867 detailed occupations organized into 23 major groups. SOC 2028 is anticipated as the next revision. | OMB (external standard) | Auto-approve. Flag SOC 2028 migration as a future change event. |
| Summary SOC Code | SOC codes ending in "0000" (e.g., 11-0000 "Management occupations") that represent major group aggregates, not individual occupations. These are filtered out during ingestion and must never appear in the processed dataset. | BLS SOC structure (external standard) | Auto-approve. The ingestor filters these; ~22 expected in raw XLSX. |
| Employment (in thousands) | The raw BLS data reports employment figures "in thousands" (e.g., 1795.5 means 1,795,500 workers). The ingestor multiplies by 1,000 and rounds to long integer. | BLS Employment Projections methodology | Propose — the conversion is project-specific, though the source convention is BLS standard. |
| Median Annual Wage | The BLS-reported median wage for an occupation. Half of workers in the occupation earn more, half earn less. Subject to top-coding at $239,200. | BLS Occupational Employment and Wage Statistics | Auto-approve. Standard BLS metric. |
| Top-Coded Wage / Wage Cap | BLS top-codes median wages at $239,200 for occupations where the true median exceeds the BLS confidentiality threshold. The raw data shows these as ">=239,200". Approximately 3-5% of detailed occupations are affected. | BLS data confidentiality rules | Propose — the specific threshold ($239,200) is BLS policy, but the "top-coded" concept needs explicit glossary entry. |
| N/A Wage | Occupations where wage data is not available or not applicable (e.g., elected officials whose compensation varies by jurisdiction). Raw value is "N/A", converted to null. | BLS data conventions | Propose — small number of occupations (~20-30 of ~832). |
| Projection Cycle | BLS Employment Projections are released biennially, each covering a 10-year horizon. The current cycle is 2023-2033. Each release is a complete replacement of the prior cycle. | BLS Employment Projections program | Auto-approve. Reference: https://www.bls.gov/emp/ |
| Annual Average Openings | The projected annual average number of job openings, combining growth openings (new positions from expanding employment) and replacement openings (filling positions vacated by workers leaving the occupation). Always positive even for declining occupations. | BLS Employment Projections methodology | Auto-approve. Critical nuance: declining occupations still have openings due to replacement needs. |
| Education Code | BLS integer classification (1-8) for typical entry-level education requirement. | BLS Employment Projections (project-specific encoding) | Propose — the classification is BLS-defined but the integer encoding is specific to the EP data tables. |
| Work Experience Code | BLS integer classification (1-3) for required related-occupation experience. | BLS Employment Projections (project-specific encoding) | Propose — same reasoning as education_code. |
| Training Code | BLS integer classification (1-6) for typical on-the-job training requirement. | BLS Employment Projections (project-specific encoding) | Propose — same reasoning as education_code. |

### Taxonomy/Classification Systems
| System | Description | Authority | Coverage in Data |
|--------|-------------|-----------|-----------------|
| SOC 2018 (Standard Occupational Classification) | The primary U.S. federal taxonomy for classifying occupations. 23 major groups, 98 minor groups, 459 broad occupations, 867 detailed occupations. Used by BLS, Census Bureau, O*NET, and other federal agencies. | Office of Management and Budget (OMB) | 100% — every row is keyed by SOC code. ~832 detailed occupations expected (some SOC codes have no EP data). |
| BLS Education Level Classification | Integer codes 1-8 mapping to entry-level education requirements: 1=Doctoral or professional degree, 2=Master's degree, 3=Bachelor's degree, 4=Associate's degree, 5=Postsecondary nondegree award, 6=Some college no degree, 7=High school diploma or equivalent, 8=No formal educational credential. Codes derived from string labels in the ingestor via `_EDUCATION_CODE_MAP`. | Bureau of Labor Statistics | 100% — all 832 occupations have education codes. All 8 levels confirmed in full dataset. |
| BLS Work Experience Classification | Integer codes 1-3: 1=5 years or more, 2=Less than 5 years, 3=None. Codes derived from string labels via `_WORK_EXPERIENCE_CODE_MAP`. | Bureau of Labor Statistics | 100% — all 832 occupations have work experience codes. All 3 levels confirmed. |
| BLS Training Classification | Integer codes 1-6: 1=Internship/residency, 2=Apprenticeship, 3=Long-term OJT, 4=Moderate-term OJT, 5=Short-term OJT, 6=None. Codes derived from string labels via `_TRAINING_CODE_MAP`. | Bureau of Labor Statistics | 100% — all 832 occupations have training codes. All 6 levels confirmed in full dataset. |

### Enumerated Values with Business Meaning
| Field | Values | Meaning |
|-------|--------|---------|
| education_code | 1-8 | 1=Doctoral or professional degree, 2=Master's degree, 3=Bachelor's degree, 4=Associate's degree, 5=Postsecondary nondegree award, 6=Some college no degree, 7=High school diploma or equivalent, 8=No formal educational credential. VERIFIED against full 832-row dataset (2026-04-07). |
| work_experience_code | 1-3 | 1=5 years or more, 2=Less than 5 years, 3=None. VERIFIED against full dataset. |
| training_code | 1-6 | 1=Internship/residency, 2=Apprenticeship, 3=Long-term OJT, 4=Moderate-term OJT, 5=Short-term OJT, 6=None. VERIFIED against full dataset. |
| median_wage_capped | true/false | true = original BLS value was ">=239,200" (top-coded); false = wage is actual median or null |
| source_method | "xlsx_download" | Metadata: data was fetched via XLSX download from BLS EP data tables |

---

## Entity Types

### Primary Entities
| Entity Type | Identifier Field(s) | Example | Notes for @entity-resolver |
|-------------|---------------------|---------|---------------------------|
| Occupation | soc_code | 15-1252 (Software Developers) | ID-based resolution. SOC code is the authoritative identifier. 1:1 mapping with occupation_title in source data. Direct join key to O*NET (same SOC taxonomy). Bridge to College Scorecard via CIP-to-SOC crosswalk. |
| SOC Major Group | soc_code prefix (first 2 digits) | 15 (Computer and Mathematical Occupations) | Derived entity — not a separate row in the data, but the 2-digit SOC prefix groups related occupations. Useful for aggregation and category-level analysis. 23 major groups total. |

### Entity Lifecycle Events
| Event Type | How It Appears in Data | Frequency |
|-----------|----------------------|-----------|
| SOC taxonomy revision | SOC codes are reassigned or restructured (e.g., SOC 2018 replaced SOC 2010). Old codes may split, merge, or be renumbered. | Rare — ~10-year cycle. SOC 2028 anticipated. BLS publishes a crosswalk between old and new codes. |
| Occupation addition | New SOC codes appear in a new projection cycle (e.g., new technology-driven occupations). | Uncommon. Happens with each SOC revision and occasionally between revisions. |
| Occupation removal | SOC codes disappear from projections (occupation merged, obsoleted, or reclassified). | Uncommon. Same triggers as additions. |
| Projection cycle change | All projection data updates simultaneously when BLS releases a new 10-year projection cycle (e.g., 2023-2033 replaces 2022-2032). | Biennial. Complete replacement of all projection values. |

---

## Temporal Patterns

### Valid Time
| Pattern | Description | Notes for @temporal-modeler |
|---------|-------------|---------------------------|
| Biennial projection snapshot | BLS Employment Projections are released every 2 years, each covering a 10-year horizon. The current cycle is 2023-2033. Each release is a complete replacement, not an incremental update. | Model as a snapshot table. If multiple projection cycles are retained, add a projection_cycle dimension (e.g., "2023-2033"). For MVP, a single snapshot is sufficient. |
| Base year vs. projected year | employment_current is the base year (2023), employment_projected is the target year (2033). The time horizon is always 10 years. | Column names in the raw XLSX change with each cycle (e.g., "Employment, 2023" becomes "Employment, 2025"). The ingestor uses fuzzy header matching to handle this. |
| Wage data currency | Median wage data reflects the most recent BLS Occupational Employment and Wage Statistics survey, which may lag the projection base year by 1-2 years. | Wage data is not projected — it is the latest available point estimate. Do not treat it as a 10-year projection. |

### Amendment/Correction Patterns
| Pattern | Description | Frequency |
|---------|-------------|-----------|
| Biennial full replacement | Each new projection cycle replaces all prior data. There is no amendment mechanism — the entire dataset is recomputed. | Every 2 years. Pipeline should handle as full table replace. |
| Mid-cycle corrections | BLS occasionally corrects individual values between projection cycles. | Very rare. No systematic mechanism to detect corrections vs. regular updates. |
| XLSX header changes | Column headers in the source XLSX change with each projection cycle to reflect new base/target years. | Every 2 years. The ingestor's fuzzy header matching mitigates this. |

---

## Data Quality Considerations

### Known Edge Cases
| Edge Case | Description | Impact | Notes for @dq-rule-writer |
|-----------|-------------|--------|--------------------------|
| Top-coded wages ($239,200) | BLS top-codes median wages at $239,200 for high-earning occupations (e.g., Surgeons, Anesthesiologists, CEOs). The true median is higher but not disclosed. | Expected 3-5% of occupations (~25-40 rows). | Enforce consistency rule: median_wage_capped=true IFF median_annual_wage=239200.0. This is a HARD rejection rule — any inconsistency is an ingestor bug. |
| N/A wage occupations | Some occupations have "N/A" wages — typically elected officials (Legislators), self-employed-dominated occupations, or occupations with non-standard compensation. Converted to null. | Expected ~20-30 of ~832 occupations (~2-4%). | Set median_annual_wage null threshold at 5%. When wage is null, median_wage_capped must be false. |
| Negative employment change | Declining occupations have negative employment_change and employment_change_pct values. The 10-row sample has only positive values (sample bias). | Expected 15-40% of occupations in the full dataset. | MUST allow negative values for employment_change and employment_change_pct. Do NOT set a minimum of 0. Expected range: -500,000 to +1,000,000 (change) and -50% to +50% (pct). |
| Positive annual openings for declining occupations | Even occupations with negative employment growth have positive annual openings because of replacement needs (retirements, workers leaving the occupation). | Universal — openings_annual_avg is ALWAYS positive. | openings_annual_avg minimum must be > 0 (strictly positive). A zero or negative value is a data error. |
| Summary rows in source XLSX | Raw XLSX contains ~22 summary rows with SOC codes ending in "0000" (e.g., 11-0000 "Management occupations"). These have "See summary" in education/training fields and code values of 0. | Filtered by ingestor. Should never appear in processed data. | Write a post-ingestor rule: no soc_code should match `\d{2}-0000$`. If any appear, the ingestor's filter is broken. |
| Employment "in thousands" conversion rounding | Raw values like 1795.5 (thousands) become 1,795,500. The multiplication by 1000 + rounding to long can introduce +/- 500 rounding artifacts. | Negligible for analysis. | Employment change consistency rule should allow +/- 1000 tolerance: abs(employment_projected - employment_current - employment_change) <= 1000. |
| Very small occupations | Some detailed occupations have very small employment (e.g., Surgeons at 36,600 in sample). Legitimate but far from the median. | Not an error. Employment naturally spans orders of magnitude. | Set employment_current minimum at 1 (theoretical floor). Do not flag small values as outliers. |

### Domain-Specific Validity Rules
| Rule | Description | Source |
|------|-------------|--------|
| SOC code format: XX-XXXX | Every soc_code must match `^\d{2}-\d{4}$`. No trailing decimals, no spaces, no missing hyphens. | SOC 2018 standard. Verified: 10/10 sample values match. |
| No summary SOC codes in output | soc_code must NOT match `^\d{2}-0000$`. Summary rows must be filtered by the ingestor. | BLS EP data structure — summary rows are aggregates, not individual occupations. |
| SOC code uniqueness (grain) | No duplicate soc_code values. Each detailed occupation appears exactly once. | Data grain definition. Any duplicate is an ingestor bug. |
| Wage cap consistency | If median_wage_capped=true, then median_annual_wage must equal 239200.0. If median_annual_wage is null, median_wage_capped must be false. | BLS wage top-coding rules + ingestor contract. |
| Employment change consistency | employment_projected - employment_current should equal employment_change within +/- 1000 (rounding tolerance from thousands conversion). | Derived field relationship. Verified in all 10 sample rows. |
| Education code range 1-8 | education_code must be between 1 and 8 inclusive. Values outside this range indicate data corruption or source schema change. | BLS education level classification (8 defined levels). |
| Work experience code range 1-3 | work_experience_code must be between 1 and 3 inclusive. | BLS work experience classification (3 defined levels). |
| Training code range 1-6 | training_code must be between 1 and 6 inclusive. | BLS training classification (6 defined levels). |
| Code-to-text determinism | Same education_code always maps to same education_typical (and same for work_experience and training pairs). | Verified in sample — 100% consistent. Any inconsistency is a data or ingestor bug. |
| Employment values must be positive | employment_current, employment_projected, and openings_annual_avg must all be > 0 for detailed occupations. | Economic domain logic — a detailed occupation with zero or negative employment would not be in the projections. |
| Wage range $20,000-$239,200 | When non-null, median_annual_wage should be between $20,000 (approximate federal minimum wage full-time) and $239,200 (BLS cap). | Economic floor + BLS ceiling. |

---

## Regulatory & Compliance Context

### Applicable Regulations
| Regulation | Relevance | Key Requirements | Notes for @bcbs239-auditor |
|-----------|-----------|-----------------|---------------------------|
| BLS Data Use Terms | Primary. BLS data is public domain (produced by a federal statistical agency) but usage is subject to BLS terms of service. | 1. Data is freely available for public use. 2. Attribution to BLS is expected. 3. BLS blocks automated scraping (403 on bot User-Agents) — manual download or browser-like headers required. | No access restrictions on the data itself. Assess for data lineage and provenance tracking. Source attribution should appear in data products. |
| OMB Statistical Policy Directives | Background. The SOC taxonomy is maintained under OMB authority. SOC revisions follow OMB review cycles. | 1. SOC taxonomy changes must follow OMB process. 2. Federal agencies must adopt new SOC versions within implementation timelines. | Relevant for SOC 2028 migration planning. No immediate compliance action required. |

### PII Expectations
| PII Type | Expected? | Sensitivity | Notes for @pii-scanner |
|----------|-----------|-------------|----------------------|
| Personal names | No | N/A | This data contains OCCUPATION titles, not personal names. No individual worker information. |
| Worker identifiers | No | N/A | All data is at the occupation-aggregate level. No individual worker records, SSNs, or employee IDs. |
| Health records | No | N/A | Not applicable. |
| Financial PII | No | N/A | Wages are OCCUPATION-LEVEL MEDIANS, not individual compensation. No personal financial data. |
| Location data | No | N/A | No geographic breakdown in this dataset. BLS publishes separate state/metro-level data, but this table is national-level only. |

**Summary for @pii-scanner:** This dataset contains NO PII. All values are occupation-level aggregates published by a federal statistical agency. The pipeline should confirm zero PII findings. Justification: "governance/domain-context.md BLS OOH PII section confirms no personal data — all fields are occupation-level aggregates."

---

## External Data Opportunities (from BLS OOH perspective)
| External Source | What It Adds | Join Key | Notes for @insight-manager |
|----------------|-------------|----------|---------------------------|
| College Scorecard (ALREADY INGESTED) | Program-level earnings and debt by institution/major. Combined with BLS OOH, answers: "What does studying X at school Y lead to in terms of career prospects?" | CIP-to-SOC crosswalk (CIP code -> SOC code) | CRITICAL. This is the core FutureProof integration. Requires Silver zone crosswalk implementation. |
| O*NET (PLANNED) | Task-level occupation data, skills, knowledge, abilities, work activities, technology tools. Enables AI exposure analysis: "How automatable are the tasks in this occupation?" | soc_code (direct join — O*NET uses the same SOC taxonomy) | HIGH VALUE. Third planned data source. Direct SOC join — no crosswalk needed. Together with BLS OOH, provides comprehensive occupation profiles. |
| CIP-to-SOC Crosswalk Table | Official many-to-many mapping between education programs (CIP) and occupations (SOC). Maintained jointly by NCES and BLS. | cipcode (from College Scorecard) -> soc_code (from BLS OOH) | CRITICAL DEPENDENCY. Must be ingested as a reference dimension in Silver zone. Download: https://nces.ed.gov/ipeds/cipcode/ |
| BLS State/Metro Employment Data | Employment and wage data broken down by state and metropolitan area. Enables geographic analysis of career outcomes. | soc_code | MEDIUM VALUE. Adds geographic dimension. Enables questions like "What do Software Developers earn in San Francisco vs. Austin?" |
| BLS Industry-Occupation Matrix | Employment by industry for each occupation. Shows which industries employ each occupation. | soc_code | LOW-MEDIUM VALUE. Adds industry diversification context (e.g., "Software Developers work in tech, finance, healthcare..."). |

---

## Concept Mapping Guidance

### Source Codes to Business Concepts
| Source Code Pattern | Maps To | Confidence | Notes for @cde-tagger |
|--------------------|---------|------------|----------------------|
| soc_code (XX-XXXX) | Occupation Identity | Exact | SOC is the authoritative federal occupation taxonomy. Direct join key to O*NET. Bridge to CIP via crosswalk. |
| soc_code prefix (XX) | SOC Major Group (broad occupation category) | Exact (prefix) | 23 major groups (e.g., 11=Management, 15=Computer, 29=Healthcare Practitioners). Useful for category-level analysis. |
| education_code (1-8) | Entry-Level Education Requirement | Exact | BLS-defined classification with fixed text equivalents. Ordinal — higher code = higher education level. |
| work_experience_code (1-3) | Work Experience Requirement | Exact | BLS-defined. Ordinal — higher code = more experience required. |
| training_code (1-6) | On-the-Job Training Requirement | Exact | BLS-defined. Codes 2-4 are OJT of increasing duration; 5=Apprenticeship; 6=Internship/residency. |
| median_annual_wage | Occupation Median Salary | Exact (with caveats) | Subject to top-coding ($239,200) and N/A. Must be interpreted alongside median_wage_capped flag. |
| employment_change_pct | Occupation Growth Rate | Exact | 10-year projected percentage change in employment. Primary indicator of occupation demand trajectory. |
| openings_annual_avg | Annual Job Opportunity Volume | Exact | Combines growth + replacement openings. Better indicator of actual job availability than growth rate alone (declining occupations still have openings). |

### Known Mapping Ambiguities
| Source Code | Candidates | Recommended | Rationale |
|------------|-----------|-------------|-----------|
| median_annual_wage (when capped) | True median salary vs. reported $239,200 | Retain $239,200 with capped flag | True median is not available. Users must be told "at least $239,200." Gold zone should expose the capped flag prominently. |
| employment_change vs. openings_annual_avg | "Job growth" (could mean either) | Use openings_annual_avg as the primary "opportunity" metric | employment_change can be negative; openings are always positive and include replacement demand. For career guidance, openings is the more actionable metric. |
| education_typical vs. education_code | Which to carry to Silver/Gold | Carry both; use code for computation, text for display | Code enables sorting/filtering (ordinal); text enables human-readable presentation. |

---

## Canonical Concept Map (BLS OOH)

This section defines the target business concepts for BLS OOH data that feed into the Silver and Gold zones. It complements the College Scorecard concept map above — together they form the full FutureProof concept model.

**Status:** PROPOSED (Unconfirmed)
**Source:** Agent-proposed based on domain knowledge of BLS Employment Projections and SOC taxonomy, informed by EDA findings and FutureProof project goals.

> **User Said:** User provided directed context: "BLS Employment Projections data -- ~832 detailed occupations with SOC codes, employment projections, wages, education requirements. The CIP-to-SOC crosswalk bridges College Scorecard programs to BLS occupations in Silver zone." (session 2026-04-07)
> **Agent Action:** Proposed canonical concepts based on BLS EP data structure and FutureProof career-guidance use case.

### Target Business Concepts
| # | Business Concept | Plain English Name | Expected Source Codes | Category | Priority |
|---|-----------------|-------------------|----------------------|----------|-----------|
| 1 | Occupation | A specific job or career identified by SOC code | soc_code + occupation_title (~832 distinct) | Entity | CORE |
| 2 | Occupation Category | Broad occupation group (SOC major group) | soc_code 2-digit prefix (23 major groups) | Entity | CORE |
| 3 | Occupation Median Salary | Median annual pay for an occupation | median_annual_wage + median_wage_capped | Compensation Metric | CORE |
| 4 | Occupation Growth Rate | 10-year projected employment change percentage | employment_change_pct | Demand Metric | CORE |
| 5 | Annual Job Openings | Projected annual average openings (growth + replacement) | openings_annual_avg | Demand Metric | CORE |
| 6 | Entry Education Requirement | Typical education needed to enter the occupation | education_typical + education_code | Requirements | CORE |
| 7 | Current Employment | Number of people currently working in the occupation | employment_current | Volume Metric | EXTENDED |
| 8 | Projected Employment | Number of people expected to work in occupation in 10 years | employment_projected | Volume Metric | EXTENDED |
| 9 | Employment Change (Absolute) | Net change in number of jobs over projection period | employment_change | Volume Metric | EXTENDED |
| 10 | Work Experience Requirement | Required prior work experience in a related occupation | work_experience + work_experience_code | Requirements | EXTENDED |
| 11 | Training Requirement | Typical on-the-job training needed | training_typical + training_code | Requirements | EXTENDED |
| 12 | Career Accessibility Score | Derived: composite of education level, experience, and training requirements. Lower = more accessible. | Derived from education_code + work_experience_code + training_code | Derived Metric | OPTIONAL |

### Cross-Source Concept Linkages (FutureProof Integration)
| Concept | BLS OOH Source | College Scorecard Source | Link Mechanism |
|---------|---------------|------------------------|----------------|
| Program-to-Occupation Mapping | soc_code | cipcode | CIP-to-SOC crosswalk (many-to-many) |
| Education ROI | median_annual_wage (occupation salary) | earn_mdn_hi_1yr, earn_mdn_hi_2yr (program graduate earnings) | Compare program-level graduate earnings with occupation-level median salary. Divergence indicates career-switching or geographic effects. |
| Education Requirements Alignment | education_code (what the occupation requires) | credlev (what the program grants) | Match: does the program's credential level meet the occupation's entry requirement? |
| Debt-to-Salary Ratio | median_annual_wage | debt_all_stgp_eval_mdn | Silver/Gold zone derived metric: program debt / occupation salary. Core FutureProof value proposition. |

### Concept-to-Code Mapping Rules

```json
{
  "domain": "us_labor_market_projections",
  "taxonomy": "SOC_2018",
  "tiers": {
    "exact": {
      "description": "6-character SOC code (XX-XXXX) maps to specific detailed occupation",
      "confidence": 1.0,
      "example": "15-1252 -> Software Developers"
    },
    "prefix": {
      "description": "2-digit SOC major group maps to broad occupation category",
      "confidence": 0.8,
      "example": "15 -> Computer and Mathematical Occupations"
    },
    "pattern": {
      "description": "Not applicable — SOC codes are hierarchical, not pattern-based",
      "confidence": null,
      "example": null
    },
    "heuristic": {
      "description": "SOC-to-CIP reverse crosswalk (via CIP-to-SOC crosswalk, many-to-many)",
      "confidence": 0.6,
      "example": "SOC 15-1252 -> CIP 11.0701 (Computer Science) via crosswalk"
    }
  }
}
```

### Collision Resolution Rules

| Collision Scenario | Resolution | Rationale |
|-------------------|------------|-----------|
| Multiple CIP codes mapping to one SOC code | Retain all mappings — one occupation can be entered from many programs | The CIP-to-SOC relationship is genuinely many-to-many. This is valuable for FutureProof: shows all educational paths to a given career. |
| Multiple SOC codes for one CIP code | Retain all mappings — one program can lead to many occupations | Graduates of a program work in diverse occupations. All mapped occupations should be presented to users. |
| Wage = $239,200 (capped) for comparison metrics | Use $239,200 as the value but flag all derived metrics as "at least" or "minimum estimate" | True median is unknown. Any ratio or comparison using a capped wage is a lower bound. Gold zone must surface this caveat. |

---

## Unanswered Interview Questions (BLS OOH)

This section documents EDA-informed interview questions that would normally be asked of the user. Since no interactive interview tool was available, all questions are flagged as unanswered with agent assumptions documented.

### Question 1: SOC 2028 Migration Planning
**Question:** "The current data uses SOC 2018 codes. BLS is expected to release SOC 2028 within the next few years. When that happens, SOC codes will change (splits, merges, renumbering). Should we (a) plan for this now with a SOC version dimension, (b) handle it when it happens, or (c) maintain a SOC 2018-to-2028 crosswalk?"
**Status:** UNANSWERED
**Agent Assumption:** Handle when it happens. SOC 2028 is not yet published. Adding a version dimension now would add complexity with no current benefit. BLS will publish a crosswalk when the transition occurs.
**Mandatory DQ Rule:** Write a sentinel rule that checks soc_code patterns. If any codes appear that do not match known SOC 2018 codes, alert for possible taxonomy change.

### Question 2: Wage Top-Code Handling in Gold Zone
**Question:** "Approximately 3-5% of occupations have wages top-coded at $239,200. For FutureProof's career guidance features, should we (a) display '$239,200+' as the salary, (b) attempt to estimate true medians from other sources, or (c) flag but use $239,200 as-is for calculations?"
**Status:** UNANSWERED
**Agent Assumption:** Option (c) — use $239,200 for calculations but always surface the median_wage_capped flag so downstream consumers know the value is a floor, not the actual median. Gold zone should display "at least $239,200" in user-facing products.
**Mandatory DQ Rule:** No additional rule needed beyond the existing wage cap consistency rule.

### Question 3: Projection Cycle Refresh Strategy
**Question:** "BLS releases new projections every 2 years. When the 2025-2035 cycle is released, should we (a) replace the 2023-2033 data entirely, (b) keep both cycles for trend analysis, or (c) maintain only the latest?"
**Status:** UNANSWERED
**Agent Assumption:** Full replacement (option a) for MVP. The projection cycle is a complete restatement, not an incremental update. Consider retaining historical cycles (option b) if year-over-year trend analysis becomes a requirement.
**Mandatory DQ Rule:** Write a freshness rule that checks load_date is within 900 days of the current date (biennial release + buffer). Alert if data is stale.

### Question 4: Integration Priority — Which BLS Metrics Matter Most for Career Guidance?
**Question:** "The BLS OOH data has projections (growth, openings), wages, and requirements (education, experience, training). For FutureProof's career guidance use case, which of these is most important? Should the Gold zone prioritize (a) salary comparisons, (b) growth/demand metrics, (c) requirements/accessibility, or (d) all equally?"
**Status:** UNANSWERED
**Agent Assumption:** All are important but salary (median_annual_wage) and growth (employment_change_pct, openings_annual_avg) are likely the primary user-facing metrics. Education requirements are critical for the program-to-occupation matching (does this degree qualify me for this job?). All should be CORE priority.
**Mandatory DQ Rule:** No specific rule — but @mcp-engineer should ensure all three categories (salary, growth, requirements) are queryable.

### Question 5: Target User Questions for MCP Server (BLS OOH Specific)
**Question:** "What are the primary career-outcome questions users will ask that require BLS OOH data? For example: 'What's the job outlook for software developers?' or 'Which occupations pay the most with just a bachelor's degree?'"
**Status:** UNANSWERED
**Agent Assumption:** Based on FutureProof's career-guidance mission, primary BLS OOH queries:
1. "What is the salary / job outlook for [occupation]?"
2. "What education do I need to become a [occupation]?"
3. "Which occupations are growing the fastest?"
4. "Which occupations pay the most for [education level]?"
5. "If I study [program], what careers can I pursue and what do they pay?" (requires CIP-to-SOC join)
6. "What's the salary gap between what [program] graduates earn and what [occupation] pays?" (requires cross-source join)
**Mandatory DQ Rule:** No specific rule — guidance for @mcp-engineer.

---

## Assumptions (User-Deferred) — BLS OOH

| # | Assumption | Basis | Confidence | Risk if Wrong |
|---|-----------|-------|------------|---------------|
| 1 | SOC 2028 migration will be handled reactively | SOC 2028 not yet published | MEDIUM | Medium — if migration happens soon, we may need to backfill a version dimension. |
| 2 | Full table replace for biennial projections | BLS projections are complete restates | HIGH | Low — matches BLS publication model. |
| 3 | $239,200 used as-is for calculations with capped flag | No alternative source for true medians | HIGH | Low — standard practice for BLS data consumers. |
| 4 | All three metric categories (salary, growth, requirements) are CORE | FutureProof career-guidance use case | MEDIUM | Low — worst case, some metrics are less prominent in the UI. |
| 5 | ~832 detailed occupations is the expected row count | BLS documentation + EDA notes | MEDIUM | Low — count varies slightly between projection cycles. DQ rule uses 750-900 range. |
| 6 | No PII in this dataset | All occupation-level aggregates from federal agency | HIGH | Very low — BLS publishes this as public data. |
| 7 | openings_annual_avg is more actionable than employment_change for career guidance | Openings include replacement demand; growth can be negative | MEDIUM | Low — both metrics are retained; this only affects default prominence. |

---

## AI-Ready Considerations (BLS OOH)
| Consideration | Recommendation | Notes for @mcp-engineer |
|--------------|---------------|------------------------|
| Primary user questions | "What does [occupation] pay?" "Is [occupation] growing?" "What education do I need for [occupation]?" "What careers can I pursue with [degree]?" | Support occupation lookup by title (fuzzy match) and SOC code (exact match). Title search is critical — users will not know SOC codes. |
| Cross-source queries | "If I study [program] at [school], what careers can I get and what do they pay?" — requires joining College Scorecard (program earnings) with BLS OOH (occupation salary) via CIP-to-SOC crosswalk. | This is the core FutureProof query. Pre-join in Gold zone or implement a join query in the MCP server. Either way, the crosswalk must be available. |
| Context an LLM needs | The LLM must know: (1) wages top-coded at $239,200 mean "at least this much"; (2) projections are 10-year forecasts, not guaranteed outcomes; (3) openings exist even for declining occupations (replacement demand); (4) education requirements are "typical" entry-level, not absolute requirements. | Include as grounding context in MCP responses. Without it, the LLM will make incorrect absolute statements about salaries and requirements. |
| Wage capping disclosure | Always disclose when a wage is top-coded. "The median salary for Surgeons is at least $239,200 (exact figure not reported by BLS)." | The capped flag must propagate to the MCP layer. Do not silently present $239,200 as if it were the actual median. |
| Growth rate interpretation | Negative growth does NOT mean no job opportunities. Even occupations losing employment have replacement openings. | When presenting declining occupations, always pair growth rate with openings. "Secretaries: -10% growth, but 136,000 annual openings due to retirements." |
| Education matching | Users will ask "Can I get this job with my degree?" The answer depends on matching the program's credential level with the occupation's education requirement AND the CIP-to-SOC crosswalk relationship. | Build a "qualification match" indicator in Gold zone: does the program's credential level >= the occupation's education_code? (Requires mapping CREDLEV to education_code scale.) |
| Data freshness disclosure | Projections cover 2023-2033. Wage data reflects the most recent BLS survey. | Include projection cycle in MCP metadata. "These projections cover the 2023-2033 period, published by BLS in [year]." |
| Comparison queries | Users will compare occupations: "What pays more, Software Developer or Data Scientist?" Also compare educational paths: "Is CS or Data Science the better major for becoming a Data Scientist?" | Support ranked lists and side-by-side comparisons. Index by soc_code for fast lookups. |

---

## Confidence Notes (BLS OOH)

**High confidence:**
- Domain identification (BLS Employment Projections / SOC 2018) — unambiguous from source, field names, and data structure
- No PII — all occupation-level aggregates from a federal statistical agency
- Wage top-coding rules ($239,200 cap, consistency with boolean flag)
- SOC code format and uniqueness requirements
- Education/experience/training code ranges and deterministic code-to-text mappings
- Summary row filtering requirement (SOC codes ending in 0000)
- Employment change can be negative (EDA sample is biased positive)

**Medium confidence:**
- Expected row count (~832) — varies slightly between projection cycles; DQ range of 750-900 provides buffer
- Wage null rate (~2-4% expected) — sample shows 10% but sample is small and overrepresents N/A cases
- Full dataset distribution characteristics — all statistical thresholds are PRELIMINARY based on 10-row sample
- Canonical concept map — proposed by agent based on domain knowledge and project goals
- MCP question patterns — assumed from FutureProof project description
- Education code mapping in EDA (code 3 mapped to "High school diploma" in sample — BLS documentation says code 3 should be "Some college, no degree"; verify with full dataset)

**Low confidence / Needs human validation:**
- Projection cycle refresh strategy (replace vs. retain history) — depends on future requirements
- Relative importance of salary vs. growth vs. requirements for career guidance UI
- SOC 2028 migration approach — timeline and impact unknown
- Career Accessibility Score (concept #12) — novel derived metric, may not be useful
- Education code 3 mapping discrepancy — EDA observed code 3 = "High school diploma" but BLS documentation lists code 3 = "Some college, no degree"; needs verification against full dataset or BLS documentation

---
---

# Domain Context: O*NET Database (Task-Level Occupation Data)
**Date:** 2026-04-07
**Agent:** @domain-context
**Based On:** governance/eda/raw-onet-eda.md (2026-04-07)
**Data Sources:** onet (O*NET 30.2 Database — 5 of 7 planned tables from `db_30_2_text.zip`)
**Confidence:** High
**Cross-Reference:** This is the THIRD and final primary FutureProof data source. O*NET joins to BLS OOH via SOC code (direct, after truncating O*NET's 8-digit XX-XXXX.XX to BLS's 6-digit XX-XXXX). O*NET joins to College Scorecard indirectly via the CIP-to-SOC crosswalk chain (College Scorecard -> CIP-to-SOC crosswalk -> SOC -> O*NET).

---

## Domain Identification
**Domain:** U.S. Occupational Information — Task-Level Work Analysis
**Sub-domain:** O*NET Content Model (Work Activities, Work Context, Task Statements, Occupation Relationships)
**Description:** O*NET (the Occupational Information Network) is the U.S. Department of Labor's primary database of occupational information. It provides structured, survey-based data on what workers do in each occupation — their specific tasks, generalized work activities, and the physical/social context of their work environment — plus inter-occupation relationship mappings. Each occupation is rated by incumbents and occupational experts on standardized scales. In the FutureProof pipeline, O*NET provides the deepest layer of occupation analysis: task-level data for AI automation exposure scoring (RES/AI stats), work context for burnout assessment, work activities for human-skill intensity (HMN stat), and occupation relationships for career branching (Stage 3).

---

## Domain Vocabulary

### Core Terms
| Term | Definition | Source | Notes for @data-steward |
|------|-----------|--------|------------------------|
| O*NET-SOC Code | Extended Standard Occupational Classification code in XX-XXXX.XX format. The first 6 characters (XX-XXXX) match the BLS SOC code. The 2-digit suffix (.XX) distinguishes O*NET-specific detailed occupations within a single BLS occupation. A .00 suffix indicates the base/only occupation for that BLS SOC. | O*NET Resource Center / BLS SOC 2018 (external standard) | Auto-approve. CRITICAL: always treat as string, never numeric. The .00 suffix is semantically significant — it means "this is the base occupation" vs. .01/.02 which mean "this is a detailed split." |
| Content Model Element ID | A hierarchical identifier for O*NET's Content Model taxonomy (e.g., "4.A.1.a.1" for "Getting Information"). Organizes all measured dimensions of work into a tree structure. Section 4.A = Work Activities, 4.C = Work Context. | O*NET Content Model (external standard) | Auto-approve. Reference: https://www.onetcenter.org/content.html |
| Scale ID | A code identifying the measurement scale used for a rating. IM = Importance (1-5), LV = Level (0-7), CX = Context point estimate (1-5), CXP = Context category percentage (0-100), CT = Context point estimate for 3-point items (1-3), CTP = Context category percentage for 3-point items (0-100). | O*NET Scales Reference (external standard) | Auto-approve. The 6 scale types are fundamental to interpreting all rated data. See "Scale Type System" section below for full details. |
| Importance (IM) Scale | A 1-5 rating of how important a work activity or context element is to an occupation. Higher = more important. All 41 work activities are rated on IM for every occupation. | O*NET Scales Reference | Auto-approve. Always paired with LV scale for work activities. |
| Level (LV) Scale | A 0-7 rating of the level/complexity at which a work activity is performed. 0 = not relevant (activity does not apply). Combined with IM to create a two-dimensional profile of each occupation's work activities. | O*NET Scales Reference | Auto-approve. LV = 0 correlates with not_relevant = "Y". |
| Domain Source | The methodology used to collect ratings for an occupation. Values: "Incumbent" (survey of workers in the occupation), "Occupational Expert" (small expert panel), "Analyst" (analyst-derived without survey), "Analyst - Transition" (analyst-derived for transitioning/new occupations). | O*NET data collection methodology | Propose — important for understanding data quality. Incumbent has largest samples (27-238), Expert has smallest (18-38), Analyst has no sample. |
| Recommend Suppress | An O*NET quality flag indicating whether the data point should be suppressed due to small sample size or unreliable estimates. Values: "Y" (suppress recommended), "N" (data is reliable), "n/a" (not applicable — used for Occupational Expert and Analyst sources). | O*NET data quality methodology | Propose — this is the primary DQ signal from O*NET. 1.5% of Work Activities and 2.5% of Work Context are flagged "Y". |
| Not Relevant | A flag on the LV (Level) scale indicating the work activity is not relevant to the occupation. Only appears on LV scale rows in Work Activities. When "Y", data_value is near zero (0.00-1.79, mean 0.47). Never used in Work Context (100% "n/a"). | O*NET rating methodology | Propose — only meaningful for Work Activities LV scale. |
| Task Type | Classification of a task statement: "Core" (central to the occupation, 72.6%), "Supplemental" (sometimes performed, 22.9%), or "n/a" (analyst-derived tasks where classification was not performed, 4.5%). | O*NET task classification | Propose — "n/a" correlates 1:1 with domain_source = "Analyst". |
| "All Other" Residual Category | SOC codes ending in "9" in the 4-digit detail position (e.g., "Managers, All Other") that represent a catch-all for occupations not classified elsewhere. These exist in Occupation Data but have NO task, activity, context, or relationship data. 93 such occupations in O*NET 30.2, including all 19 military occupations (55-xxxx). | SOC 2018 taxonomy structure | Propose as project-specific edge case documentation. These are real SOC codes but effectively empty in O*NET. |
| Relatedness Tier | A classification of inter-occupation relationships in the Related Occupations file. Values: "Primary-Short" (index 1-5, most closely related), "Primary-Long" (index 6-10, next-closest), "Supplemental" (index 11-20, broader relationships). This column is newer than the spec anticipated. | O*NET 30.2 Related Occupations file | Propose — replaces the binary primary/supplemental distinction in the spec with a three-tier system. |

### Taxonomy/Classification Systems
| System | Description | Authority | Coverage in Data |
|--------|-------------|-----------|-----------------|
| O*NET-SOC 2019 (extended SOC) | Extended SOC codes using XX-XXXX.XX format. Based on SOC 2018 with O*NET-specific detailed occupations added via the .XX suffix. 1,016 codes in O*NET 30.2 (867 base .00 codes + 149 detailed codes). | O*NET Resource Center / DOL-ETA | 100% — every row in every table is keyed by O*NET-SOC code. |
| O*NET Content Model | Hierarchical taxonomy of work dimensions. Section 4.A = 41 Generalized Work Activities (e.g., "Getting Information", "Making Decisions"). Section 4.C = 57 Work Context elements (e.g., "Time Pressure", "Physical Proximity"). Each element has a unique hierarchical ID (e.g., 4.A.1.a.1). | O*NET Resource Center | 100% of Work Activities rows use 41 Content Model 4.A elements. 100% of Work Context rows use 57 Content Model 4.C elements. |
| O*NET Scale System | 6 scale types used to rate occupation dimensions: IM (Importance, 1-5), LV (Level, 0-7), CX (Context point estimate, 1-5), CXP (Context category percentage, 0-100), CT (Context 3-point estimate, 1-3), CTP (Context 3-category percentage, 0-100). | O*NET Scales Reference | Work Activities uses IM + LV. Work Context uses CX + CXP + CT + CTP. |
| SOC 2018 (derivable) | The standard BLS SOC codes (XX-XXXX) are derivable by truncating O*NET codes to 6 digits. 867 unique BLS SOCs derivable from 1,016 O*NET codes. 76 BLS SOCs have multiple O*NET detailed codes. | BLS/OMB (derived) | 100% derivable. Direct join key to BLS OOH data (832 occupations). |

### Scale Type System (Critical for All Downstream Agents)

This is the single most important domain concept for O*NET data interpretation. Every rated value in Work Activities and Work Context is measured on one of 6 scales. Misinterpreting the scale makes the data meaningless.

| Scale ID | Full Name | Range | Used In | Rows in Data | Interpretation |
|----------|-----------|-------|---------|-------------|----------------|
| IM | Importance | 1.0 - 5.0 | Work Activities | 36,654 (50% of WA) | How important is this activity to the occupation? 1=Not Important, 5=Extremely Important. |
| LV | Level | 0.0 - 7.0 | Work Activities | 36,654 (50% of WA) | At what level of complexity is this activity performed? 0=Not Relevant. Paired with IM for every activity-occupation combination. |
| CX | Context (point estimate) | 1.0 - 5.0 | Work Context | 49,170 (16.5% of WC) | Point estimate rating for a 5-point context dimension. One row per element per occupation. |
| CXP | Context Categories (percentage) | 0.0 - 100.0 | Work Context | 241,450 (81.1% of WC) | Percentage of respondents choosing each of 5 response categories. 5 rows per CX element per occupation. Sum to 100% per element-occupation. |
| CT | Context 3-point (point estimate) | 1.0 - 3.0 | Work Context | 1,788 (0.6% of WC) | Point estimate for 3-point context dimensions (Work Schedules, Duration of Typical Work Week). |
| CTP | Context 3-category (percentage) | 0.0 - 100.0 | Work Context | 5,268 (1.8% of WC) | Percentage choosing each of 3 response categories. 3 rows per CT element per occupation. |

**Why this matters for Silver/Gold zones:** The spec estimated ~49,000 Work Context rows. The actual count is 297,676 because CXP rows (81.1% of all Work Context) expand each CX element into 5 category-percentage rows. Silver zone transformations must understand this structure to correctly pivot or aggregate the data. For FutureProof's Burnout boss fight, the CX point-estimate rows are likely sufficient; the CXP rows provide distribution detail for deeper analysis.

### Enumerated Values with Business Meaning
| Field | Values | Meaning |
|-------|--------|---------|
| scale_id (Work Activities) | IM, LV | IM = Importance (1-5), LV = Level (0-7). Every occupation has both IM and LV ratings for all 41 activities. |
| scale_id (Work Context) | CX, CXP, CT, CTP | CX = 5-point estimate, CXP = 5-category percentages, CT = 3-point estimate, CTP = 3-category percentages. CXP is 81.1% of all WC rows. |
| task_type | Core, Supplemental, n/a | Core = central to occupation (72.6%), Supplemental = sometimes performed (22.9%), n/a = analyst-derived (4.5%). |
| domain_source | Incumbent, Occupational Expert, Analyst, Analyst - Transition | Incumbent = worker survey (70-75%), Expert = small panel (23-24%), Analyst = analyst-derived (4-5%), Analyst - Transition = new/transitioning occupation (1-2%). |
| recommend_suppress | N, Y, n/a | N = data reliable, Y = suppress recommended (small sample), n/a = not applicable (expert/analyst sources). |
| not_relevant (Work Activities only) | N, Y, n/a | N = activity is relevant (LV scale), Y = activity not relevant (LV scale, data_value near 0), n/a = all IM-scale rows + all Work Context rows. |
| relatedness_tier | Primary-Short, Primary-Long, Supplemental | Primary-Short (index 1-5) = most related, Primary-Long (index 6-10) = next-closest, Supplemental (index 11-20) = broader relationships. |
| source_method | "bulk_zip_download" | Metadata: data fetched from O*NET 30.2 ZIP archive. |

---

## Entity Types

### Primary Entities
| Entity Type | Identifier Field(s) | Example | Notes for @entity-resolver |
|-------------|---------------------|---------|---------------------------|
| Occupation (O*NET detail) | onet_soc_code | 15-1252.00 (Software Developers) | ID-based resolution. O*NET-SOC code is authoritative. Always treat as string (XX-XXXX.XX). 1,016 unique occupations in O*NET 30.2. Direct join to BLS OOH by truncating to XX-XXXX (867 unique BLS SOCs derivable). |
| Occupation (BLS base) | onet_soc_code truncated to 6 digits | 15-1252 (Software Developers) | Derived entity for cross-source joining. 76 BLS SOCs split into multiple O*NET detailed codes. Silver zone must handle aggregation (e.g., average O*NET ratings across detailed codes when joining to a single BLS SOC). |
| Work Activity | element_id (4.A.x.x.x) | 4.A.1.a.1 (Getting Information) | 41 distinct activities. Fixed taxonomy — same 41 across all occupations. Each occupation is rated on all 41 activities on both IM and LV scales. |
| Work Context Element | element_id (4.C.x.x.x) | 4.C.1.a.2.a (Time Pressure) | 57 distinct context elements. Fixed taxonomy. 55 use CX/CXP scales, 2 use CT/CTP scales. |
| Task | task_id | 15046 | Globally unique integer. 18,796 distinct tasks across 923 occupations. Variable per occupation (4-40 tasks, mean 20.4). |
| Occupation Relationship | onet_soc_code + related_onet_soc_code | 15-1252.00 -> 15-1254.00 | Directed pair. 18,460 relationships. 56.3% are symmetric. |

### Entity Lifecycle Events
| Event Type | How It Appears in Data | Frequency |
|-----------|----------------------|-----------|
| Occupation added (new SOC) | New onet_soc_code appears in Occupation Data. May initially appear with only Tasks and Related Occupations data (no Work Activities/Context until survey data is collected). | Uncommon. 29 occupations currently in this "partial data" state. |
| Occupation removed/reclassified | onet_soc_code disappears from future releases. O*NET publishes crosswalk tables for SOC taxonomy changes. | Rare. Tied to SOC revision cycles (~10 years). |
| Survey data refresh | Date field updates for an occupation as new survey waves complete. Rolling updates — not all occupations update simultaneously. | Continuous. Dates range from 12/2004 to 12/2025 (21-year span). Most data collected 2019-2025. |
| Occupation transition to full data | An occupation that previously had only Tasks/Related Occupations gains Work Activities and Work Context data (moves from the 29-occupation partial set to the 894-occupation full set). | Uncommon. Happens as O*NET conducts surveys for new occupations. |
| "All Other" / Military — never gains data | 93 residual "All Other" and Military occupations exist in Occupation Data but never gain child data because they are aggregate/residual categories, not specific occupations that can be surveyed. | Permanent. These 93 codes will never have task/activity/context data. |

---

## Temporal Patterns

### Valid Time
| Pattern | Description | Notes for @temporal-modeler |
|---------|-------------|---------------------------|
| Rolling survey snapshot | O*NET data is collected via ongoing surveys. The `date` field on each row indicates when that specific data point was collected. Dates range from 12/2004 to 12/2025 — a 21-year span. Most data is recent (2019-2025 peak). | Model as a snapshot table. The date field is informational metadata, not a temporal dimension for time-series analysis. All data in a given O*NET release is considered "current" regardless of individual survey dates. |
| Release-based versioning | O*NET publishes numbered releases (current: 30.2). Each release is a complete database, not an incremental update. Some occupations have data from 2004 surveys that has not been re-surveyed. | The Silver zone should treat each O*NET release as a full replacement. If tracking across releases is needed, add a release_version dimension. |
| Uneven occupation freshness | Not all occupations are surveyed simultaneously. Some have data from 2004, others from 2025. The `date` field varies within a single release. | For FutureProof, this means some occupation profiles are based on older survey data. Consider exposing the survey date as a freshness indicator in Gold zone products. Occupations with very old dates (pre-2015) may have less accurate ratings. |

### Amendment/Correction Patterns
| Pattern | Description | Frequency |
|---------|-------------|-----------|
| Quarterly release updates | O*NET publishes ~2-4 releases per year (e.g., 30.0, 30.1, 30.2). Each release may add new occupations, update survey data, or correct errors. | Quarterly. Full database replacement each time. |
| Retroactive survey refresh | When O*NET re-surveys an occupation, the new ratings replace the old ones for that occupation. Old data is not preserved within the database. | Ongoing. No mechanism to detect which occupations changed between releases. |

---

## Data Quality Considerations

### Known Edge Cases
| Edge Case | Description | Impact | Notes for @dq-rule-writer |
|-----------|-------------|--------|--------------------------|
| 93 "All Other" / Military occupations with no child data | These are residual SOC categories (e.g., "Managers, All Other" 11-9199.00) and all 19 Military occupations (55-xxxx.00). They appear in Occupation Data but have ZERO rows in Task Statements, Work Activities, Work Context, or Related Occupations. All 93 are .00 base codes. | Expected. NOT a data quality issue. | Do NOT write referential integrity rules that require all Occupation Data SOCs to appear in child tables. Instead, write a rule that confirms approximately 93 occupations are "Occupation Data only" — significant deviation from this count could indicate a source change. Silver zone should filter these out or flag as "no O*NET profile available." |
| 29 occupations with partial data | 29 occupations have Tasks and Related Occupations but NO Work Activities or Work Context. These are recently added or transitioning occupations (e.g., "Web and Digital Interface Designers" 15-1255.00). Combined with the 93 above: 122 total missing from Work Activities/Work Context. | Expected for new occupations. | Allow this partial pattern. Write a rule that checks the partial-data count is between 20-40 (roughly stable across releases). These occupations should be flagged in Silver zone as "partial O*NET profile." |
| Career Changers Matrix and Career Starters Matrix files DO NOT EXIST | These 2 of 7 planned files are not in the O*NET 30.2 ZIP archive. All HTTP download attempts return 404. They may have been discontinued or consolidated into the Related Occupations file (which now has a Relatedness Tier column). | CRITICAL for Stage 3 branching pipeline. | The ingestors for these tables MUST be removed or made conditional. Related Occupations (18,460 rows with Primary-Short/Primary-Long/Supplemental tiers) is the fallback for career branching. See "Career Changers/Starters Data Gap" section below. |
| Work Context 6x larger than spec estimated | Spec estimated ~49,000 rows. Actual: 297,676. The spec did not account for CXP/CTP category-percentage rows (81.1% of all Work Context data). | NOT a bug. DQ row count rules must use the actual count, not the spec estimate. | Set Work Context row count threshold at 297,676 +/- 5%. The original spec estimate of ~49,000 was wrong. Document this clearly so future spec readers are not confused. |
| 16 occupations with 57 Work Context rows (vs. 338 normal) | 16 occupations have only CX/CT point-estimate rows, missing all CXP/CTP category-percentage rows. These appear to be recently updated occupations where category data has not yet been collected. | MEDIUM. These occupations have complete point-estimate ratings but lack distribution detail. | Flag but do not reject. Write a rule that checks for occupations with fewer than 338 rows and documents them as "partial Work Context data." The CX point-estimate data is still usable for FutureProof's Burnout boss fight. |
| recommend_suppress = "Y" (1.5% WA, 2.5% WC) | O*NET flags data points with small samples or unreliable estimates. Work Context has higher suppression rates on CXP/CTP percentage scales (3.0% CXP, 5.0% CTP) than point-estimate scales (0.04% CX). | Expected. Preserve in Bronze, filter or flag in Silver. | Write rules that check suppress rates: Work Activities < 3%, Work Context < 5%. Alert if rates increase significantly (could indicate O*NET changing methodology or reducing survey coverage). |
| not_relevant = "Y" only on LV scale (1.5% of WA) | 1,094 Work Activities rows have not_relevant = "Y". All are on the LV (Level) scale, never IM. Data values are near zero (0.00-1.79, mean 0.47). Most common: mechanical/technical activities rated irrelevant for office/service occupations. | Expected. These are real "this activity doesn't apply to this job" signals. | Preserve the flag. Silver zone should treat not_relevant = "Y" rows as valid data (the near-zero LV value IS the correct rating for an irrelevant activity). Do NOT filter these out — they are analytically meaningful for identifying what occupations DON'T do. |
| Related Occupations schema changed from spec | Spec expected a column named "Related Index". Actual column is "Index". Spec did not anticipate the "Relatedness Tier" column. | CRITICAL for ingestor — the column name mismatch causes 100% data loss. | The ingestor must be updated: read "Index" instead of "Related Index", and capture the new "Relatedness Tier" column. See "Ingestor Issues" in EDA report. |
| Task type = "n/a" (4.5% of tasks) | 845 tasks have task_type = "n/a" instead of "Core" or "Supplemental". These correlate exactly 1:1 with domain_source = "Analyst". | Expected for analyst-derived tasks. | Allow "n/a" as a valid task_type value. DQ rule should check that task_type "n/a" implies domain_source = "Analyst" (deterministic relationship). |
| Date range spans 21 years (12/2004 to 12/2025) | Some occupation data has not been re-surveyed since 2004. Most data is from 2019-2025. | NOT an error, but old data may be less accurate for rapidly changing occupations. | Do NOT write a freshness rule that rejects old dates. Consider a Gold zone "data freshness" indicator that flags occupations with survey dates older than 10 years. |
| Analyst - Transition domain source (1.8% of WA, 0.3% of WC) | These are transitioning occupations with analyst-derived ratings. They have no sample size (N=null), no standard error, no CI bounds, and recommend_suppress = "n/a". | Expected for new/transitioning occupations. | Allow null N, null SE, null CI when domain_source = "Analyst - Transition". Write a correlation rule: if domain_source = "Analyst - Transition", then N must be null. |

### Career Changers/Starters Data Gap — Impact on FutureProof Stage 3

The Career Changers Matrix and Career Starters Matrix were planned as the primary data source for Stage 3 career branching ("where do people in this career go next?" and "how do people enter this career?"). These files do not exist in O*NET 30.2.

**Impact assessment:**
- Stage 3 branching CANNOT use Career Changers/Starters as originally planned
- Related Occupations (18,460 rows) is the ONLY available career relationship data
- Related Occupations provides occupational similarity, not actual career transition data — the semantics are different ("these jobs are similar" vs. "people actually move between these jobs")
- The new Relatedness Tier column (Primary-Short/Primary-Long/Supplemental) provides useful granularity for prioritizing suggestions

**Recommended fallback for Stage 3:**
1. Use Related Occupations Primary-Short (index 1-5) as the primary branching source — these are the most closely related occupations
2. Use Primary-Long (index 6-10) as secondary suggestions
3. Supplemental (index 11-20) for "explore more" features
4. Consider supplementing with external data (LinkedIn career transitions, Census ACS occupation-to-occupation flows) if true transition data is needed post-hackathon

**Notes for @dq-rule-writer:** Do NOT write rules for raw.onet_career_changers or raw.onet_career_starters — these tables will not exist. Redirect all career branching DQ rules to raw.onet_related_occupations.

### Domain-Specific Validity Rules
| Rule | Description | Source |
|------|-------------|--------|
| O*NET-SOC code format: XX-XXXX.XX | Every onet_soc_code must match `^\d{2}-\d{4}\.\d{2}$`. Both the base SOC and the .XX suffix must be present. | O*NET-SOC standard. Verified: 100% valid across all 5 tables. |
| O*NET-SOC code uniqueness in Occupation Data | No duplicate codes in the occupation master table. 1,016 unique = 1,016 rows. | Data grain definition. Duplicates indicate an ingestor bug. |
| Work Activities: exactly 82 rows per occupation | Every occupation with WA data must have exactly 82 rows (41 activities x 2 scales). No exceptions observed. | Structural invariant verified in EDA. |
| Work Context: 338 or 57 rows per occupation | Full-data occupations have 338 rows. Partial-data occupations (16 observed) have 57 rows (CX/CT only, no CXP/CTP). No other counts are valid. | Structural invariant verified in EDA. |
| Related Occupations: exactly 20 rows per source occupation | Every occupation with relationship data has exactly 20 rows (5 Primary-Short + 5 Primary-Long + 10 Supplemental). | Structural invariant: 923 occupations x 20 = 18,460 rows. |
| No self-references in Related Occupations | source onet_soc_code must never equal related_onet_soc_code. 0 self-references observed. | Logical domain constraint — an occupation cannot be related to itself. |
| IM scale range [1.0, 5.0] | Importance scale data_value must be between 1.0 and 5.0 inclusive. Observed: 1.00-4.99. | O*NET Scales Reference. |
| LV scale range [0.0, 7.0] | Level scale data_value must be between 0.0 and 7.0 inclusive. Observed: 0.00-6.81. Zero is valid (means not relevant). | O*NET Scales Reference. |
| CX scale range [1.0, 5.0] | Context 5-point estimate must be between 1.0 and 5.0. | O*NET Scales Reference. |
| CXP scale range [0.0, 100.0] | Context category percentage must be between 0 and 100. 5 CXP rows per CX element should sum to approximately 100. | O*NET Scales Reference + percentage semantics. |
| CT scale range [1.0, 3.0] | Context 3-point estimate must be between 1.0 and 3.0. Only used for Work Schedules and Duration elements. | O*NET Scales Reference. |
| CTP scale range [0.0, 100.0] | Context 3-category percentage must be between 0 and 100. 3 CTP rows per CT element should sum to approximately 100. | O*NET Scales Reference + percentage semantics. |
| Task ID globally unique | Every task_id in Task Statements must be globally unique across all occupations. 18,796 unique IDs verified. | Data grain definition. |
| Referential integrity: all child SOC codes exist in Occupation Data | Every onet_soc_code in Tasks, Work Activities, Work Context, and Related Occupations must exist in Occupation Data. 0 orphans verified. | Cross-table integrity. |
| Work Context not_relevant = "n/a" always | Unlike Work Activities, Work Context never uses the not_relevant flag. All 297,676 rows have "n/a". | EDA observation — if any "Y" or "N" values appear, it indicates a source schema change. |

---

## Regulatory & Compliance Context

### Applicable Regulations
| Regulation | Relevance | Key Requirements | Notes for @bcbs239-auditor |
|-----------|-----------|-----------------|---------------------------|
| DOL/ETA Data Publication Terms | Primary. O*NET is published by the U.S. Department of Labor's Employment and Training Administration under Creative Commons CC BY 4.0 license. | 1. Data is freely available for public use. 2. Attribution to O*NET Resource Center required. 3. License terms: https://www.onetcenter.org/license_db.html | No access restrictions. Attribution should appear in data products and MCP server responses. Assess for data lineage and provenance tracking. |
| OMB Statistical Policy (SOC taxonomy) | Background. O*NET's occupation coding follows the OMB-maintained SOC 2018 taxonomy. SOC revisions require federal agencies to adopt new versions. | Same as BLS OOH section — SOC 2028 migration planning applies equally to O*NET data. | Relevant for cross-source SOC alignment. When SOC 2028 is published, O*NET and BLS will both need to migrate — changes should be synchronized. |

### PII Expectations
| PII Type | Expected? | Sensitivity | Notes for @pii-scanner |
|----------|-----------|-------------|----------------------|
| Personal names | No | N/A | O*NET contains occupation titles and descriptions, not personal identifiers. Survey respondent identities are never published. |
| Worker identifiers | No | N/A | All data is occupation-level aggregate. No individual worker records, employee IDs, or survey respondent identifiers. |
| Health records | No | N/A | Work Context includes physical demands and health-related work conditions (e.g., "Exposed to Hazardous Conditions") but these are occupation-level descriptions, not individual health records. |
| Financial PII | No | N/A | O*NET does not contain wage data. (Wages come from BLS OOH, not O*NET.) |
| Location data | No | N/A | O*NET is national-level data. No geographic breakdown, addresses, or coordinates. |

**Summary for @pii-scanner:** This dataset contains NO PII. All values are occupation-level aggregates derived from anonymized surveys conducted by the U.S. Department of Labor. Survey respondent identities are never included in the published database. The pipeline should confirm zero PII findings. Justification: "governance/domain-context.md O*NET PII section confirms no personal data — all fields are occupation-level aggregates from anonymized surveys."

---

## External Data Opportunities (from O*NET perspective)
| External Source | What It Adds | Join Key | Notes for @insight-manager |
|----------------|-------------|----------|---------------------------|
| BLS OOH (ALREADY INGESTED) | Occupation wages, employment projections, education requirements. Combined with O*NET, creates comprehensive occupation profiles: what the job involves (O*NET) + what it pays and where it's headed (BLS). | soc_code (truncate O*NET XX-XXXX.XX to BLS XX-XXXX) | CRITICAL. Direct SOC join. 76 BLS SOCs have multiple O*NET detailed codes — Silver zone must aggregate O*NET ratings for these cases. |
| College Scorecard (ALREADY INGESTED) | Program-level outcomes (earnings, debt) by institution and major. Combined with O*NET + BLS, completes the FutureProof chain: program -> occupation -> tasks/context. | CIP-to-SOC crosswalk (College Scorecard CIP -> SOC -> O*NET) | CRITICAL. Two-hop join. Enables "If I study [program], what tasks will I do in my career and how exposed am I to AI?" |
| Karpathy/AI Automation Scores (EXTERNAL) | AI automation susceptibility scores for tasks or work activities. Combined with O*NET task data, directly powers the RES (AI Resilience) stat and AI boss fight. | Task-level or activity-level matching (methodology TBD) | HIGH VALUE. This is the key external enrichment for FutureProof's AI exposure analysis. Join method may be semantic (LLM-based task matching) rather than key-based. |
| LinkedIn Career Transition Data (EXTERNAL) | Actual career transition patterns — where people move from/to specific occupations. Would supplement or replace the missing Career Changers/Starters Matrix. | soc_code or occupation title matching | MEDIUM VALUE. Would enable true transition-based Stage 3 branching vs. similarity-based (Related Occupations). Likely requires partnership or scraping. |
| O*NET Skills, Knowledge, Abilities (IN SAME DATABASE) | Additional O*NET tables not in scope for hackathon MVP. Skills (35 dimensions), Knowledge (33 dimensions), Abilities (52 dimensions). Would enrich skill tree generation and career matching. | onet_soc_code (direct join — same database) | MEDIUM VALUE for post-hackathon. Easy to add — same ZIP file, same ingestor pattern. |
| Census ACS Occupation-to-Occupation Flows (EXTERNAL) | Actual worker flows between occupations from the American Community Survey. Alternative data source for career transitions. | soc_code (Census uses SOC) | LOW-MEDIUM VALUE. Public data but complex to process. Would provide statistical career transition rates. |

---

## Concept Mapping Guidance

### Source Codes to Business Concepts
| Source Code Pattern | Maps To | Confidence | Notes for @cde-tagger |
|--------------------|---------|------------|----------------------|
| onet_soc_code (XX-XXXX.XX) | Occupation Identity (O*NET detail level) | Exact | O*NET-SOC is the authoritative code. Truncate to XX-XXXX for BLS joining. Always retain the full .XX suffix in O*NET-internal tables. |
| onet_soc_code prefix (XX) | SOC Major Group (23 groups) | Exact (prefix) | Same 23 major groups as BLS SOC. Useful for category-level aggregation. |
| onet_soc_code suffix (.XX) | O*NET Detail Level | Pattern | .00 = base BLS occupation (867 codes). Non-.00 = O*NET detailed split (149 codes). The suffix determines whether aggregation is needed for BLS joining. |
| element_id (4.A.x.x.x) | Generalized Work Activity | Exact | 41 fixed dimensions. Map to FutureProof's HMN stat dimensions. Each activity is a potential "human skill" axis. |
| element_id (4.C.x.x.x) | Work Context Dimension | Exact | 57 fixed dimensions. Key burnout-relevant elements: Time Pressure (4.C.1.a.2.a), Duration of Typical Work Week (4.C.3.d.4), Work Schedules (4.C.3.d.3), Physical Proximity (4.C.2.b.1.a). |
| task_id + task text | Occupation-Specific Task | Exact | Globally unique tasks. These are the atomic units for AI automation exposure scoring — "can an AI do this specific task?" |
| scale_id (IM/LV/CX/CXP/CT/CTP) | Measurement Scale | Exact | Always use scale_id to determine the correct interpretation and range of data_value. NEVER compare values across different scale types. |
| relatedness_tier | Career Relationship Strength | Exact | Primary-Short = closest, Primary-Long = next-closest, Supplemental = broad. Use for tiered career suggestion relevance. |

### Known Mapping Ambiguities
| Source Code | Candidates | Recommended | Rationale |
|------------|-----------|-------------|-----------|
| onet_soc_code .00 suffix | "This IS the BLS occupation" vs. "This is O*NET's version of the BLS occupation" | Treat .00 as direct BLS mapping | 867 of 1,016 O*NET codes are .00. For cross-source joining, truncate to 6 digits. The .00 suffix is semantically equivalent to the BLS code. |
| Non-.00 O*NET codes to BLS | Aggregate to parent BLS SOC vs. pick one detailed code | Aggregate (average ratings across detailed codes) | When BLS SOC 29-1229 maps to O*NET 29-1229.01 + 29-1229.02, the BLS-level profile should be the average of the detailed O*NET profiles. Weighted average by employment (from BLS OOH) would be ideal but requires cross-source data. |
| Related Occupations vs. Career Changers/Starters | Occupation similarity vs. actual career transitions | Use Related Occupations as fallback, document limitation | Related Occupations measures "these jobs are similar" (content-based). Career Changers/Starters would have measured "people actually move between these jobs" (transition-based). The semantics differ but Related Occupations is the only available data. |
| CX vs. CXP for Work Context analysis | Point estimate (one value) vs. distribution (5 values) | Use CX for scalar metrics, CXP for distribution analysis | For FutureProof's Burnout boss fight, CX point estimates are simpler and sufficient. CXP provides richer "how many people experience X" detail for deeper analysis. |
| Work Activities: IM vs. LV for skill profiling | Importance (how much it matters) vs. Level (how complex it is) | Use both — they measure different things | IM answers "Is this activity important to this job?" LV answers "At what level of complexity?" For FutureProof's HMN stat, IM identifies WHICH human skills matter; LV identifies HOW MUCH skill is needed. |

---

## Canonical Concept Map (O*NET)

This section defines the target business concepts for O*NET data that feed into the Silver and Gold zones. It complements the College Scorecard and BLS OOH concept maps above — together they form the complete FutureProof concept model.

**Status:** PROPOSED (Unconfirmed)
**Source:** Agent-proposed based on domain knowledge of O*NET Content Model, FutureProof's five-stat/boss-fight architecture, and EDA findings from O*NET 30.2.

> **User Said:** User directed: "O*NET is the third and final primary data source for FutureProof. It provides task-level AI automation exposure, work context for burnout, career branching. Career Changers/Starters files are missing — Related Occupations is the fallback." (session 2026-04-07)
> **Agent Action:** Proposed canonical concepts based on O*NET Content Model structure, FutureProof stat/boss architecture, and available data (5 of 7 planned tables). Concepts 14-15 (Career Transition Source/Target) are removed due to missing Career Changers/Starters data; replaced with Concept 14 (Occupation Similarity Network) based on Related Occupations.

### Target Business Concepts
| # | Business Concept | Plain English Name | Expected Source Codes | Category | Priority |
|---|-----------------|-------------------|----------------------|----------|-----------|
| 1 | Occupation Profile (O*NET) | Complete O*NET profile for an occupation | onet_soc_code + title + description (1,016 occupations, 923 with full data) | Entity | CORE |
| 2 | Task Inventory | All tasks performed in an occupation | task_id + task text per occupation (mean 20.4 tasks per occupation) | Work Content | CORE |
| 3 | Task AI Exposure Potential | Whether a specific task can be automated by AI | task text (input to AI scoring model, e.g., Karpathy scores) | Derived / AI Analysis | CORE |
| 4 | Human Skill Profile (HMN stat) | The pattern of human work activities required by an occupation | Work Activities IM + LV ratings for 41 activities per occupation | Stat Input | CORE |
| 5 | Work Context Profile | The physical/social environment of an occupation | Work Context CX ratings for 57 elements per occupation | Stat Input | CORE |
| 6 | Burnout Risk Indicators | Work context dimensions relevant to occupational stress | Specific Work Context elements: Time Pressure, Duration of Typical Work Week, Work Schedules, Physical Proximity, Consequence of Error, Frequency of Conflict Situations | Boss Fight Input | CORE |
| 7 | AI Resilience Score (RES stat) | Composite score of how resilient an occupation is to AI automation | Derived from task-level AI exposure + work activity human-skill intensity | Derived Metric | CORE |
| 8 | Occupation Similarity Network | Related occupations with tiered relevance (fallback for career branching) | Related Occupations: Primary-Short (index 1-5), Primary-Long (6-10), Supplemental (11-20) | Career Pathway | CORE |
| 9 | Work Activity Importance Ranking | Which of the 41 activities matter most for each occupation | Work Activities IM scale, ranked by data_value per occupation | Analytical View | EXTENDED |
| 10 | Work Activity Complexity Profile | Complexity level at which each activity is performed | Work Activities LV scale per occupation | Analytical View | EXTENDED |
| 11 | Work Context Distribution | How respondents distributed across response categories | Work Context CXP/CTP percentage rows per element per occupation | Analytical View | EXTENDED |
| 12 | Occupation Data Completeness Flag | Whether an occupation has full, partial, or no O*NET profile data | Derived from presence/absence in child tables (full=894, partial=29, none=93) | Data Quality Indicator | EXTENDED |
| 13 | Survey Freshness Indicator | How recently the O*NET survey data was collected for an occupation | date field from Task Statements / Work Activities | Data Quality Indicator | OPTIONAL |

### Cross-Source Concept Linkages (FutureProof Integration)
| Concept | O*NET Source | BLS OOH Source | College Scorecard Source | Link Mechanism |
|---------|-------------|---------------|------------------------|----------------|
| Full Occupation Profile | O*NET tasks, activities, context | BLS wage, growth, requirements | (indirect — via CIP-to-SOC) | SOC code join (O*NET XX-XXXX.XX truncated to BLS XX-XXXX) |
| AI Exposure by Career Path | O*NET task-level AI scoring | BLS occupation growth (is AI-exposed job declining?) | (indirect) | SOC code join. Declining growth + high AI exposure = strong signal. |
| Program-to-Tasks Chain | O*NET tasks for mapped occupations | (bridge) | College Scorecard CIP programs | CIP -> SOC crosswalk -> O*NET tasks. "If I study X, what tasks will I do?" |
| Burnout-Adjusted Career Value | O*NET work context (stress, hours) | BLS wage (compensation) | College Scorecard debt (financial pressure) | SOC join + CIP-SOC crosswalk. Enables "Is the salary worth the burnout risk?" |
| Career Branching Options | O*NET Related Occupations (similarity) | BLS growth/openings for related occupations | (indirect) | SOC join. "What similar careers are growing faster?" |

### Concept-to-Code Mapping Rules

```json
{
  "domain": "occupational_information_onet",
  "taxonomy": "ONET_SOC_2019",
  "tiers": {
    "exact": {
      "description": "8-character O*NET-SOC code (XX-XXXX.XX) maps to specific O*NET detailed occupation",
      "confidence": 1.0,
      "example": "15-1252.00 -> Software Developers"
    },
    "prefix": {
      "description": "6-character SOC code (XX-XXXX, truncated) maps to BLS base occupation",
      "confidence": 0.95,
      "example": "15-1252 -> Software Developers (BLS level)"
    },
    "pattern": {
      "description": "2-digit SOC major group prefix maps to broad occupation category",
      "confidence": 0.8,
      "example": "15 -> Computer and Mathematical Occupations"
    },
    "heuristic": {
      "description": "Content Model element IDs map to work dimensions via hierarchical taxonomy",
      "confidence": 1.0,
      "example": "4.A.1.a.1 -> Getting Information (Work Activity), 4.C.1.a.2.a -> Time Pressure (Work Context)"
    }
  }
}
```

### Collision Resolution Rules

| Collision Scenario | Resolution | Rationale |
|-------------------|------------|-----------|
| Multiple O*NET detailed codes for one BLS SOC | Aggregate (average) O*NET ratings across detailed codes when joining to BLS | A single BLS occupation (e.g., 29-1229 "Physicians, All Other") may split into multiple O*NET details (.01, .02). The BLS-level profile should average the O*NET details. Employment-weighted average is ideal but requires BLS employment data per detailed code (not available). |
| IM vs. LV for activity importance | Retain both; do not collapse | IM and LV measure orthogonal dimensions (importance vs. complexity). Both are needed for complete skill profiling. High-IM + low-LV means "important but simple." Low-IM + high-LV means "uncommon but complex when done." |
| CX vs. CXP for Work Context metrics | Use CX as the default scalar metric; retain CXP for distribution analysis | CX is simpler (one value per element per occupation). CXP provides richer detail (5 percentages per element per occupation). For FutureProof MVP, CX is sufficient. |
| Related Occupations: which tier to use for branching suggestions | Use Primary-Short (index 1-5) as primary, Primary-Long (6-10) as secondary, Supplemental (11-20) as "explore more" | Primary-Short occupations are the most similar. This tiered approach provides natural UX for career exploration (first show closest matches, then expand). |
| recommend_suppress = "Y" data points | Preserve in Bronze; Silver zone should flag but not filter by default | Suppressed data points may still be useful for directional analysis (they have values, just unreliable ones). Gold zone should exclude suppressed points from stat calculations. |

---

## O*NET-Specific: SOC Code Cross-Source Bridging

This section documents the SOC code format differences between O*NET and BLS OOH, which is critical for Silver zone integration.

### Format Comparison
| Source | Format | Example | Unique Codes |
|--------|--------|---------|-------------|
| O*NET | XX-XXXX.XX (8-digit) | 15-1252.00 | 1,016 |
| BLS OOH | XX-XXXX (6-digit) | 15-1252 | ~832 |
| Derivable from O*NET | XX-XXXX (truncated) | 15-1252 | 867 |

### Bridging Rules for Silver Zone

1. **Simple case (.00 suffix, 867 codes):** Truncate O*NET code to 6 digits. Direct 1:1 mapping to BLS SOC. Example: O*NET 15-1252.00 -> BLS 15-1252.
2. **Split case (non-.00 suffix, 149 codes across 76 BLS SOCs):** Multiple O*NET codes map to one BLS SOC. Truncate for joining, but retain full O*NET code for O*NET-internal analysis. Example: O*NET 29-1229.01 + 29-1229.02 + 29-1229.03 -> BLS 29-1229.
3. **Aggregation strategy for splits:** When presenting a single occupation profile at BLS granularity (e.g., for Gold zone occupation profiles), average O*NET ratings across detailed codes. Document which detailed codes were aggregated.
4. **Coverage gap:** O*NET has 867 derivable BLS SOCs vs. BLS OOH's ~832 occupations. Some O*NET SOCs may not have BLS OOH data (and vice versa). Silver zone should use LEFT joins from each source and document unmatched codes.

### Notes for @entity-resolver
- The O*NET-to-BLS SOC mapping is a deterministic truncation, NOT a fuzzy match. No resolution algorithm is needed.
- Entity resolution complexity arises only when aggregating multiple O*NET detailed codes into one BLS base occupation. This is a known 1:N relationship (76 cases), not an ambiguity.
- The 93 "All Other"/Military O*NET occupations will mostly NOT match BLS OOH (BLS also excludes "All Other" categories from detailed projections). This is expected.

---

## O*NET-Specific: The 93 "All Other" / Military Occupation Gap

These 93 occupations exist in Occupation Data but have zero rows in all other tables. They are structurally empty — not missing data.

**Why they exist:** SOC taxonomy includes "All Other" residual categories for each minor group (e.g., 11-9199.00 "Managers, All Other") to capture occupations not individually classified. O*NET cannot survey these because they are heterogeneous collections, not specific jobs. All 19 military occupations (55-xxxx.00) are also in this set because O*NET does not survey military positions.

**Impact on FutureProof:**
- These 93 occupations will have NO O*NET profile (no tasks, no activities, no context)
- They WILL appear in BLS OOH (BLS publishes projections for "All Other" categories)
- Silver zone joins between O*NET and BLS OOH will have null O*NET data for these occupations
- Gold zone occupation profiles should mark them as "No detailed O*NET data available — this is a residual occupation category"

**Notes for @data-steward:** Create a glossary entry for "All Other residual occupation" explaining why no O*NET data exists. This prevents downstream users from interpreting the null O*NET data as a data quality issue.

---

## Unanswered Interview Questions (O*NET)

This section documents EDA-informed interview questions that would normally be asked of the user via the domain interview protocol. Since this is a directed pipeline run, all questions are flagged as unanswered with agent assumptions documented. Each unanswered question creates a mandatory DQ rule requirement.

### Question 1: Career Changers/Starters Data Source
**Question:** "The Career Changers Matrix and Career Starters Matrix files do not exist in O*NET 30.2. The spec planned to use these for Stage 3 career branching. Should we (a) use Related Occupations as the fallback, (b) source career transition data from elsewhere (LinkedIn, Census ACS), or (c) defer Stage 3 branching until transition data is found?"
**Status:** UNANSWERED — requires follow-up
**Agent Assumption:** Option (a) — use Related Occupations as the fallback. Related Occupations provides occupational similarity (not actual transitions) but is the best available data within O*NET. The Relatedness Tier column provides useful tiering. Post-hackathon, consider option (b) for more accurate transition data.
**Mandatory DQ Rule:** Write DQ rules for raw.onet_related_occupations as the sole career relationship table. Do NOT write rules for career_changers or career_starters.

### Question 2: Work Context CXP Data Usage
**Question:** "Work Context has 297,676 rows — 81.1% are CXP category-percentage rows showing the distribution of responses across 5 categories. For FutureProof's Burnout boss fight, do you need (a) just the CX point estimates (~49K rows, simpler), (b) the full CXP distributions (297K rows, richer), or (c) both?"
**Status:** UNANSWERED — requires follow-up
**Agent Assumption:** Option (a) for hackathon MVP — CX point estimates are sufficient for scalar burnout indicators. Retain CXP in Bronze and Silver for future enrichment. Gold zone Burnout boss fight should use CX data.
**Mandatory DQ Rule:** Write DQ rules for all scale types (CX, CXP, CT, CTP). Even if Gold zone only uses CX, Bronze and Silver must validate all data.

### Question 3: O*NET Survey Freshness Threshold
**Question:** "O*NET survey dates range from 2004 to 2025. Some occupations have 20-year-old data. Should we (a) use all data regardless of age, (b) flag occupations with data older than a threshold (e.g., 10 years), or (c) exclude very old data?"
**Status:** UNANSWERED — requires follow-up
**Agent Assumption:** Option (b) — flag but do not exclude. All data is retained in Bronze and Silver. Gold zone should include a "survey freshness" indicator. Suggested threshold: flag occupations with most recent survey date before 2016 (10+ years old).
**Mandatory DQ Rule:** Do NOT write a rule that rejects old survey dates. Write an informational rule that counts occupations with survey dates older than 10 years and tracks this count across O*NET releases.

### Question 4: Handling the 29 Partial-Data Occupations
**Question:** "29 occupations have Tasks and Related Occupations but no Work Activities or Work Context. Should these (a) be included in Gold zone products with a 'partial profile' flag, (b) excluded from Gold zone until full data is available, or (c) have their Work Activities/Context estimated from similar occupations?"
**Status:** UNANSWERED — requires follow-up
**Agent Assumption:** Option (a) — include with a "partial profile" flag. These occupations have some useful data (tasks, relationships) even without full activity/context ratings. Excluding them would reduce coverage. Estimation (option c) is risky and should not be done without explicit approval.
**Mandatory DQ Rule:** Write a rule that identifies and counts partial-data occupations. Track this count across releases — if it increases significantly, O*NET may be adding many new occupations without survey data.

### Question 5: Relatedness Tier Mapping to is_primary
**Question:** "The spec defines an is_primary boolean (true for index 1-10, false for 11-20). The actual data has a three-tier Relatedness Tier column (Primary-Short, Primary-Long, Supplemental). Should we (a) capture the three-tier column and derive is_primary from it, (b) replace is_primary entirely with the three-tier column, or (c) capture both?"
**Status:** UNANSWERED — requires follow-up
**Agent Assumption:** Option (c) — capture both. Add relatedness_tier as a new column in the schema. Retain is_primary as derived (Primary-Short or Primary-Long = true, Supplemental = false) for backward compatibility with the spec. The three-tier column provides finer granularity for Stage 3 branching.
**Mandatory DQ Rule:** Write a consistency rule: is_primary must be true when relatedness_tier is "Primary-Short" or "Primary-Long", and false when "Supplemental". Any inconsistency is an ingestor derivation bug.

### Question 6: O*NET Ratings for AI Scoring Methodology
**Question:** "For FutureProof's AI Resilience (RES) stat and AI boss fight, how should O*NET data feed into AI automation scoring? Options: (a) Score individual tasks from Task Statements using an LLM/Karpathy method, (b) Score work activities from Work Activities using their IM/LV profiles, (c) Both, (d) Use an existing AI exposure index."
**Status:** UNANSWERED — requires follow-up
**Agent Assumption:** Option (c) — both. Task Statements provide granular "can AI do this specific task?" inputs. Work Activities provide broader "how human-skill-intensive is this occupation?" context. The combination is more robust than either alone. Specific scoring methodology is outside the scope of raw ingest — this will be defined in the Silver or Gold zone spec.
**Mandatory DQ Rule:** No specific DQ rule for AI scoring methodology. Ensure task text and work activity ratings are preserved with full fidelity in Bronze for downstream consumption.

---

## Assumptions (User-Deferred) — O*NET

All assumptions below were made by @domain-context in the absence of user input. Each carries MEDIUM confidence unless otherwise noted. The @principal-data-architect will review these at the bronze-to-silver zone transition.

| # | Assumption | Basis | Confidence | Risk if Wrong |
|---|-----------|-------|------------|---------------|
| 1 | Related Occupations is the sole career branching data source (Career Changers/Starters unavailable) | Files missing from O*NET 30.2 ZIP; HTTP 404 on all URL variants | HIGH | Medium — if career transition data is critical, an alternative source (LinkedIn, Census) would be needed. Related Occupations provides similarity, not actual transitions. |
| 2 | CX point estimates are sufficient for Burnout boss fight (MVP) | CX provides scalar values; CXP adds distributional detail | MEDIUM | Low — CXP data is retained in Bronze/Silver if richer analysis is needed later. |
| 3 | 93 "All Other"/Military occupations should be filtered in Silver zone | These are residual categories with no O*NET survey data | HIGH | Very low — these are structurally empty by design. |
| 4 | O*NET survey date freshness threshold of 10 years for flagging | Arbitrary but reasonable — occupation characteristics can change significantly over 10+ years | MEDIUM | Low — flagging is informational, not exclusionary. |
| 5 | Non-.00 O*NET codes should be averaged when aggregating to BLS SOC level | Standard approach for hierarchical code aggregation | MEDIUM | Medium — unweighted average treats all O*NET details equally. Employment-weighted would be better but requires external data. |
| 6 | recommend_suppress = "Y" data should be preserved in Bronze, flagged in Silver, excluded from Gold stat calculations | O*NET recommends suppression; preserving gives option to override | HIGH | Low — conservative approach. If suppressed data is later needed, it exists in Bronze. |
| 7 | Three-tier relatedness (Primary-Short/Primary-Long/Supplemental) provides better UX than binary is_primary | Finer granularity enables progressive disclosure in career exploration | MEDIUM | Very low — is_primary is still derivable from the three-tier column. |
| 8 | No PII in O*NET data | All occupation-level aggregates from anonymized DOL surveys | HIGH | Very low — DOL would not publish PII. |
| 9 | Full table replace strategy for O*NET release updates | Each O*NET release (30.0, 30.1, 30.2) is a complete database | HIGH | Low — matches O*NET publication model. |

---

## AI-Ready Considerations (O*NET)
| Consideration | Recommendation | Notes for @mcp-engineer |
|--------------|---------------|------------------------|
| Primary user questions | "What does a [job title] actually do day-to-day?" "What skills do I need for [occupation]?" "How stressful is [occupation]?" "What careers are similar to [occupation]?" "How exposed is [occupation] to AI automation?" | Support occupation lookup by title (fuzzy match on O*NET title) and SOC code. Users will NOT know O*NET-SOC codes — title search is essential. |
| Task-level AI exposure queries | "Which tasks in [occupation] can AI do?" "What percentage of [occupation] tasks are automatable?" | Requires pre-computed AI exposure scores per task (Gold zone). Return individual task scores AND aggregate occupation score. Task descriptions should be included verbatim — they are the atomic evidence for AI exposure claims. |
| Work context / burnout queries | "How many hours do [occupation] workers typically work?" "How stressful is [occupation]?" "What's the work environment like?" | Map specific Work Context elements to user-friendly burnout dimensions. Time Pressure, Duration of Typical Work Week, and Consequence of Error are the highest-value elements for burnout assessment. Return both scalar (CX) and, if requested, distribution (CXP) data. |
| Career exploration / branching queries | "What careers are similar to [occupation]?" "If I'm a [occupation], what else could I do?" | Use Related Occupations with tiered presentation: show Primary-Short first (5 closest), then Primary-Long (5 more), then "Explore more" for Supplemental (10). Include occupation titles and brief descriptions for each suggestion. |
| Cross-source career guidance | "If I study [program], what will my daily work look like?" "Is [occupation] a good career given AI trends?" | Requires joining O*NET (tasks/context) + BLS OOH (salary/growth) + College Scorecard (program outcomes) via SOC/CIP codes. This is the full FutureProof chain. Pre-join in Gold zone for fast retrieval. |
| Context an LLM needs | The LLM must know: (1) O*NET ratings are survey-based averages, not absolute facts; (2) "All Other" occupations have no O*NET data — this is by design, not a data gap; (3) Related Occupations shows similar jobs, not actual career transitions; (4) Some data may be 10+ years old (check survey date); (5) recommend_suppress = "Y" means the rating is unreliable. | Include this as grounding context in every MCP response involving O*NET data. Without it, the LLM will present survey averages as facts and misinterpret missing data. |
| Scale interpretation | IM and LV scales should NOT be averaged together — they measure different things. Always present IM (importance, 1-5) and LV (level/complexity, 0-7) separately. For CX (1-5), translate values: 1="Never/Very Low", 2-3="Sometimes/Moderate", 4-5="Often/Very High". | Pre-compute human-readable labels for scale values in Gold zone. Raw numeric values are not user-friendly. |
| Data completeness disclosure | Always disclose when an occupation has partial data (29 occupations) or no O*NET data (93 occupations). "This occupation does not have detailed task and activity data in O*NET." | Include a data_completeness field in MCP responses: "full" (894 occupations), "partial" (29), "none" (93). |

---

## Confidence Notes (O*NET)

**High confidence:**
- Domain identification (O*NET Content Model / DOL-ETA occupational information) — unambiguous from source URL, file structure, and data patterns
- Career Changers/Starters Matrix files do not exist in O*NET 30.2 — verified via file listing and HTTP 404s
- 93 "All Other"/Military occupations are structurally empty — verified across all child tables
- O*NET-SOC code format (XX-XXXX.XX) — 100% validation across all 5 tables
- Scale type system (IM/LV/CX/CXP/CT/CTP) and their ranges — verified from O*NET Scales Reference and EDA data
- Work Context row count (297,676) is correct despite spec estimate of ~49,000 — CXP/CTP rows account for the difference
- No PII — all occupation-level aggregates from anonymized federal surveys
- Referential integrity across all tables (0 orphans) — verified in EDA
- Related Occupations schema change (Index vs. Related Index column, new Relatedness Tier) — verified from actual file headers

**Medium confidence:**
- 29 partial-data occupations (Tasks + Related but no WA/WC) — count may vary across releases
- 16 occupations with 57 (vs. 338) Work Context rows — likely recently updated, count may change
- CX point estimates sufficient for MVP Burnout boss fight — depends on product requirements
- Related Occupations as adequate fallback for Career Changers/Starters — semantics differ (similarity vs. transitions)
- Survey freshness threshold of 10 years for flagging — arbitrary but reasonable
- Aggregation strategy for non-.00 O*NET codes (unweighted average) — employment-weighted would be better

**Low confidence / Needs human validation:**
- AI automation scoring methodology (how O*NET tasks/activities feed into RES stat) — outside raw ingest scope, to be defined in Silver/Gold spec
- Whether Career Changers/Starters data was consolidated into Related Occupations or simply discontinued — O*NET documentation unclear
- Optimal tiering of Related Occupations for Stage 3 UX (Primary-Short vs. Primary-Long split at index 5 vs. some other threshold)
- Long-term strategy for career transition data (Related Occupations vs. external sources like LinkedIn)
