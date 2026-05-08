# Domain Context: Higher Education Outcomes
**Date:** 2026-04-05
**Agent:** @domain-context
**Based On:** governance/eda/raw-college-scorecard-eda.md (2026-04-05)
**Data Sources:** college_scorecard (U.S. Department of Education College Scorecard — Field of Study), bls_ooh (Bureau of Labor Statistics — Employment Projections / Occupational Outlook Handbook), onet (O*NET 30.2 Database — Task-Level Occupation Data), karpathy_ai_exposure (Karpathy AI Exposure Scores — LLM-generated occupation-level AI reshaping estimates), bea_rpp (BEA Regional Price Parities — state-level cost-of-living index, national=100), anthropic_economic_index (Anthropic Economic Index v2 — empirical Claude usage observations mapped to O*NET tasks / SOC occupations, release 2025-03-27)
**Confidence:** High

---

## Revision History

| Date | What Changed | Reason |
|------|-------------|--------|
| 2026-04-05 | Initial version | First domain context synthesis from EDA report |
| 2026-04-07 | Added BLS OOH section | Second data source — BLS Employment Projections (SOC-coded occupations) |
| 2026-04-07 | Added O*NET section | Third data source — O*NET 30.2 task/activity/context/pathway data. Documents missing Career Changers/Starters files, scale type system, 93 "All Other"/Military gap, and SOC code format bridging to BLS. |
| 2026-04-09 | Added Karpathy AI Exposure section | Fourth data source — LLM-generated AI exposure scores for 342 BLS occupations. Completes the RES stat and Fight AI boss in the FutureProof pentagon. |
| 2026-04-10 | Added BEA Regional Price Parities section | Fifth data source — state-level cost-of-living index (50 states + DC, annual snapshot, national=100). Enables salary purchasing power adjustment in the frontend and the Tier 3 Fight Location Lock boss. Does NOT join to other sources by SOC/CIP — joins at query time by the student's selected state. |
| 2026-04-14 | Added College Scorecard Institution-Level section | Sixth data source — institution-level cost of attendance, net price, tuition, room/board. Joins to existing field-of-study data on UNITID (91.9% coverage). Enables true ROI formula using net_price instead of debt_median. Source-specific context document: `domain/raw-ingest-college-scorecard-institution-context.md`. Key EDA corrections: row count is 3,039 (not ~6,500), COA coverage 73.5% (not 90%), negative net prices are legitimate, quintile monotonicity unreliable at adjacent pairs. All conditional agents (entity-resolver, pii-scanner, temporal-modeler) can be SKIPPED. |
| 2026-04-16 | Added Anthropic Economic Index section | Seventh data source — Anthropic's empirical observations of Claude usage mapped to O*NET tasks / SOC occupations (release 2025-03-27, CC-BY 4.0). Complements Karpathy's theoretical AI exposure with observed adoption. Grain: `(task_id, soc_code)` Bronze, `soc_code` Silver. Aggregation is SUM (not mean) with even `pct / N` split across multi-SOC tasks to preserve the 100% global-share invariant. SOC coverage revised from ≥80% to ≥60% (actual 61.3% — gaps are in manual/physical occupations Claude traffic doesn't touch, not an ingestor defect). Extends `consumable.ai_exposure` with `observed_exposure_pct` and `automation_pct`. Blocks S4 (`three-signal-ai-exposure-composite`). |
| 2026-04-30 | Added IPEDS Finance section | Ninth data source — IPEDS Finance Survey (F1A public/GASB + F2 private nonprofit/FASB + F3 for-profit) UNIONed across institutional control, joined to **EFIA** (12-Month Instructional Activity, NOT EFFY which is headcount) on UNITID for `total_fte_enrollment = COALESCE(FTEUG,0)+COALESCE(FTEGD,0)+COALESCE(FTEDPP,0)`, filtered to 4-year-bachelor's-or-above via HD `ICLEVEL=1 AND HLOFFER>=5`. FY23 (provisional, released Sep 2024) is the operative cycle — FY24 not yet released by NCES (HTTP 404 on F2324 bulk URLs as of 2026-04-30). All 8 v1.3-locked column codes byte-verified against FY23 dictionaries (`F1C011/F1C071/F1H02`, `F2E011/F2E061/F2H02`, `F3E011/F3E03C1`); pre-2014-15 belief that F3 omits institutional support is REFUTED — `F3E03C1` is 100% non-null on FY23. Post-filter row count = **2,675** (NOT 5,000–8,000 — RAW-IPF-001 needs revision to `2,500–3,200`); form mix F1A 30.6% / F2 59.0% / F3 10.4%; F3 endowment 100% structurally NULL (no F3H family); imputation prevalence ≤1.22% on every field (§2 Decision #8 well-calibrated). UNITID overlap with `bronze.college_scorecard_institution` = 98.0% of finance / 86.2% of scorecard. Three ingestor configuration gates (fiscal_year=2023, F3 col overrides, EFIA prefix/suffix/dedup overrides) AND a code change (three-column NULL-safe FTE sum) required before promote. Powers consumable `marketing_ratio` and `endowment_per_fte` planks of `consumable.institution_aura`. |
| 2026-04-30 | Re-finalized IPEDS Finance section against actually-landed FY2022 bronze | Supersedes the prior 2026-04-30 IPEDS Finance entry. The bronze table actually landed against **FY2022** (academic year 2021-22) — NCES had not yet published FY24 finance files at ingest time, so the spec's working-assumption FY24 / earlier draft's FY23 cycles do not correspond to live data. Section rewritten against `governance/eda/raw-ingest-ipeds-finance-eda.md` (2,683 rows, snapshot `982081695100705470`). Updates the recap edge-cases table to FY2022-measured values: 2,683 rows (vs. earlier draft's 2,675), form mix F1A 29.9% / F2 59.4% / F3 10.7%, CON-IFP-008 overlap 90.39% (tight-pass at threshold — add P2 watch-line at 88%). **Surfaces a meaningful prior omission:** endowment imputation prevalence is 25-31% on F1A/F2 (NCES bureau-imputed via prior-year × market-return), not the ≤1.22% the prior entry conflated across all fields. Keeps §2 Decision #8 (accept imputed) as the v1.3 policy, recommends `endowment_value_provenance` flag column for v1.4. Adds plain-English definitions of the four bronze fields, the structural F3-endowment-NULL invariant, the public-system-administrative-office outlier pattern (real IPEDS entities, not data errors), and the cycle-as-runtime-parameter clarification. Cycle vintage advances at the next NCES publication (~Sep 2026 for FY24) by parameter change only. |
| 2026-04-30 | Finalized EADA section | Eighth data source — Equity in Athletics Disclosure Act institution-level athletic finance reporting. Replaces @bs:data-analyst's provisional 2026-04-30 stub with the canonical synthesis. Captures three-endpoint SPA acquisition pattern; the corrected file model (institution totals live in `InstLevel.xlsx`, separate from per-team `Schools.xlsx`, no in-pipeline filter needed); the corrected lowercase `unitid` / `institution_name` and uppercase `GRND_TOTAL_EXPENSE` / `GRND_TOTAL_REVENUE` / `RECRUITEXP_TOTAL` column names; sentinels (`-1`, `-2`, blank → NULL); 74.5% UNITID overlap with `bronze.college_scorecard_institution` (calibrates BSE-EAD-009 down from 95%); revenue ≈ expense structural identity at the grand-total level; 17.8% real-zero recruiting rate; **open architectural question** on whether per-FTE derivations should use EADA's in-file `EFTotalCount` instead of cross-source LEFT JOIN to `base.ipeds_finance` (covers the 521 EADA institutions missing from IPEDS-side join surface). Also adds forward-looking **aura-score** domain context: neutral brand-gravity signal composed of `endowment_per_fte` + `marketing_ratio` + `athletic_spend_per_fte`; `athletic_subsidy_ratio` deliberately excluded as normative-overlap with ROI/ERN; versioned via `aura_score_version`. PII reaffirmed as none (institution-level public data). Lands `bronze.eada` in the source registry. |

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

---

## Karpathy AI Exposure

**Date Added:** 2026-04-09
**Based On:** governance/eda/raw-karpathy-ai-exposure-eda.md (2026-04-09)
**Source:** Andrej Karpathy's `karpathy/jobs` GitHub repository — `scores.json` + `occupations.csv`
**User Familiarity:** Familiar — knows the dataset basics
**Confidence:** High (domain and data structure unambiguous; scoring methodology confidence is Medium due to LLM-generation)

### Source Methodology

Karpathy scored 342 BLS occupations for AI exposure using a structured LLM pipeline:

1. **Input:** Full BLS Markdown occupation descriptions (from the Occupational Outlook Handbook)
2. **Model:** Gemini Flash via OpenRouter
3. **Rubric:** Structured 0-10 scale measuring "how much will AI reshape this occupation" — NOT a job-loss predictor. Considers both direct automation and indirect productivity effects.
4. **Key heuristic:** If the job can be done entirely from a home office on a computer, exposure is 7+.
5. **Output:** Integer score (0-10) plus a 2-3 sentence rationale per occupation.
6. **Effort level:** Self-described as "a saturday morning 2 hour vibe coded project."

The scoring was a single LLM run — no averaging across multiple runs, no human calibration, no inter-rater reliability testing. The scores are directionally useful estimates, not empirical measurements.

### Domain Vocabulary

| Term | Definition | Source | Notes for @data-steward |
|------|-----------|--------|------------------------|
| exposure_score | 0-10 integer measuring how much AI will reshape an occupation. Higher = more exposed to AI-driven change. Does NOT predict job elimination — predicts reshaping of work tasks and workflows. | Karpathy methodology (project-specific) | Propose. Emphasize "reshaping not replacement" in business term definition. |
| slug | Kebab-case occupation identifier from Karpathy's repo (e.g., "financial-analysts"). Unique per occupation. The grain of the raw table. | Karpathy repo (project-specific) | Propose. Not a standard identifier — maps to SOC codes for integration. |
| category | Karpathy's BLS category grouping (25 categories, e.g., "business-and-financial", "healthcare"). Derived from BLS occupation groups but not a 1:1 mapping to SOC major groups. | Karpathy repo (project-specific) | Propose. Document that this is not standard BLS taxonomy. |
| rationale | 2-3 sentence LLM-generated explanation of the exposure score. All unique, substantive, grammatically complete. Length: 297-587 chars, mean 412 chars. | LLM output (project-specific) | Propose. Carry forward as metadata for MCP context. |
| stat_res | FutureProof's AI Resilience stat, derived by inverting exposure_score: `MIN(11 - exposure_score, 10)`. Range 1-10 where 10 = most resilient to AI change. | FutureProof project (project-specific) | Propose. This is a Gold-zone derived metric, not in the raw data. |
| boss_ai_score | The difficulty rating for the "Fight AI" boss encounter in the FutureProof gauntlet. Directly equals the raw exposure_score (no transformation). | FutureProof project (project-specific) | Propose. This is a Gold-zone derived metric, not in the raw data. |

### SOC Taxonomy and Coverage

**Overall SOC coverage: 84.8% (290 of 342 rows have SOC codes).**

| SOC Type | Count | Percentage | BLS OOH Match |
|----------|-------|------------|---------------|
| Detailed codes (XX-XXXX) — exact BLS match | 244 | 71.3% of total | Direct match |
| Broad codes (XX-XXX0) — roll-up codes | 46 | 13.5% of total | Prefix match only; no direct match in BLS OOH detailed code table |
| Null SOC | 52 | 15.2% of total | No match possible without resolution |

**Notes for @entity-resolver:**
- **Null SOC resolution strategy:** Attempt title-match against BLS OOH `occupation_title` in Silver zone. User confirmed this approach. Occupations with null SOC are concentrated in transportation-and-material-moving (54.5% null), installation-maintenance-and-repair (33.3%), production (31.3%), and computer-and-information-technology (30.0%).
- **Broad code propagation:** Propagate Karpathy exposure score from broad code (XX-XXX0) to all detailed codes (XX-XXXX) under the same prefix. User confirmed: maximize coverage. All 46 broad codes have at least one detailed BLS match under the same prefix.
- After both resolution strategies, potential BLS OOH coverage could reach 595 of 832 occupations (71.5%).
- Zero duplicate SOC codes in the raw data. Zero malformed SOC codes.

### Limitations and Known Biases

| Limitation | Description | Impact | Downstream Handling |
|-----------|-------------|--------|-------------------|
| LLM-generated scores | Scores are estimates from a single Gemini Flash run, not empirical measurements. No averaging, no calibration, no inter-rater reliability. | Scores are directionally useful but carry unknown error margins. | Acknowledge in metadata. User confirmed: accept as-is for hackathon MVP. |
| Score-7 cluster | 70 occupations (20.5%) scored exactly 7 — nearly double any other score bucket. The LLM appears to have a "default high" heuristic for computer-based office work. | Creates a "gravity well" that may reduce discriminative power among office/digital occupations. | Document as methodology artifact. No special downstream handling. Notes for @dq-rule-writer: this is NOT a data quality issue — it is expected LLM scoring behavior. Do not flag as anomaly. |
| Self-referential bias | An LLM is scoring jobs for LLM replaceability — the scorer has inherent bias about its own capabilities. | May systematically over- or under-estimate exposure for AI-adjacent occupations. | User confirmed: acknowledge in metadata, no special downstream handling. Notes for @dq-rule-writer: no corrective rule needed. |
| No demand elasticity | Scores do not account for whether AI-driven productivity gains will increase demand for the occupation (Jevons paradox). | A high score may overstate risk for occupations where AI makes them more valuable (e.g., software developers). | Carry as metadata caveat. Important context for MCP/LLM serving. |
| No regulatory barriers | Scores do not account for regulatory, licensing, or social barriers to AI adoption. | Healthcare, legal, and financial occupations may be scored higher than real-world adoption timelines justify. | Carry as metadata caveat. |
| No social preferences | Scores do not account for human preference for human service (e.g., therapy, childcare, pastoral care). | Some high-scoring occupations may resist AI replacement due to social expectations. | Carry as metadata caveat. |
| Score 0 absent | Actual range is 1-10, not 0-10 as rubric allows. No occupation was scored as having zero AI exposure. | The `stat_res` inversion formula `MIN(11 - exposure_score, 10)` produces range 1-10 for input range 1-10. The cap at 10 is defensive code for a 0-input case that does not currently exist. | Notes for @dq-rule-writer: DQ rule range should remain 0-10 (rubric allows it), but effective range is 1-10. |

### FutureProof Integration

This dataset completes the fifth stat in the FutureProof pentagon and the fifth boss fight in the gauntlet:

| FutureProof Concept | Derivation | Range | Interpretation |
|--------------------|-----------|-------|----------------|
| stat_res (AI Resilience) | `MIN(11 - exposure_score, 10)` | 1-10 | 10 = highly resilient to AI change, 1 = heavily reshaped by AI |
| boss_ai_score (Fight AI) | Direct: `exposure_score` | 1-10 | 10 = hardest boss (most AI exposure), 1 = easiest (least exposed) |

**User Said:** "stat_res and boss_ai_score are sufficient for hackathon MVP" (session 2026-04-09)
**Agent Action:** No additional derived metrics documented. If post-hackathon refinement adds metrics (e.g., exposure-weighted career path scores, AI resilience percentile ranks), this section should be updated.

**Pentagon completion:** With this data source, all 5 stats are populated: stat_earnings, stat_demand, stat_skills, stat_flex, and stat_res. The boss gauntlet is also complete: 5 of 5 boss fights have scoring data.

### Cross-Validation Results

**Wage alignment with BLS OOH: perfect.** For all 241 rows with both a direct SOC match and non-null wage data, Karpathy's `median_pay_annual` exactly equals our BLS OOH `median_annual_wage` ($0 difference on every row). This confirms Karpathy used the same BLS data snapshot as our pipeline. No data vintage mismatch.

**Exposure-pay correlation:** Moderate positive (Pearson r=0.387). Higher-paid occupations tend to be more AI-exposed, consistent with the "computer-based office work" heuristic. Average pay climbs from $50,576 (score 1) to $97,558 (score 8), then drops at scores 9-10 (routine digital tasks, not high-skill knowledge work).

**Exposure-education correlation:** Strong positive trend. Bachelor's degree occupations average 6.9 exposure; no-credential occupations average 2.8. Exception: doctoral occupations average only 5.1 (physicians/surgeons have moderate exposure despite high education).

### Temporal Strategy

**User Said:** "Event-driven refresh. Refresh when Karpathy updates or when we re-score with Gemma post-hackathon. No fixed cadence." (session 2026-04-09)

| Pattern | Description | Notes for @temporal-modeler |
|---------|-------------|---------------------------|
| Static snapshot | Single LLM scoring run. Not time-series. No temporal dimension in the data itself. | Model as a static reference table, not a temporal fact table. |
| Event-driven refresh | Re-ingest when Karpathy updates scores or when project re-scores with a different model (e.g., Gemma). | No SLA on refresh cadence. No need for slowly-changing dimension handling at hackathon MVP. |
| No amendment pattern | Scores do not get corrected or amended — the entire dataset is replaced on refresh. | Full-refresh strategy. No merge/upsert logic needed. |

### PII Assessment

| PII Type | Present? | Sensitivity | Notes for @pii-scanner |
|----------|----------|-------------|----------------------|
| Personal names | No | N/A | All data is occupation-level aggregate. No individual workers, students, or identifiable persons. |
| SSN / Tax ID | No | N/A | Not applicable. |
| Location data | No | N/A | Occupations are national-level, not geolocated. |
| Health records | No | N/A | Not applicable. |
| Financial records (individual) | No | N/A | Wage data is BLS median aggregates, not individual compensation. |

**Conclusion:** No PII. This is entirely occupation-level aggregate data sourced from public BLS descriptions and scored by an LLM. No individual-level data exists anywhere in the pipeline for this source.

### Regulatory & Compliance Context

| Regulation | Relevance | Key Requirements | Notes for @bcbs239-auditor |
|-----------|-----------|-----------------|---------------------------|
| None directly applicable | LLM-generated scores on public BLS data do not trigger HIPAA, FERPA, SOX, GDPR, or PCI DSS. | N/A | No compliance assessment needed for this source in isolation. However, when joined with College Scorecard (FERPA-adjacent) data in Gold zone, the combined product should be reviewed. |

**Note:** If FutureProof were used for employment decisions (hiring, compensation), AI-generated occupation scores could raise concerns under EEOC guidance on automated employment decision tools. Current use case (student career guidance) does not trigger this, but document as a risk if the product scope expands.

### Edge Cases for DQ

| Edge Case | Description | Impact | Notes for @dq-rule-writer |
|-----------|-------------|--------|--------------------------|
| Null SOC codes | 52 of 342 rows (15.2%) have no SOC code. | These rows cannot join to BLS OOH or O*NET without title-match resolution in Silver. | Set SOC coverage threshold to >= 84% (warn). Do NOT set to 95% — EDA confirmed 84.8% actual. |
| Broad SOC codes | 46 of 290 non-null SOC codes (15.9%) are broad codes (XX-XXX0) that don't exist in BLS OOH detailed code table. | Silver must propagate scores to detailed codes. | Warn if broad code percentage exceeds 20% of non-null SOC codes. |
| Score 7 overrepresentation | 70 rows (20.5%) score exactly 7. | LLM scoring artifact, not a data quality issue. | Do NOT flag this as an anomaly. Document as expected behavior. |
| "See How to Become One" education | 36 rows (10.5%) have this BLS placeholder instead of a real education level. | Not an error — BLS uses this when education requirements vary widely. | Allow as valid value. Do not count as null. |
| "None" vs "No formal educational credential" | 1 row has "None" (Military) vs 21 rows with "No formal educational credential." | Possible inconsistency but likely legitimate (military has its own training pipeline). | Flag for manual review. Low priority. |
| Military row | 1 row with null SOC, null wage, null employment, null education. Structurally incomplete. | Will not join downstream. Minimal data. | Allow — this row is a known BLS edge case. Do not count against coverage thresholds. |
| BLS wage cap | 1 row at $239,200 (BLS top-coding). | Expected BLS behavior, not a data issue. | Allow as valid. Do not flag as outlier. |

### External Data Opportunities

| External Source | What It Adds | Join Key | Notes for @insight-manager |
|----------------|-------------|----------|---------------------------|
| Re-scoring with Gemma or other open model | Reduces single-model bias. Enables score averaging or confidence intervals. | Same slug/SOC key | User mentioned post-hackathon. Would require running the same BLS descriptions through a different LLM. |
| O*NET task-level data | Empirical task decomposition that could validate or refine LLM exposure scores. | SOC code (O*NET-SOC to BLS SOC bridging already documented) | Already in pipeline. Gold zone could compare LLM scores vs. task-level automation potential. |
| Academic AI exposure indices | Papers like Felten et al. (2023), Eloundou et al. (2023) provide alternative exposure scores based on task-AI capability matching. | SOC code | Would enable cross-validation of Karpathy scores against peer-reviewed research. Post-hackathon priority. |

### Concept Mapping Guidance

| Source Code Pattern | Maps To | Confidence | Notes for @cde-tagger |
|--------------------|---------|------------|----------------------|
| exposure_score (raw) | AI Exposure Score | Exact | Raw LLM score, 0-10 integer. Carry as-is to Silver. |
| exposure_score (inverted) | AI Resilience (stat_res) | Derived | Gold-zone derivation: `MIN(11 - exposure_score, 10)`. Not a CDE — project-specific metric. |
| exposure_score (direct) | Boss AI Difficulty (boss_ai_score) | Derived | Gold-zone alias: `exposure_score` renamed. Not a CDE — project-specific metric. |
| soc_code | Standard Occupational Classification | Exact | SOC 2018 format (XX-XXXX). Standard BLS taxonomy. Auto-approve as CDE. |
| median_pay_annual | Median Annual Wage | Exact | BLS-sourced, identical to our BLS OOH values. Cross-validates perfectly. |
| category | Karpathy Occupation Category | Project-specific | 25 categories. Not a standard taxonomy. Do NOT map to SOC major groups — close but not 1:1. |

### AI-Ready Considerations

| Consideration | Recommendation | Notes for @mcp-engineer |
|--------------|---------------|------------------------|
| User questions about AI exposure | Expose stat_res and boss_ai_score through MCP. Common queries: "How exposed is [occupation] to AI?", "What careers are most AI-resilient?", "Should I worry about AI replacing [career]?" | Return both the score AND the rationale text. The rationale provides crucial context that prevents misinterpretation of the numeric score. |
| Methodology caveats | Always include methodology caveats when serving AI exposure data. | Include in MCP response metadata: "Scores are LLM estimates (Gemini Flash), not empirical measurements. A high score indicates reshaping, not job elimination." |
| Score interpretation | Users will conflate "AI exposure" with "AI will take my job." The data does not support that interpretation. | MCP responses should frame scores in terms of "how much your work will change" not "how likely you are to lose your job." |
| Rationale text | The `rationale` field is the single most valuable field for LLM-to-user communication. | Serve rationale alongside scores. It explains WHY an occupation scored as it did, which is more useful than the number alone. |

### Assumptions (User-Deferred)

No user-deferred assumptions for this source. The user provided direct answers on all critical questions:
- **Concept list:** stat_res and boss_ai_score confirmed as sufficient for MVP.
- **Data quality approach:** Accept scores as-is; directionally useful despite LLM bias.
- **SOC resolution:** Title-match for nulls, propagate broad codes to detailed codes.
- **Temporal strategy:** Event-driven refresh, static for hackathon.
- **Self-referential bias:** Acknowledge in metadata, no special handling.

### Confidence Notes

**High confidence:**
- Domain identification (AI labor market impact / LLM-generated exposure scores) — unambiguous from source, methodology, and data structure
- SOC coverage at 84.8% — verified in EDA, all format validations pass
- Wage cross-validation is perfect ($0 diff across 241 rows) — confirms data vintage alignment with BLS OOH
- No PII — entirely occupation-level aggregate data from public BLS sources
- Score distribution (1-10 range, mode at 7, mean 5.31) — verified in EDA
- 342 rows, all slugs unique, zero duplicates — grain integrity confirmed

**Medium confidence:**
- Title-match strategy for null SOC resolution — feasible but match rate unknown until Silver implementation. Some Karpathy titles may not align with BLS OOH titles exactly (e.g., combined occupation groups).
- Broad code propagation — applying one score to multiple detailed occupations assumes uniform exposure within the occupation group, which may not hold for all 46 broad codes.
- Score-7 cluster as "methodology artifact" vs. "real signal" — we cannot distinguish whether 7 genuinely describes 20.5% of occupations or whether the LLM defaults to 7 when uncertain.

**Low confidence / Needs validation post-hackathon:**
- Whether Karpathy will update scores or if the dataset is permanently static
- Optimal strategy for post-hackathon re-scoring (which model, same rubric or improved rubric, averaging vs. replacement)
- Whether demand elasticity, regulatory barriers, and social preferences should be incorporated as score adjustments (user deferred to post-hackathon)

---

## BEA Regional Price Parities

**Date Added:** 2026-04-10
**Based On:** governance/eda/raw-bea-rpp-eda.md (2026-04-10)
**Source:** U.S. Bureau of Economic Analysis (BEA), Regional Economic Accounts — Regional Price Parities by State, All Items (table SARPP, `LineCode=1`, `Year=2024`, `GeoFips=STATE`)
**Spec:** docs/specs/raw-ingest-bea-rpp.md
**Confidence:** High (domain, methodology, grain, and integration model are unambiguous; individual row values are a mix of spec-verified and primary-agent estimates — see Data Provenance Caveat below)

### Domain Identification

**Domain:** U.S. macroeconomic / regional cost-of-living reference data
**Sub-domain:** BEA Regional Price Parities (state-level, All Items, annual)
**Description:** Regional Price Parities (RPPs) measure differences in price levels across geographic areas for a given year, expressed as a percentage of the overall U.S. national price level. BEA sets the national average to **100.0** by construction, so an RPP of 110.7 (California 2024) means the local price level is 10.7% above the national average and an RPP of 86.9 (Arkansas 2024) means it is 13.1% below. BEA publishes RPPs for All Items, Goods, Services (Rents), and Services (Other); this dataset ingests the **All Items** index only. RPPs are the BEA's authoritative measure of regional purchasing power and are the standard input to any analysis that adjusts wage, income, or salary figures for local cost of living.

### Why It Matters to FutureProof

RPPs power FutureProof's **"What does this salary mean where you live?"** feature. Every salary figure surfaced to a student — median wages from BLS OOH, earnings from College Scorecard — is a *national* number. Without an RPP adjustment, a $65K median salary shown to a student in California (RPP 110.7) and a student in Iowa (RPP 87.8) tells both of them the same story, but the lived experience of that salary differs by ~26 percentage points of purchasing power. The RPP table lets the MCP tools and frontend translate national salary figures into local-purchasing-power equivalents via the simple formula `local_pp = national_salary × (100.0 / rpp_all_items)`.

RPPs also unlock the **Fight Location Lock** boss (PRD Tier 3 stretch). The boss tests whether a career's national-level salary actually provides a good life in the student's home state, combining wage, RPP, and (eventually) geographic concentration of the industry. For the hackathon MVP, the RPP reference table alone is sufficient to drive the frontend purchasing-power display; the full boss depends on future BLS geographic wage data.

### Grain and Taxonomy

- **Grain:** One row per U.S. geographic entity. **51 rows** total: 50 states + District of Columbia. No metro areas, no counties, no territories, no sub-national regions. No sub-components (Goods / Services / Rents are filtered out at ingest — we keep only LineCode=1, All Items).
- **Primary entity:** U.S. state (plus DC).
- **Canonical identifier:** 2-digit ANSI/FIPS state code, zero-padded string (e.g., `"06"` California, `"19"` Iowa, `"11"` District of Columbia). DC is included at FIPS 11. Canonical gaps in the FIPS sequence (03, 07, 14, 43, 52) are intentional — those codes were never assigned.
- **Secondary identifiers (derived in Silver):** 2-letter USPS state abbreviation (`CA`, `IA`, `DC`), full state name (`California`, `Iowa`, `District of Columbia`), and Census region (`Northeast`, `Midwest`, `South`, `West`).
- **Cadence:** **Annual snapshot.** BEA publishes new RPPs each February for the prior calendar year. Current load is **data_year = 2024** (released February 2026). There is no within-year variation; a single `data_year` is the only temporal dimension in the table.
- **Size:** Trivial (~5 KB raw, 51 rows × 8 columns).

### Domain Vocabulary

| Term | Definition | Source | Notes for @data-steward |
|------|-----------|--------|------------------------|
| Regional Price Parity (RPP) | BEA index measuring the price level of goods and services in a geographic area relative to the U.S. national average (base = 100.0). Published for All Items, Goods, Services (Rents), and Services (Other). | BEA Regional Economic Accounts (external standard) | Auto-approve. External standard; align definition with BEA methodology guide. Cross-reference BT-098. |
| All Items RPP | The composite RPP across goods and services. The single index used for cost-of-living comparison across states. The only line code (`LineCode=1`) this pipeline ingests. | BEA (external standard) | Auto-approve. External standard. |
| National Baseline (100.0) | BEA construction: the population-weighted U.S. average is fixed at exactly 100.0. No state equals 100.0 exactly because it is a construct, not a state. A simple arithmetic mean of state RPPs lands near but not at 100 (observed 96.98 in EDA, expected for unweighted state mean). | BEA methodology | Auto-approve. |
| Purchasing Power Multiplier | Derived field: `100.0 / rpp_all_items`. The factor by which a national salary is multiplied to express local purchasing power. California: 0.9034 (salary buys 90.3% as much). Iowa: 1.1390 (salary buys 113.9% as much). Range observed: ~0.90–1.15. | FutureProof-derived (Silver zone) | Propose. Cross-reference BT-099. |
| Cost Tier | Gold-zone categorical classification of states into `very_high` / `high` / `average` / `low` / `very_low` based on RPP thresholds at 108 / 103 / 97 / 91. | FutureProof-derived (Gold zone) | Propose. Project-specific enum; document thresholds in business glossary. |
| GeoFips | BEA's name for the ANSI/FIPS geographic identifier column. 2-digit zero-padded string at the state level. | BEA API schema | Rename to `state_fips` in Silver. |
| LineCode | BEA's sub-component selector within table SARPP. `1` = All Items, `2` = Goods, `3` = Services (Rents), `4` = Services (Other). This ingest filters to `LineCode=1` only. | BEA API schema | Do not expose; internal to ingest. |

### Taxonomy / Classification Systems

| System | Description | Authority | Coverage in Data |
|--------|-------------|-----------|-----------------|
| ANSI/FIPS state codes | 2-digit numeric state identifiers (01 = AL through 56 = WY, plus 11 = DC). | U.S. Census Bureau / NIST FIPS PUB 5-2 (retired, now ANSI INCITS 38-2009) | 51 / 51 rows (100%). All canonical state FIPS present; deliberate scheme gaps at 03, 07, 14, 43, 52. |
| USPS state abbreviations | 2-letter state codes (AL, AK, AZ, ..., WY, DC). Derived in Silver from FIPS code. | U.S. Postal Service | 51 / 51 (100% after Silver derivation). |
| U.S. Census regions | Four-region grouping: Northeast (9), Midwest (12), South (17), West (13). Derived in Silver from FIPS code. | U.S. Census Bureau | 51 / 51 (100% after Silver derivation); all 4 regions represented. |

### Enumerated Values with Business Meaning

| Field | Values | Meaning |
|-------|--------|---------|
| source_method | `bea_api`, `csv_cache` | Provenance of the row. `bea_api` = live BEA API call succeeded; `csv_cache` = fell back to cached CSV at `data/raw/bea_cache/bea_rpp_2024.csv`. Current load is 100% `csv_cache`. DQ must use `IN ('bea_api','csv_cache')`, NOT `= 'bea_api'`. |
| census_region (Silver) | `Northeast`, `Midwest`, `South`, `West` | Standard U.S. Census region. DC is classified as `South` per Census convention, even though its RPP (109.9) is behaviorally Northeast-like (see Known Quirks). |
| cost_tier (Gold) | `very_high`, `high`, `average`, `low`, `very_low` | Project-specific RPP bucketing. Thresholds: `>=108` / `>=103` / `>=97` / `>=91` / `else`. Used by the frontend and the Fight Location Lock boss. |

### Entity Types

#### Primary Entities

| Entity Type | Identifier Field(s) | Example | Notes for @entity-resolver |
|-------------|---------------------|---------|---------------------------|
| U.S. State (including DC) | `geo_fips` (raw) → `state_fips` (Silver) | `"06"` = California, `"11"` = District of Columbia | **Trivial resolution.** State FIPS is a canonical, universally-recognized identifier assigned by ANSI/NIST. There is no fuzzy matching, no alias reconciliation, no temporal identity drift. `geo_fips` ↔ `geo_name` is a 1:1 bijection in the EDA. The Silver zone simply validates the FIPS code and derives USPS abbreviation and Census region from a static lookup. **@entity-resolver can SKIP this source** — the only "resolution" work is the static FIPS → abbreviation and FIPS → region lookups already specified in the Silver spec, which is a derivation task, not an entity-resolution task. Document the skip decision with rationale: "State FIPS is a canonical identifier with 100% coverage and zero ambiguity; no resolution work required." |

#### Entity Lifecycle Events

**None applicable.** U.S. states and DC do not merge, split, rename, or otherwise change identity on any timescale relevant to this pipeline. The set of 50 states + DC has been stable since 1959 (Hawaii admission). There are no entity lifecycle events for @entity-resolver to model.

### Temporal Patterns

#### Valid Time

| Pattern | Description | Notes for @temporal-modeler |
|---------|-------------|---------------------------|
| Annual snapshot | BEA publishes one RPP per state per calendar year. This ingest loads `data_year = 2024` only; all 51 rows carry the identical year. There is no within-year variation, no monthly/quarterly cadence, no intra-year revisions published mid-year. | **Model as a static reference table keyed by `state_fips`**, with `data_year` as a load-time column, not a time-series dimension. No slowly-changing-dimension handling required for the hackathon MVP. @temporal-modeler can **SKIP complex temporal modeling** for this source. Document the skip: "Single-year snapshot reference data; `data_year` is the only temporal dimension and is constant across the table. No bitemporal modeling, no SCD2, no effective-dating required." |
| Annual refresh cadence | Each February, BEA publishes the prior calendar year's RPPs. When we refresh, the entire 51-row table is replaced; individual state values are not amended. | On refresh, increment `data_year` (2024 → 2025 → ...) and update the DQ `data_year = N` rule to match. If the product needs to compare RPP trends across years post-hackathon, switch to an append-with-year strategy and partition by `data_year`. Not required for MVP. |
| Batch stamp, not event time | All 51 rows share identical `ingested_at` and `load_date` values because the load is a single batch. These columns are load-batch identifiers, not per-row event times. | Do not model `ingested_at` as an event-time column. Treat it as provenance metadata. |

#### Amendment / Correction Patterns

**None observed.** BEA does occasionally revise historical RPP series when it updates its underlying price index methodology (typically every ~5 years), but within a given publication year the data is static. A revision, when it occurs, replaces the entire historical series rather than emitting per-row amendments. For this pipeline, revisions are handled via full refresh — no merge, no upsert, no correction-tracking columns needed.

### Data Provenance Caveat (CRITICAL for Downstream Agents)

**8 of 51 rows are spec-verified; 43 of 51 rows are primary-agent estimates.**

The @primary-agent ingestor attempted the live BEA API call but fell back to the CSV cache (`source_method = 'csv_cache'` on all 51 rows). The cache contains **8 spec-verified 2024 RPP values** (from the public BEA February 2026 release, as documented in the spec) and **43 primary-agent-generated plausible placeholder values** filling in the remaining states until a live BEA API load succeeds.

**Verified (8 rows, authoritative):**

| FIPS | State | RPP |
|------|-------|-----|
| 05 | Arkansas | 86.9 |
| 06 | California | 110.7 |
| 11 | District of Columbia | 109.9 |
| 15 | Hawaii | 110.0 |
| 19 | Iowa | 87.8 |
| 28 | Mississippi | 87.0 |
| 34 | New Jersey | 108.8 |
| 40 | Oklahoma | 87.8 |

**Estimated (43 rows, placeholder):** Every other state. Observed range of estimates: [88.2, 107.9]. The estimates are directionally sensible (high-cost coastal states high, rural interior low) and internally consistent (no NaNs, no outliers, all within the [80.0, 130.0] DQ guardrails), but **they are not BEA-authoritative values** and will shift when the live API load succeeds and replaces them with real 2024 figures.

**Implications for downstream agents:**
- **@dq-rule-writer:** All DQ rule thresholds MUST hold simultaneously in (a) the current estimates-in-place state and (b) a future verified state. The rules in the EDA report are already designed this way — do not tighten them further based on current observed values. In particular, do NOT pin `source_method = 'bea_api'`, do NOT write a uniqueness rule on `rpp_all_items` (IA and OK legitimately tie at 87.8), and do NOT write tight per-state spot checks beyond the 2 the spec specifies (CA and AR, which are verified).
- **@data-contract-author:** The data contract's quality tier should be marked "High (for the 8 verified rows) / Medium (for the 43 estimated rows) until the live BEA API load replaces estimates." Add a `data_provenance` field to the contract that surfaces the estimate/verified distinction, or annotate the consumable table's README with the caveat so Gemma can cite it in user-facing responses.
- **@doc-generator:** The data dictionary and business glossary entries for `rpp_all_items` should note that this source currently contains a mix of verified and estimated values and that individual row values may shift on the next refresh.
- **@insight-manager / @mcp-engineer:** When the Gemma agent surfaces purchasing-power adjustments for states other than {CA, HI, DC, NJ, AR, MS, IA, OK}, responses should be phrased so that a future value revision does not make prior statements materially wrong (e.g., "approximately 3% above the national average" rather than "exactly 103.5"). Consider exposing a `provenance` field on the MCP tool response.
- **@governance-reviewer / @staff-engineer:** Treat replacement of estimated values with live BEA API values as a **data correction**, not a schema change — it does not require re-review of the contract or pipeline, only a DQ re-run and regression against the recommended thresholds.

### Data Quality Considerations

#### Known Edge Cases

| Edge Case | Description | Impact | Notes for @dq-rule-writer |
|-----------|-------------|--------|--------------------------|
| Iowa and Oklahoma tie at 87.8 | Two distinct states share the same `rpp_all_items` value. 50 distinct values across 51 rows. Both are spec-verified. | Breaks naive uniqueness assumptions on the measure column. | **Do NOT** write a uniqueness rule on `rpp_all_items`. Only `geo_fips` / `state_fips` should carry a uniqueness rule. |
| DC present at FIPS 11 | District of Columbia is not a state but is included in the dataset at FIPS 11 with RPP 109.9. | Any rule that filters "states only" will silently drop DC and break row-count and regional-coverage rules. | Write `count(*) WHERE geo_fips='11' = 1` as an explicit P0 rule. Any state-only filter must explicitly include FIPS 11. |
| `source_method` is 100% `csv_cache` today | Current load ran through the fallback path; no row came from the live BEA API. | A DQ rule pinning `source_method = 'bea_api'` would fail on the current load. | Rule must be `source_method IN ('bea_api','csv_cache')`. |
| FIPS scheme gaps (03, 07, 14, 43, 52) | These FIPS codes were never assigned. The 51 present codes are the complete canonical set. | A "contiguous FIPS codes" rule would false-positive. | Use an explicit 51-element canonical FIPS list for the completeness rule. |
| Estimates-in-place (43 of 51 rows) | See Data Provenance Caveat above. | DQ rules must pass in both estimate and verified states. | Rules are pre-designed in the EDA to tolerate both states. Do not tighten. |
| DC in Census South despite Northeast-like RPP | DC's RPP (109.9) behaviorally clusters with the Northeast (NJ 108.8, NY 107.5, MA 107.9) but the Census Bureau classifies DC as South. | A "region-level distribution" DQ rule that asserts "South mean RPP < Midwest mean RPP" or similar would false-positive due to DC's outlier position. | Do NOT write region-distribution-shape rules. Safe regional rule: "All 4 census regions represented" and "each region has >= 9 rows". |

#### Domain-Specific Validity Rules

| Rule | Description | Source |
|------|-------------|--------|
| National baseline = 100.0 by construction | No individual state equals 100.0 exactly; the national baseline is a population-weighted construct, not a row in the data. Simple arithmetic mean of state RPPs lands near but not at 100 (observed 96.98, EDA). | BEA methodology |
| Realistic RPP range | Over the last decade of BEA releases, no state has reported RPP outside ~[85.6, 113.0]. The spec DQ guardrails of [80.0, 130.0] carry generous headroom. | BEA historical publications |
| `purchasing_power_multiplier × rpp_all_items ≈ 100.0` | Silver-zone derivation invariant. Tolerance 0.01. | FutureProof-derived |
| California and Arkansas as sanity anchors | CA RPP historically in [108.5, 111.0]; AR RPP historically in [85.6, 87.9]. Verified anchors for spot-check DQ rules. | BEA historical data + spec |
| `geo_fips` matches `^\d{2}$` | State FIPS codes are always 2-digit zero-padded numeric strings. | ANSI/FIPS standard |

### Regulatory & Compliance Context

#### Applicable Regulations

| Regulation | Relevance | Key Requirements | Notes for @bcbs239-auditor |
|-----------|-----------|-----------------|---------------------------|
| None directly applicable | BEA RPP is U.S. Government-published aggregate economic statistics, public domain. No HIPAA, FERPA, GLBA, SOX, GDPR, or PCI DSS exposure. | N/A | No compliance assessment needed for this source in isolation. When joined with College Scorecard (FERPA-adjacent) in the Gold zone, compliance review of the combined product remains driven by the College Scorecard source, not this one. |
| U.S. Government Work / Public Domain | As a U.S. federal agency publication, BEA RPP data carries no copyright and can be freely redistributed with attribution. | Attribution: "Source: U.S. Bureau of Economic Analysis, Regional Economic Accounts." | Include attribution in the data contract and MCP tool responses. |

#### PII Expectations

| PII Type | Expected? | Sensitivity | Notes for @pii-scanner |
|----------|-----------|-------------|----------------------|
| Personal names | No | N/A | The entire table is 51 state-level aggregate rows. No individuals, no workers, no businesses, no names. |
| SSN / Tax ID / Government ID | No | N/A | Not applicable. |
| Location data (individual-level) | No | N/A | Geography is state-level only. `geo_fips` identifies a U.S. state, which is a jurisdiction, not a person or an address. State-level aggregation is categorically non-PII under HIPAA Safe Harbor and every other U.S. privacy framework. |
| Health records | No | N/A | Not applicable. |
| Financial records (individual) | No | N/A | RPP is a macroeconomic price index, not a measurement of any individual's income, spending, or wealth. |
| Education records | No | N/A | Not applicable. |

**Conclusion:** **No PII of any kind.** This is the cleanest PII posture of any source in the FutureProof pipeline. Every value in every row is a U.S. Government-published aggregate statistic about a state-level jurisdiction. **@pii-scanner can SKIP this source entirely** and document the skip with rationale: "51-row state-level macroeconomic reference table from BEA; all values are public-domain aggregate statistics; no individual-level data of any kind; no sensitivity review required at any zone."

### External Data Opportunities

| External Source | What It Adds | Join Key | Notes for @insight-manager |
|----------------|-------------|----------|---------------------------|
| BEA Metro-area RPPs (table MARPP) | Sub-state granularity — metro-level purchasing power adjustment. SF Bay Area vs. rest of California, NYC metro vs. upstate NY, etc. | CBSA code (requires separate state ↔ CBSA join) | High value for post-hackathon. Many students live in a specific metro, not "California in general." Requires a new ingest spec; not in current scope. |
| BEA historical RPP series (2008-present) | Time-series of how state cost-of-living has evolved. Useful for trend analysis. | `state_fips`, `data_year` | Medium value. Would support "how has purchasing power changed in your state?" narratives. Post-hackathon. |
| BEA Personal Income per Capita by State | Combined with RPP, yields real-income-per-capita by state. Richer context for career-outcome comparisons. | `state_fips` | High value for advanced analysis. Post-hackathon. |
| BLS OES State/Metro Wage data | Geographic occupation-level wage data. Combined with RPP, enables the full **Fight Location Lock** boss scoring formula (wage × RPP × geographic concentration). | SOC code + `state_fips` | Explicitly called out in the spec as the missing ingredient for the full boss. High priority post-hackathon. |
| U.S. Census ACS state-level data | Demographics, housing costs, commute patterns. Context for purchasing-power interpretation. | `state_fips` | Medium value. Would enrich MCP responses with "why is this state expensive?" context. |

### Concept Mapping Guidance

#### Source Codes → Business Concepts

| Source Code Pattern | Maps To | Confidence | Notes for @cde-tagger |
|--------------------|---------|------------|----------------------|
| `rpp_all_items` | Regional Price Parity (All Items) | Exact | BEA-published index. External standard. Auto-approve as CDE. Cross-reference BT-098. |
| `geo_fips` | State FIPS Code | Exact | ANSI/FIPS standard. Auto-approve as CDE. |
| `geo_name` | State Name | Exact | Plain-language state name. Auto-approve. |
| `purchasing_power_multiplier` (Silver) | Purchasing Power Multiplier | Exact (derived) | FutureProof-derived; propose as project-specific term. Cross-reference BT-099. |
| `cost_tier` (Gold) | Cost of Living Tier | Exact (derived) | FutureProof-derived enum; propose as project-specific term. |
| `adjusted_30k/50k/75k/100k` (Gold) | Purchasing-Power-Adjusted Salary Examples | Exact (derived) | Pre-computed display fields for the frontend. |

#### Known Mapping Ambiguities

**None.** Every field in this source maps unambiguously to a single business concept. This is the simplest concept-mapping of any source in the FutureProof pipeline.

### Canonical Concept Map (BEA RPP)

**Status:** CONFIRMED (spec-driven, no user interview required)
**Source:** Spec docs/specs/raw-ingest-bea-rpp.md + EDA report

#### Target Business Concepts

| # | Business Concept | Plain English Name | Expected Source Codes | Category | Priority |
|---|-----------------|-------------------|----------------------|----------|-----------|
| 1 | Regional Price Parity | Cost of Living Index (state, national=100) | `rpp_all_items` | Reference / Macroeconomic | CORE |
| 2 | Purchasing Power Multiplier | Salary Purchasing Power Factor | derived: `100.0 / rpp_all_items` | Derived / Financial | CORE |
| 3 | Cost Tier | Cost of Living Tier (very_high / high / average / low / very_low) | derived from `rpp_all_items` thresholds | Derived / Categorical | CORE |
| 4 | State (ANSI/FIPS) | State Identifier | `geo_fips`, `state_fips`, `state_abbr`, `state_name` | Reference / Geography | CORE |
| 5 | Census Region | U.S. Census Region | derived from `state_fips` | Reference / Geography | EXTENDED |
| 6 | Data Year | RPP Publication Year | `data_year` | Provenance / Temporal | CORE |

#### Cross-Source Concept Linkages (FutureProof Integration)

**Critical integration fact:** The BEA RPP table does **NOT** join to College Scorecard, BLS OOH, O*NET, or Karpathy AI Exposure by SOC or CIP code. It has no SOC, no CIP, no program, no occupation. Its only identifier is `state_fips`.

Instead, the RPP table joins at **query time** by the **student's selected state**. The join topology is:

```
BEA RPP (state_fips / state_abbr)
  → consumable.regional_price_parities
    → MCP tool: get_regional_price_parity(state)
    → MCP tool: compare_purchasing_power(salary, state_a, state_b)
    → Frontend: salary adjustment display on every screen that shows a salary
    → (Stretch) Fight Location Lock boss scoring
```

The student picks their state once (during onboarding or as a setting). Every time the frontend or Gemma presents a salary from BLS OOH or College Scorecard, it calls `get_regional_price_parity(selected_state)` and multiplies the national salary by the returned `purchasing_power_multiplier`. The pipeline does not pre-compute a cross-product of (occupation × state × adjusted salary) — that would be 832 × 51 = 42,432 rows and the combinatorics do not justify the storage. Instead, the Gold table is the 51-row RPP reference table, and the multiplication happens at serve time.

This means the RPP integration is **fundamentally different** from how BLS OOH, O*NET, and Karpathy integrate: those three all join on SOC (with the CIP↔SOC crosswalk bridging College Scorecard). BEA RPP is orthogonal — it is a **query-time lens**, not a pipeline-time join.

**Notes for @semantic-modeler and @principal-data-architect:** Model this table as an independent reference dimension, not a fact table. Do not add it to the SOC-keyed join graph. Document it as a "state-keyed lookup that applies at query time."

#### Concept-to-Code Mapping Rules

No mapping tiers needed — every field is a direct 1:1 mapping. No prefix, pattern, or heuristic mapping required. The ConceptNormalizer has no work to do on this source beyond passthrough.

#### Collision Resolution Rules

**None applicable.** One row per state, one RPP per row, no collisions possible at the grain.

### AI-Ready Considerations

| Consideration | Recommendation | Notes for @mcp-engineer |
|--------------|---------------|------------------------|
| User questions about cost of living | Expose `get_regional_price_parity(state)` as a first-class MCP tool. Students will ask "is X expensive?", "how much do I need to make in Y to live like I make $50K nationally?", "is it cheaper to live in Iowa or Texas?" | Accept flexible state input: USPS abbr, full name, or FIPS. Always return the `state_name`, `state_abbr`, `rpp_all_items`, `purchasing_power_multiplier`, `cost_tier`, and the pre-computed `adjusted_30k/50k/75k/100k` examples. Include a short prose explanation like "prices in California are about 11% higher than the national average" that Gemma can use verbatim. |
| Salary adjustment context | Every MCP tool that returns a wage (from BLS OOH or College Scorecard) should be paired with an optional RPP adjustment. | Offer a `student_state` parameter on wage-returning tools; when provided, include an `adjusted_salary` field in the response alongside the national figure. Never silently replace the national figure with the adjusted one — always return both so the student sees the comparison. |
| "What if I move?" scenario | Expose `compare_purchasing_power(salary, state_a, state_b)` as a second MCP tool. | Useful for students weighing multiple geographic options. Returns both states' adjusted salaries plus the dollar and percentage difference. |
| Provenance caveat in responses | While the data provenance caveat (8 verified, 43 estimated) is in effect, MCP responses should hedge numeric precision for non-verified states. | Consider a `provenance` field on tool responses: `"verified"` for {CA, HI, DC, NJ, AR, MS, IA, OK}, `"estimated"` for the other 43. Gemma can use this to phrase responses with appropriate confidence. |
| RPP interpretation | Students will ask "what does RPP 110 mean?" or "why does my state matter?" | Include a short methodology blurb in tool descriptions: "Regional Price Parities are a BEA-published index comparing the price level of a state to the U.S. national average (100). A state with RPP 110 has prices 10% above the national average; a state with RPP 87 has prices 13% below." |

### Assumptions (User-Deferred)

No user-deferred assumptions for this source. The spec is explicit on all design decisions:
- **Grain:** one row per state (spec).
- **Line code:** All Items only, LineCode=1 (spec).
- **Temporal model:** single-year static reference, annual refresh (spec).
- **Integration model:** query-time join by student's selected state, no SOC/CIP join (spec).
- **Derived fields:** `purchasing_power_multiplier` in Silver, `cost_tier` + `adjusted_NNk` in Gold (spec).
- **MCP tools:** `get_regional_price_parity(state)` and `compare_purchasing_power(salary, a, b)` (spec).

The only open item is the data provenance caveat — 43 of 51 rows are estimates pending a successful live BEA API load. This is tracked as a refresh task on the pipeline, not as a user decision.

### Confidence Notes

**High confidence:**
- Domain identification (BEA Regional Price Parities, All Items, state level, 2024) — unambiguous from source, methodology, and spec
- Grain (51 rows, 50 states + DC, one row per state) — verified exact in EDA
- Entity resolution posture (trivial; state FIPS is a canonical identifier) — EDA confirms 1:1 bijection between `geo_fips` and `geo_name`
- PII posture (zero PII; public-domain aggregate statistics) — structurally impossible for this source to contain PII
- Temporal posture (annual snapshot; no within-year variation; `data_year` is the only temporal dimension) — verified constant across all rows
- Integration model (query-time join by student's selected state; no SOC/CIP pipeline join) — explicit in spec, no ambiguity
- The 8 spec-verified row values — matched exactly in the EDA
- DC in Census South despite Northeast-like RPP — a known BEA/Census classification quirk, not a data error

**Medium confidence:**
- The 43 estimated row values are directionally plausible but not BEA-authoritative. They will shift on the next successful live API load. DQ thresholds are designed to tolerate both states.
- Cost-tier thresholds (108 / 103 / 97 / 91) are a project design choice rather than a BEA standard; if the distribution looks wrong to users, these can be retuned without changing upstream DQ.

**Low confidence / Needs post-hackathon revisit:**
- Whether the frontend should default to RPP-adjusted or national salary figures (UX question, not a data question)
- Whether metro-area RPPs (BEA MARPP) should replace state RPPs once available — student lived experience in SF Bay Area differs sharply from "California" as a whole
- The Fight Location Lock boss formula depends on geographic occupation wage data from BLS OES, which is not yet in the pipeline

---

## Anthropic Economic Index

**Date Added:** 2026-04-16
**Based On:** `governance/eda/raw-anthropic-economic-index-eda.md` (2026-04-16)
**Source:** HuggingFace `Anthropic/EconomicIndex`, release `release_2025_03_27`
**Spec:** `docs/specs/raw-ingest-anthropic-economic-index.md`
**User Familiarity:** Familiar — knows the dataset as the empirical complement to Karpathy exposure
**Confidence:** High (domain identification, grain, and aggregation strategy are unambiguous; SOC coverage shortfall is a documented dataset limitation, not a defect)

### Source Methodology

Anthropic's Economic Index v2 is an empirical measurement of how Claude is *actually being used*, derived by classifying a sample window of Claude.ai conversations against the O*NET task taxonomy. Each conversation is assigned to at most one O*NET task statement; per-task volume is reported as a global share of classified traffic, and each task is further decomposed across five v2 interaction modes (`directive`, `feedback_loop`, `task_iteration`, `validation`, `learning`) plus a `filtered` residual for conversations removed by safety or quality classifiers.

**Critical contrast with Karpathy AI Exposure:** Karpathy scores are *theoretical* (an LLM reading BLS descriptions and estimating "how much will AI reshape this occupation"). Anthropic's index is *observational* (measured adoption on Claude traffic, right now). They are orthogonal signals — a high Karpathy score means "AI could reshape this job"; a high Anthropic `observed_exposure_pct` means "AI users are already working on this job's tasks." Both are needed; neither replaces the other.

The two Automation/Augmentation taxonomies Anthropic publishes are **not interchangeable**. FutureProof uses the v2 file (`automation_vs_augmentation_by_task.csv`, five modes + filtered). In v2:
- `automation = directive + feedback_loop` — Claude acts without the user in the loop (delegation or autonomous feedback loops)
- `augmentation = task_iteration + validation + learning` — Claude assists; the user remains the driver
- `learning` is **augmentation**, not a separate third category, because the user is learning *from* Claude while remaining in control
- `filtered` is excluded from both (privacy/safety suppression or classifier miss)

### Domain Vocabulary

| Term | Definition | Source | Notes for @data-steward |
|------|-----------|--------|------------------------|
| task_pct | Global share (percent units, 0-100) of classified Claude conversations attributed to this O*NET task statement. Sum across all 3,365 task rows = 100.0000 exactly. **Aggregation must be SUM, not mean.** | Anthropic v2 methodology (authoritative for this dataset) | Propose. Emphasize "global share, percent units" in business term definition — this is the single gotcha readers will miss. |
| directive | v2 interaction mode: user delegates a task to Claude and Claude executes without clarification loops. **Automation.** | Anthropic v2 (authoritative) | Auto-approve — Anthropic-published standard. |
| feedback_loop | v2 interaction mode: Claude acts autonomously with environmental feedback (e.g., running code, reading results, iterating). **Automation.** | Anthropic v2 (authoritative) | Auto-approve. |
| task_iteration | v2 interaction mode: user and Claude iterate on a task collaboratively. **Augmentation.** | Anthropic v2 (authoritative) | Auto-approve. |
| validation | v2 interaction mode: Claude reviews or validates user-produced work. **Augmentation.** | Anthropic v2 (authoritative) | Auto-approve. |
| learning | v2 interaction mode: user learns *from* Claude (tutoring, explanation, knowledge transfer). **Augmentation** (user remains the driver). | Anthropic v2 (authoritative) | Auto-approve. Explicitly document that this is augmentation, not a third category — users will assume "learning = neutral." |
| filtered | Residual bucket — conversations removed by safety classifiers, privacy filters, or classifier miss. Not counted as automation or augmentation. | Anthropic v2 (authoritative) | Auto-approve. |
| automation_pct | FutureProof-derived Silver field: `directive + feedback_loop` share of Claude traffic on a SOC's tasks (volume-weighted across tasks within SOC). Range 0-1 (fraction). | FutureProof project-specific | Propose. **Naming inconsistency flag:** the `_pct` suffix elsewhere in this pipeline implies 0-100, but this field is 0-1. See @semantic-modeler recommendation. |
| augmentation_pct | FutureProof-derived Silver field: `task_iteration + validation + learning` share (volume-weighted). Range 0-1. | FutureProof project-specific | Propose. Same naming caveat as `automation_pct`. |
| filtered_pct | FutureProof-derived Silver field: `filtered` share (volume-weighted). Range 0-1. Per-SOC, `automation_pct + augmentation_pct + filtered_pct ≈ 1.0`. | FutureProof project-specific | Propose. Same naming caveat. |
| observed_exposure_pct | FutureProof-derived Silver/Gold field: sum of split task shares for a SOC (percent units, 0-100, same scale as source `task_pct`). The empirical counterpart to Karpathy's theoretical `exposure_score`. | FutureProof project-specific | Propose. Emphasize this is in percent units (matches source), not a 0-10 score (that's Karpathy). |

### Taxonomy / Classification Systems

| System | Description | Authority | Coverage in Data |
|--------|-------------|-----------|-----------------|
| O*NET task statements (free text) | 3,364 distinct Anthropic-measured task strings; join key is normalized task text (lowercase + strip trailing period). | O*NET / U.S. Department of Labor (task statements); Anthropic (measurement) | 3,364 / 3,365 Anthropic rows match an O*NET task statement (99.97%). The one non-match is the literal placeholder `task_name='none'` (1.78% of all traffic). |
| O*NET-SOC codes | `XX-XXXX.NN` format (detailed O*NET extension). Strip `.NN` to get base SOC `XX-XXXX`. | O*NET / BLS | 588 distinct base SOCs derivable from Anthropic data (after task→SOC expansion). |
| SOC 2018 (base) | Standard Occupational Classification — `XX-XXXX` codes shared across BLS OOH, O*NET, Karpathy, and this source. | BLS / OMB | 510 of 832 SOCs in `consumable.occupation_profiles` have Anthropic coverage (61.3%). See coverage analysis below. |
| v2 interaction mode taxonomy | Five modes + filtered residual. Fixed 6-axis vector summing to 1.0 per task. | Anthropic Economic Index v2 (authoritative) | 100% of `automation_vs_augmentation_by_task.csv` rows conform (3,364/3,364 rows sum to 1.0 within 1e-6). |

### Enumerated Values with Business Meaning

| Field | Values | Meaning |
|-------|--------|---------|
| v2 interaction mode | `directive`, `feedback_loop`, `task_iteration`, `validation`, `learning`, `filtered` | Six-axis decomposition of how Claude was used on a task. First two = automation; next three = augmentation; last = suppressed/excluded. |
| task_name | 3,364 O*NET task strings + 1 literal `'none'` placeholder | `'none'` is the uncategorized-traffic bucket (1.78% of volume) and MUST be filtered before Silver aggregation. |

### Entity Types

| Entity Type | Identifier Field(s) | Example | Notes for @entity-resolver |
|-------------|---------------------|---------|---------------------------|
| O*NET Task Statement | `task_name` (normalized free text) | `"modify existing software to correct errors / adapt to new hardware / upgrade interfaces"` (6.65% of all traffic) | Bronze grain. Join to O*NET bridge by normalized text equality (lowercase + rstrip `.`). One non-match is `'none'` — filter it in Silver, do not attempt to resolve. |
| Occupation (SOC 2018) | `soc_code` (base `XX-XXXX`, stripped from `XX-XXXX.NN`) | `15-1252` (Software Developers) | Silver grain. Shared identifier with BLS OOH, O*NET, and Karpathy pipelines. No new entity resolution work required here — reuses the SOC entity already established upstream. |

**Task → SOC fan-out:** 82 of 3,364 Anthropic tasks map to ≥2 SOCs (max 34-way). These are boilerplate task statements that O*NET reuses across related occupations (e.g., generic "collaborate with colleagues" phrasings). The Bronze/Silver split strategy preserves the global-sum invariant — see Aggregation Strategy below.

### Temporal Patterns

| Pattern | Description | Notes for @temporal-modeler |
|---------|-------------|---------------------------|
| Snapshot per release | One release = one window of classified Claude traffic. No row-level timestamps. | Model as a pinned-release static reference, not a time-series. The `source_release` should be a table-level property, not a per-row column. |
| Release pinning required | Anthropic has published newer releases (`release_2026_01_15`, `release_2026_03_24`) that contain only raw conversation snapshots and lack task-level aggregates. `release_2025_03_27` is the canonical and currently only release carrying `task_pct_v2.csv` + `automation_vs_augmentation_by_task.csv`. | Hard-pin `release_2025_03_27` in the ingestor. Do not auto-follow HEAD. A refresh requires Anthropic to re-publish task-level v2 aggregates — not guaranteed on any cadence. |
| No amendment pattern | No row-level corrections. Full-refresh on new release. | No SCD handling needed. Replace the table on refresh; archive prior release snapshots if cross-release comparison is ever needed (post-hackathon). |

### Data Quality Considerations

#### Known Edge Cases

| Edge Case | Description | Impact | Notes for @dq-rule-writer |
|-----------|-------------|--------|--------------------------|
| `task_name='none'` placeholder | 1 row in `task_pct_v2.csv` (pct = 1.78) representing Claude conversations that could not be classified to any O*NET task. | Must be preserved in Bronze, filtered in Silver. If not filtered, it will fail the task→SOC join and silently appear as data loss. | P0: Bronze must preserve the row verbatim. P0: Silver must filter `task_name='none'` before join. Dedicated test: `dropped_none_pct` between 1.5 and 2.5. |
| Row-sum invariant on v2 axes | Every row in `automation_vs_augmentation_by_task.csv` has `directive + feedback_loop + task_iteration + validation + learning + filtered = 1.0`. Verified exact in EDA (3,364/3,364 rows within 1e-6). | If violated, either the source is corrupted or the ingestor has dropped a column. Always fatal. | P0: `abs(row_sum - 1.0) <= 1e-6` on every Bronze row. Chaos test: corrupt one axis, verify it fails. |
| Task → multi-SOC fan-out | 82 tasks (2.4% of tasks) map to ≥2 SOCs; maximum 34-way. These are O*NET boilerplate statements. | Naive sum-without-split would inflate the global total to ~118% (violating the 100% invariant). Silver must split `pct / N` before aggregating. | P0: post-split global sum = sum of non-`none` task_pct, tolerance ±0.01. P1 informational: log tasks mapping to >5 SOCs. |
| Fully-filtered tasks | 1,066 tasks (31.69%) have `filtered ≥ 0.999` — the entire task was suppressed in classified traffic. | Aggregated SOCs whose tasks are all fully filtered will have near-zero `automation_pct` and `augmentation_pct`. That is real, not a bug. | Informational only. Do not fail a SOC row with near-zero automation/augmentation — annotate with low-confidence flag instead. |
| SOC coverage shortfall | 510 of 832 target SOCs in `consumable.occupation_profiles` have Anthropic coverage (61.3%). Spec's original target was 80%. | Gaps cluster in 47-XXXX (Construction), 49-XXXX (Maintenance/Repair), 51-XXXX (Production), 53-XXXX (Transportation), 35-XXXX (Food Service) — occupations Claude traffic rarely touches. | **Revise P0 threshold from ≥80% to ≥60% SOC coverage.** Document the dataset limitation in the contract. This is not an ingestor defect — it is a structural property of Claude's user base. |
| `pct > 1` outliers | 8 tasks exceed 1% share. All are software-engineering / IT-support / technical-writing tasks. | Expected — consistent with Anthropic's published v2 report. | P1: verify all `pct > 1` rows map to 15-XXXX (Computer), 25-3099 (Education), or 27-30XX (Media/Communications) SOCs. Flag if an outlier maps to an unexpected major group. |
| Release freshness | Newer releases lack task-level aggregates; pipeline is pinned to 2025-03-27. | Staleness risk grows over time as Claude usage shifts. | Informational: monitor Anthropic HuggingFace for future v2 task-level releases. No SLA; refresh is event-driven. |

#### Domain-Specific Validity Rules

| Rule | Description | Source |
|------|-------------|--------|
| Global-share invariant | Sum of all `task_pct` values = 100.00 (± 0.01). | Anthropic v2 methodology |
| v2 mode-vector invariant | Every task's six v2 axes sum to 1.0 (± 1e-6). | Anthropic v2 methodology |
| Automation/augmentation partition | `automation + augmentation + filtered = 1.0` at every row (where automation = directive + feedback_loop, augmentation = task_iteration + validation + learning). | Anthropic v2 methodology |
| SOC format | Base SOC must match `^\d{2}-\d{4}$` after stripping the `.NN` O*NET extension. | BLS SOC 2018 |
| Post-split sum invariant | After splitting `pct / N_soc` across multi-SOC tasks, sum(pct_split) = sum(non-`none` task_pct) = 98.22 (± 0.01). | FutureProof Silver transform |

### Regulatory & Compliance Context

| Regulation | Relevance | Key Requirements | Notes for @bcbs239-auditor |
|-----------|-----------|-----------------|---------------------------|
| CC-BY 4.0 International | Applicable — this is the dataset's published license. | Attribution required in any downstream product. Must cite: "Anthropic Economic Index v2, release 2025-03-27, CC-BY 4.0." | Add citation string to MCP tool descriptions and any UI surface that displays Anthropic-derived metrics. No compliance controls beyond attribution. |
| None others directly applicable | Aggregated conversation-usage statistics on public data. No HIPAA, FERPA, SOX, GDPR, or PCI DSS triggers. | N/A | If the product ever expands to employment decisions (hiring, compensation), AI-exposure scores could trigger EEOC concerns — same caveat as Karpathy. |

### PII Expectations

| PII Type | Present? | Sensitivity | Notes for @pii-scanner |
|----------|----------|-------------|----------------------|
| Personal names | No | N/A | Anthropic publishes aggregated shares across millions of conversations; no per-conversation, per-user, or per-message content. |
| Conversation content | No | N/A | Only task-level volume and interaction-mode aggregates. No text from any conversation is in the release. |
| User identifiers | No | N/A | No user IDs, session IDs, or pseudonymous tokens. |
| Location data | No | N/A | Not present — task-level aggregates are global, not geolocated. |
| Anthropic-internal classifier metadata | No | N/A | The `filtered` bucket is a single aggregate number; the underlying classifier decisions are not exposed. |

**Conclusion:** No PII. This is structurally aggregate-over-millions-of-conversations data; individual-level inference is not possible from the release files.

### External Data Opportunities

| External Source | What It Adds | Join Key | Notes for @insight-manager |
|----------------|-------------|----------|---------------------------|
| Karpathy AI Exposure | Theoretical exposure — "could AI reshape this?" Pairs with Anthropic's observational "is AI already working on this?" to form a two-signal exposure frame. | SOC code | Already in pipeline. This is the **primary** consumer of Anthropic data in FutureProof — see `three-signal-ai-exposure-composite` spec. |
| Gemma re-scoring (post-hackathon) | Open-model rescoring of the same BLS descriptions; combined with Anthropic observation and Karpathy theoretical, produces a three-signal composite. | SOC code | Spec S4 (three-signal-ai-exposure-composite) consumes this. Blocked until this ingestor is COMPLETE. |
| Future Anthropic releases | If Anthropic republishes v2 task-level aggregates, compare cross-release drift to measure adoption velocity by occupation. | (release, SOC) tuple | Post-hackathon. Would enable a **velocity** signal (how fast is AI adoption growing for this occupation?) to complement the current static snapshot. |
| BLS OES (Occupational Employment Statistics) | Employment counts per SOC — would allow weighting `observed_exposure_pct` by workforce size for "how much of the labor market is Claude touching?" | SOC code | Not currently in pipeline. Optional enrichment. |

### Concept Mapping Guidance

#### Source Codes → Business Concepts

| Source Code Pattern | Maps To | Confidence | Notes for @cde-tagger |
|--------------------|---------|------------|----------------------|
| `task_pct` (percent units, 0-100) | Observed AI Exposure (per-task volume share) | Exact | Units: percent. Carry forward to Silver without rescaling. |
| `directive` + `feedback_loop` | Automation Share | Exact | Defined by Anthropic v2 methodology; no alternative decomposition is valid for this dataset. |
| `task_iteration` + `validation` + `learning` | Augmentation Share | Exact | Same caveat. Document explicitly that `learning` is augmentation (users will misread). |
| `filtered` | Filtered / Suppressed Share | Exact | Residual bucket; not a third category of "use." |
| O*NET-SOC `XX-XXXX.NN` (stripped to `XX-XXXX`) | Standard Occupational Classification (SOC 2018) | Exact | Shared CDE with BLS/ONET/Karpathy pipelines. Already registered. |
| Task name (free text, lowercase + stripped period) | O*NET Task Statement | Exact | Ephemeral — not a registered CDE. Used only for the Bronze → Silver join. |

#### Known Mapping Ambiguities

| Source Code | Candidates | Recommended | Rationale |
|------------|-----------|-------------|-----------|
| Task with N > 1 SOC mappings | (a) Assign full `pct` to each SOC (inflates total). (b) Split `pct / N` evenly (conserves total). (c) Weight by `incumbents_responding` (O*NET survey metadata). | **(b) Split `pct / N` evenly.** | (a) violates the global-sum invariant. (c) would be preferable but `incumbents_responding` has ~5,200 of 19,530 nulls and is reported at the (task, O*NET-SOC detailed) grain with inconsistent coverage — even-split is the maximum-entropy defensible choice. |
| `task_name='none'` | (a) Assign to a synthetic SOC. (b) Proportionally redistribute to all SOCs. (c) Drop. | **(c) Drop in Silver.** | `'none'` represents uncategorized traffic — it has no meaningful occupation mapping. Dropping is documented in the contract; the 1.78% loss is expected and explicit. |
| `learning` mode classification | (a) Augmentation. (b) Neutral / third category. (c) Automation (Claude is "teaching"). | **(a) Augmentation.** | Anthropic v2 methodology is explicit: in `learning`, the user remains in control and is learning *from* Claude — user stays in the loop, so it is augmentation, not automation. |

### Canonical Concept Map (Anthropic Economic Index)

**Status:** CONFIRMED
**Source:** Spec `docs/specs/raw-ingest-anthropic-economic-index.md` (primary) + Anthropic v2 methodology (authoritative taxonomy)

#### Target Business Concepts

| # | Business Concept | Plain English Name | Expected Source Columns | Category | Priority |
|---|-----------------|-------------------|-------------------------|----------|----------|
| 1 | observed_exposure_pct | Observed AI Exposure (% of Claude traffic) | `task_pct` (split by N_soc, summed per SOC) | AI Exposure — Observed | CORE |
| 2 | automation_pct | Automation Share (Claude acts without user) | `directive + feedback_loop` (volume-weighted per SOC) | AI Interaction Mode | CORE |
| 3 | augmentation_pct | Augmentation Share (Claude assists user) | `task_iteration + validation + learning` (volume-weighted per SOC) | AI Interaction Mode | CORE |
| 4 | filtered_pct | Filtered / Suppressed Share | `filtered` (volume-weighted per SOC) | AI Interaction Mode | EXTENDED |
| 5 | task_count | Number of Anthropic-measured tasks contributing to this SOC | count of distinct task_name per SOC | Provenance / Confidence | EXTENDED |
| 6 | soc_code | Standard Occupational Classification | stripped from O*NET-SOC `XX-XXXX.NN` → `XX-XXXX` | Taxonomy | CORE |
| 7 | source_release | Anthropic release identifier | constant `'release_2025_03_27'` at ingest time | Provenance / Temporal | CORE |

#### Cross-Source Concept Linkages (FutureProof Integration)

This source is the **empirical half of the AI exposure story**. It integrates with three other sources at the SOC level:

```
Anthropic Economic Index (observed_exposure_pct, automation_pct)
  → consumable.ai_exposure (joined by soc_code)
      ↘ Karpathy AI Exposure (exposure_score, theoretical)
      ↘ Gemma re-scoring (post-hackathon, theoretical, open-model)
  → three-signal-ai-exposure-composite (S4, downstream spec)
      → theoretical + observed + velocity → composite AI exposure
  → consumable.program_career_paths (via soc_code)
      → Frontend: "Fight AI" boss scoring + stat_res + a future "observed adoption" badge
```

**Key integration fact:** `consumable.ai_exposure` was **extended** (not replaced) to carry the Anthropic fields. The Karpathy `exposure_score` remains the primary `stat_res`/`boss_ai_score` driver for the hackathon demo; the Anthropic `observed_exposure_pct` and `automation_pct` are carried as **metadata/context fields** for the MCP server and for the S4 composite spec. This dual-occupation posture is deliberate: Karpathy gives coverage (342 SOCs, LLM-scored), Anthropic gives ground truth on the 510 SOCs Claude actually touches.

**The two are complementary, not competing signals.** Correlating them is a valid post-hackathon analysis but the pipeline does not pre-compute a fused score in Silver; it carries both and lets the MCP server / frontend combine them for context.

**Notes for @semantic-modeler and @principal-data-architect:** Model this as an extension of the existing SOC-keyed fact (`consumable.ai_exposure`), not a new entity. Do not introduce a new Gold table unless the S4 composite spec warrants it (at which point a derived `ai_exposure_composite` table may be appropriate). Naming inconsistency flag: the `_pct` suffix implies 0-100 elsewhere in the pipeline but `automation_pct`/`augmentation_pct`/`filtered_pct` carry 0-1 fractions. Decide once, consistently — either rename to `automation_share` (preferred) or rescale to 0-100 to match `observed_exposure_pct`.

#### Concept-to-Code Mapping Rules

Ingestor tier:
- **Bronze:** 1:1 passthrough at `(task_name, soc_code)` grain after joining Anthropic task files to the O*NET bridge. Preserve `task_name='none'` verbatim. Do not split or aggregate in Bronze.
- **Silver:** Filter `task_name='none'`. Split `pct` evenly across a task's N mapped SOCs (`pct_split = pct / N`). Aggregate to SOC grain: `observed_exposure_pct = SUM(pct_split)`, `automation_pct = weighted_mean(directive + feedback_loop, weight=pct_split)`, `augmentation_pct = weighted_mean(task_iteration + validation + learning, weight=pct_split)`, `filtered_pct = weighted_mean(filtered, weight=pct_split)`, `task_count = COUNT(DISTINCT task_name)`.
- **Gold:** Join to `consumable.occupation_profiles` by `soc_code`. Carry all Silver fields through as extensions to `consumable.ai_exposure`. No further transformation.

#### Collision Resolution Rules

**At task grain:** no collisions (task_name is unique per file).
**At task-SOC grain:** Anthropic provides one pct per task; SOC multiplicity is resolved by the even-split rule above. This is not a collision — it is a defined fan-out.
**At SOC grain:** after aggregation, `soc_code` is unique. If a SOC ever appeared twice (grain bug), the first P0 DQ rule on the Silver table would catch it.

### AI-Ready Considerations

| Consideration | Recommendation | Notes for @mcp-engineer |
|--------------|---------------|------------------------|
| User questions about "is AI already doing this job?" | Expose `observed_exposure_pct` and `automation_pct`/`augmentation_pct` through MCP. Common queries: "Are AI users already working on [occupation]?", "How much of Claude usage is aimed at my career?", "Is AI automating or assisting [occupation]?" | Return the triple (observed_exposure_pct, automation_pct, augmentation_pct) together. Any one in isolation is misleading: high exposure + high augmentation = "AI is heavily used but as an assistant" is very different from high exposure + high automation = "AI is doing the work." |
| Contrast with Karpathy theoretical score | When both signals exist for a SOC, surface them side-by-side with explicit framing. | MCP response template: "Theoretical exposure (Karpathy): X/10 — how much AI *could* reshape this. Observed exposure (Anthropic): Y% of Claude traffic — how much AI users *are actually* doing this work today. Of that, Z% is automation and W% is augmentation." |
| Coverage gaps | 510 of 832 SOCs have Anthropic data. Missing SOCs are real (Claude traffic doesn't touch them), not a data error. | When a user queries a SOC with no Anthropic data (e.g., a truck driver), MCP should explicitly say "No observed Claude usage for this occupation — this does not mean AI won't affect it, only that it is not prominent in current Claude conversations." Do not silently substitute zero. |
| Methodology caveats | Always cite the release and license when serving Anthropic-derived metrics. | Add to every MCP response carrying this data: "Source: Anthropic Economic Index v2, release 2025-03-27, CC-BY 4.0." |
| `learning` interpretation | Users will assume "learning" means AI is teaching (automation-like). It is not — the user remains in control. | Include a one-sentence clarifier on any MCP response that breaks out interaction modes: "Learning mode is counted as augmentation because the user is actively learning from Claude, not delegating work to it." |
| Filtered share interpretation | High `filtered_pct` on a SOC does **not** mean the occupation is dangerous or suppressed — it means its tasks' conversations were often removed by safety/privacy classifiers. | Do not surface `filtered_pct` as a first-class metric on the student-facing UI. Carry it for completeness and debugging but avoid showing it without context. |

### Assumptions (User-Deferred)

No user-deferred assumptions on this source. The spec and Anthropic v2 methodology are explicit on every design decision:

- **Grain:** `(task_name, soc_code)` at Bronze, `soc_code` at Silver (spec).
- **Release pinning:** `release_2025_03_27` is the canonical release; newer releases lack task-level aggregates (verified in EDA).
- **Automation/augmentation definition:** Anthropic v2 taxonomy (authoritative; no project-specific reclassification).
- **Fan-out handling:** even `pct / N` split (decided in Aggregation Strategy Decision section of the EDA; no alternative defensible given null-rich `incumbents_responding`).
- **`'none'` row:** preserve in Bronze, drop in Silver (spec).
- **SOC coverage target:** revised from ≥80% to ≥60% based on EDA finding of 61.3% actual coverage — this is a **documented threshold revision**, not a user decision.
- **Naming inconsistency:** `_pct` suffix on fraction fields is a project-wide decision deferred to @semantic-modeler — see recommendation above.

### Confidence Notes

**High confidence:**
- Domain identification (empirical observation of Claude usage mapped to O*NET tasks) — unambiguous from source, methodology, and EDA.
- Grain at Bronze `(task, soc_code)` and Silver `soc_code` — verified in EDA.
- Global-share invariant (sum(task_pct) = 100.0000 exactly; sum of post-split shares = 98.22 after dropping `'none'`) — verified.
- v2 mode-vector invariant (6 axes sum to 1.0 per row, 3,364/3,364 within 1e-6) — verified.
- Even-split `pct / N` aggregation strategy — mathematically defensible and the only sum-conserving option given `incumbents_responding` nulls.
- No PII — structural aggregate-over-millions-of-conversations posture.
- License is CC-BY 4.0 — confirmed from HuggingFace dataset card.
- Integration with `consumable.ai_exposure` and downstream `three-signal-ai-exposure-composite` (S4) — explicit in spec, unambiguous.

**Medium confidence:**
- Whether 61.3% SOC coverage is stable across future releases. Claude's user base is evolving; the coverage gap in manual/physical occupations may widen or narrow.
- Whether Anthropic will republish v2 task-level aggregates on newer release dates. If `release_2025_03_27` remains the only v2 task-level snapshot indefinitely, staleness risk grows.
- The `filtered` bucket's semantic interpretation — Anthropic documents it as a residual but does not publish the classifier cutoffs. A high filtered share could be safety, privacy, or quality-driven; we cannot decompose further.

**Low confidence / Needs post-hackathon revisit:**
- Whether to weight task-SOC splits by `incumbents_responding` (or another O*NET signal) instead of even-split. Would require a separate EDA pass on O*NET's null patterns.
- Whether to fuse Karpathy theoretical + Anthropic observed scores into a single composite `stat_res` or keep them separate. Deferred to the S4 spec.
- Whether the `_pct` naming (0-1 vs. 0-100) should be normalized project-wide. A rename affects downstream columns, tests, and MCP tool schemas — a multi-spec refactor.
- Cross-release velocity signal (how fast is AI adoption growing per occupation?). Blocked on Anthropic republishing v2 aggregates at a second date.

---

## O*NET Education, Training, and Experience (ETE)

**Date Added:** 2026-04-16
**Based On:** `governance/eda/raw-onet-experience-eda.md` (2026-04-16, 35,998 rows across 878 O*NET-SOC occupations)
**Source:** O*NET 30.2 Database — `Education, Training, and Experience.txt` (same `db_30_2_text.zip` bundle used by the other five O*NET ingestors)
**Spec:** `docs/specs/onet-experience-requirements.md`
**Primary User-Facing Purpose:** Gates the Stage 3 career branching tree by realistic experience requirements — "Chief Technology Officer" no longer appears as a one-hop branch off "Software Developer" because its 10+ year experience profile pushes it behind a locked tier.
**User Familiarity:** Expert — Jeff approved the tier thresholds and the "Over 10 years" midpoint in `governance/approvals/onet-experience-requirements-open-decisions.md` on 2026-04-16.
**Confidence:** High (all data structure, taxonomy, and scale semantics are externally defined by O*NET; the only FutureProof-derived artifacts are the tier-bucket thresholds and the midpoint-years mapping, both human-approved)

### Relationship to the Existing O*NET Section

This section extends the O*NET domain context above. It does **not** redefine O*NET-SOC format rules, the six-table architecture, the Incumbent-vs-Expert domain-source split, the `recommend_suppress` semantics, or the BLS-SOC truncation pattern — those are already captured in the main O*NET section and apply identically here. Read this section as a specialization for the ETE file only. Cross-references:

- **O*NET-SOC code format** (`XX-XXXX.XX`), suffix semantics (`.00` base vs. non-`.00` detailed), and truncation-to-BLS rules → see "O*NET-Specific: SOC Code Cross-Source Bridging" above.
- **The 93 "All Other" / Military gap** → applies identically; none of those 93 codes appear in the ETE file.
- **Scale-type interpretation as a general concept** (always use `scale_id` to interpret `data_value`) → same principle applies, but ETE uses a different set of four scales, enumerated below.

### What O*NET Publishes in the ETE File

The Education, Training, and Experience file carries **percent-frequency distributions** across four scales. Unlike Work Activities (where each occupation gets one IM and one LV rating per element) or Work Context (point estimates), ETE reports full distributions: each occupation × scale produces a set of category rows whose `data_value` percentages sum to approximately 100.

| Scale ID | Element ID | Full Name | Categories | Rows in File | What It Measures |
|----------|-----------|-----------|-----------:|-------------:|------------------|
| RL | 2.D.1 | Required Level of Education | 12 | 10,536 | Distribution of respondents across 12 education tiers (Less than High School → Post-Doctoral Training) |
| **RW** | **3.A.1** | **Related Work Experience** | **11** | **9,658** | **Distribution across 11 duration buckets (None → Over 10 years) — THIS is what FutureProof consumes** |
| PT | 3.A.2 | On-Site or In-Plant Training | 9 | 7,902 | Distribution across 9 duration buckets for employer-provided in-plant training |
| OJ | 3.A.3 | On-the-Job Training | 9 | 7,902 | Distribution across 9 duration buckets for post-hire OJT |

Arithmetic invariant: 878 occupations × (12 + 11 + 9 + 9) = 878 × 41 = **35,998 rows** (matches the EDA row count exactly).

**Spec-drafting caveat now fixed in spec §Source Data:** The original spec claimed OJ had 11 categories. OJ actually has 9 in every occupation, the same cardinality as PT. Category-count DQ rules must assert `RL=12, RW=11, PT=9, OJ=9`; anything else is a drafting error, not source drift.

### What a "Percent Frequency Distribution" Means Here

Each row carries `data_value` — the percentage of survey respondents who chose that category for that (occupation, scale). O*NET collects this via two data-collection modes, both present in the ETE file:

| `domain_source` | Rows | `recommend_suppress` pattern | `standard_error` / CI bounds | How it is collected |
|-----------------|-----:|------------------------------|------------------------------|---------------------|
| `Incumbent` | 27,388 (76.1%) | `N` or `Y` (real sample-based flag) | `standard_error` populated; CI bounds populated on ~62% of rows | Survey of workers actually in the occupation (sample sizes: median n=23, p95=40, max=98) |
| `Occupational Expert` | 8,610 (23.9%) | always `n/a` | always null | Small expert panel — no sampling distribution, hence no SE or CI |

The `recommend_suppress='n/a'` ↔ `Occupational Expert` bijection is exact (8,610 ↔ 8,610). `n` (sample size) is populated on 100% of rows including the Expert rows — treat it as always non-null for DQ purposes even though the spec's Raw schema marks it optional.

**Note on the narrower domain_source enum:** Work Activities and Work Context also carry `Analyst` and `Analyst - Transition` domain_source values; the ETE file does **not**. Only `Incumbent` and `Occupational Expert` appear. DQ rules for ETE should enforce the narrower two-value set; reusing the four-value set from Work Activities would pass but is less tight than it could be.

### Which Scale FutureProof Consumes, and Why

**Primary signal: RW (Related Work Experience).** This is the only scale that flows through to Silver and Gold. The Silver transformer at `src/silver/onet_experience_transformer.py` filters `scale_id = 'RW' AND element_id = '3.A.1'` as the first step; the other three scales are ingested into Bronze but never read downstream.

Why the other three scales are ingested but not surfaced:

- **RL (education)** — redundant with College Scorecard data; FutureProof already has richer program-level education signals via CIP→SOC.
- **PT (in-plant training)** — low actionability for students; mostly varies with industry, not career path.
- **OJ (on-the-job training)** — overlaps semantically with RW but measures post-hire learning, not pre-hire requirements. RW is the cleaner signal for career-tree gating.

We keep RL/PT/OJ in Bronze for completeness (zero extra cost once the file is parsed) and for future enrichment opportunities — e.g., a future "this career requires a PhD" warning would consume RL category 12 (Post-Doctoral Training).

### RW Category Semantics (The 11 Duration Buckets)

These eleven categories are defined by O*NET. The **midpoint-years** column is a FutureProof derivation, not O*NET-published — it exists so the distribution can be collapsed to a scalar via weighted median. The "Over 10 years" midpoint of 12 years was human-approved on 2026-04-16.

| Cat | O*NET Definition | Midpoint (yr) | Approved Tier (derived) |
|----:|-----------------|--------------:|------------------------|
| 1 | None | 0 | entry |
| 2 | Up to and including 1 month | 0 | entry |
| 3 | Over 1 month, up to and including 3 months | 0.17 | entry |
| 4 | Over 3 months, up to and including 6 months | 0.38 | entry |
| 5 | Over 6 months, up to and including 1 year | 0.75 | entry |
| 6 | Over 1 year, up to and including 2 years | 1.5 | early |
| 7 | Over 2 years, up to and including 4 years | 3 | early |
| 8 | Over 4 years, up to and including 6 years | 5 | mid |
| 9 | Over 6 years, up to and including 8 years | 7 | mid |
| 10 | Over 8 years, up to and including 10 years | 9 | senior |
| 11 | Over 10 years | 12 | senior |

**Notes for @data-steward:** The category definitions are an external O*NET standard (auto-approve). The midpoint mapping and the tier bucketing are FutureProof project-specific (propose as BT-117 / BT-118 — already captured in the spec's Business Glossary Terms section and explicitly approved by Jeff).

### Weighted-Median Aggregation Method

The Silver transformer collapses each 11-category RW distribution into a single scalar `experience_years_typical`. The algorithm is:

1. Walk categories 1 → 11 in order, accumulating `cumulative_pct += data_value`.
2. The **weighted median category** is the first category where `cumulative_pct >= 50.0`.
3. `experience_years_typical = midpoint_years[median_category]` (from the table above).
4. `experience_tier` is derived from `experience_years_typical` via the approved thresholds:

| `experience_years_typical` range | `experience_tier` |
|----------------------------------|-------------------|
| 0 ≤ yr < 1 | entry |
| 1 ≤ yr < 4 | early |
| 4 ≤ yr < 8 | mid |
| 8 ≤ yr | senior |

Note that the threshold table operates on **years**, not on category numbers. This means category 5 (midpoint 0.75 yr) lands in **entry** even though its name ("Over 6 months, up to and including 1 year") sounds borderline. This is the correct behavior — see the Retail Salespersons gotcha below.

**Why collapse a distribution to a scalar at all?** The FutureProof UI (career tree, boss gauntlet) needs a single gate value per occupation: "does this branch need more than 5 years of experience?" Passing the full 11-category vector to the frontend would push visualization complexity into React without giving the user any additional decision leverage. The scalar answer ("yes, 7 years typical") is what actually drives the UX.

**Tradeoff: we keep BOTH.** The Silver schema carries `experience_years_typical` (the scalar, `double`, always populated) AS WELL AS `experience_distribution` (a JSON string of the full `{"1": 5.2, "7": 45.3, ...}` vector). The scalar is the primary signal. The JSON column is a diagnostic escape hatch for any downstream consumer that wants to detect bimodality, compute its own summary statistic, or render a distribution chart. It costs one text column and ~200 bytes per row to keep the option open.

**Tie-break rule (approved).** If cumulative_pct lands exactly on a boundary (50.0 ± floating-point noise), pick the **lower-numbered** category — the more-conservative interpretation. The approved-open-decisions file codifies this; the implementation should use `cumulative >= 50.0` rather than `== 50.0` to avoid float-comparison fragility.

### BLS SOC vs O*NET SOC: The Truncation and Averaging Step

ETE is published at O*NET-SOC detail grain (`XX-XXXX.XX`). FutureProof's Gold table `consumable.career_branches` joins at BLS SOC grain (`XX-XXXX`). The Silver transformer must cross that boundary. This follows the **same pattern already established** in the existing O*NET Silver precedent (see the main O*NET section above and `gold-onet-profiles` spec):

1. **Truncate** `XX-XXXX.XX` to `XX-XXXX` by taking the first 7 characters (6 digits + hyphen).
2. **Group** by the truncated BLS SOC.
3. **Aggregate** multiple detail rows into one: take the **unweighted average** of `experience_years_typical` across all O*NET details for a single BLS SOC, then re-derive `experience_tier` from the averaged years.
4. **Track provenance** via `onet_details_averaged` (count of detail codes collapsed for this BLS row). 702 of 765 BLS SOCs (91.8%) average a single detail; 63 BLS SOCs (8.2%) average 2+ details; the max observed is 8.

Row-count implication — the Silver row count is **765, not 867 or 1,016**:
- ETE covers 878 O*NET detail codes (not 1,016 — the remaining 138 are a superset of the 93 "All Other" / Military codes plus ~45 recently-added codes where ETE survey data has not been collected yet).
- After BLS-SOC truncation-and-collapse, 878 details → 765 distinct BLS SOCs.
- The Silver DQ row-count rule is `720 ≤ count ≤ 810` (approved in spec §Zone 2 after EDA found the real coverage).

Weighting note — the spec and approval file explicitly chose **unweighted** averaging for multi-detail aggregation. Employment-weighting (by BLS workforce counts) would be more accurate but requires a cross-source join that isn't worth the extra dependency for the hackathon. This is the same tradeoff documented in the main O*NET section's "Assumptions" table (#5).

### Tier Thresholds (Human-Approved)

The 0-1 / 1-4 / 4-8 / 8+ year breakpoints → entry / early / mid / senior tiering is a **FutureProof-specific** classifier, not an O*NET concept. Jeff approved it on 2026-04-16 (durable record: `governance/approvals/onet-experience-requirements-open-decisions.md`). The motivation is UX-driven, not statistical:

- **Career-tree gating.** The Stage 3 career tree (`backend/app/services/career_tree.py`) takes a `max_experience_years` filter. A user planning five years out should see branches with `experience_delta_years <= 5` and have senior-tier branches dimmed or hidden. Four tiers give the UI natural grouping without overwhelming it.
- **Decade bucketing.** "Your 20s / Your 30s / Your 40s" views collapse cleanly onto entry / early / mid / senior — roughly 0-1 / 1-4 / 4-8 / 8+ maps to early-career / late-20s / mid-career / senior-career decades for the median bachelor's-degree graduate.
- **Unlock progression UX.** "This path unlocks at 8+ years experience" is a frontend pattern defined in spec §Frontend Integration Notes. The tier enum is what the badge reads.

**Why four tiers and not three or five?** Three would collapse "4-8 years" and "8+" into one senior bucket, making the CEO-vs-manager distinction disappear. Five would need a separate bucket between 4-8 and 8+ — but the 10-category midpoint table jumps from 7 (cat 9) to 9 (cat 10) to 12 (cat 11), so there's no clean natural break.

**DQ expectation.** All four tiers must be represented across the 765-row Silver table. Observed from the EDA spot checks: Retail Salespersons (`41-2031`) = entry, Software Developers (`15-1252`) = mid, Chief Executives (`11-1011`) = senior. Senior-tier share is expected to be 5-30% of rows (CEOs, surgeons, senior management, experienced-only occupations).

### Data Collection Provenance

| Field | Values | Meaning for Downstream Agents |
|-------|--------|-------------------------------|
| `domain_source` | `Incumbent` / `Occupational Expert` | Indicates the measurement mode. Incumbent rows are survey-based with sample sizes and standard errors; Expert rows are panel-based with neither. For occupations where BOTH sources contribute rows to the same occupation × scale, the percentages still sum to 100 — it's one distribution per (occupation, scale) regardless of how many sources fed it. |
| `recommend_suppress` | `N` / `Y` / `n/a` | `N` = data is reliable. `Y` = O*NET recommends suppressing this specific (occupation, scale, category) row due to a small sample or unreliable estimate. `n/a` = not applicable (always present on Expert rows, since there's no sample-based reliability judgment to make). 2.4% of rows overall are flagged `Y`; 2.2% on RW specifically. |
| `n` | integer | Sample size. Always populated (0% null in EDA), even on Expert rows. Median 23, p95 40. |
| `lower_ci_bound` / `upper_ci_bound` | double | 95% confidence interval on `data_value`. Populated only on a subset of Incumbent rows where CI was computed (17,009 of 35,998 rows; 52.75% null). Paired — both are populated or both are null. |
| `standard_error` | double | Populated exactly when `domain_source = 'Incumbent'` (1:1 with the Incumbent/Expert split). 23.9% null. |

**`recommend_suppress` propagation into Silver.** The transformer sets `suppress_flag = TRUE` on a Silver row if **any** contributing Bronze row (across all categories for that occupation's RW scale) has `recommend_suppress = 'Y'`. In the real 2026-04 data, **zero occupations have all-RW rows suppressed** (EDA confirms), so `suppress_flag=TRUE` on the Silver table is reserved for chaos-monkey synthesis today. If the real-world `suppress_flag` rate rises above zero in a future O*NET release, the DQ rule that caps `recommend_suppress='Y'` rate at 5% will catch it at Bronze.

### Update Cadence

O*NET publishes numbered releases roughly 2-4 times per year (current: 30.2). Each release is a **complete database replacement**, not an incremental update — there is no cross-release diff mechanism, and old survey data for an occupation is overwritten when O*NET re-surveys it. The `date` field on each ETE row captures when that specific (occupation, scale) was surveyed; values span 06/2008 to 08/2025, with a peak in 08/2021 (3,813 rows) reflecting a post-COVID survey wave.

**What changes between O*NET versions (for ETE specifically):**
- **Occupation coverage** drifts. New O*NET-SOC detailed codes get added (recently-added occupations initially appear with no ETE data). Old codes get re-surveyed, shifting their category distributions.
- **Scale category counts do NOT change** across minor releases. RL=12, RW=11, PT=9, OJ=9 has been stable for multiple release cycles. If this ever changes, the category-count DQ rule would catch it immediately.
- **`date` field distribution** shifts each release as new survey waves complete.
- **The spec's "~1,016 occupations" figure** refers to O*NET's Occupation Data master table, not the ETE file. ETE covered 878 occupations as of 30.2. Downstream agents should NOT calibrate row-count thresholds against 1,016; use 878 (or the BLS-truncated 765) as the reality.

### Known Gotchas

These are the edge cases that will trip up any downstream agent that doesn't read this section carefully:

| Gotcha | Description | Impact | Notes for downstream agents |
|--------|-------------|--------|-----------------------------|
| **Bimodal distributions force conservative tie-breaking** | 754 of 878 occupations (85.9%) have **no single RW category above 50%**. Many have two distinct peaks. `41-2031.00` Retail Salespersons is the canonical example: cat 1 = 39.75% (None) and cat 5 = 32.02% (6 months–1 year). Weighted median walks cumulatively and lands at cat 5 (midpoint 0.75 yr). Tier = entry (because 0.75 yr falls in 0–1 range). | A naive "mode-based" implementation would pick cat 1 and report 0 years; the weighted-median-across-cumulative rule correctly lands at cat 5 instead. Both answers happen to land in "entry" here, but the scalar differs meaningfully (0 yr vs. 0.75 yr). | @dq-rule-writer: the `41-2031 tier = "entry"` spot check is safe. **Do NOT write `41-2031 experience_category_median <= 3`** — that would fail on real data (actual median cat = 5). Assert tiers, not category numbers. |
| **Suppressed rows in RW are rare and never exhaustive** | Only 2.2% of RW rows (209/9,658) carry `recommend_suppress = 'Y'`. Zero occupations have all eleven RW rows suppressed. Zero RW rows hit `data_value = 100.0` (no single-category-100% case). | The Silver `suppress_flag = TRUE` path has **zero real-world triggers today**. Test coverage for that branch must be synthetic (chaos monkey). | @test-writer / @chaos-monkey: both "all suppressed" and "single-category 100%" cases are synthesized, not drawn from real data. Chaos manifests must include them. |
| **Partial scale coverage does not exist in ETE** | Unlike Work Context (where 16 occupations have 57-row partial coverage), ETE's 878 occupations each have the **exact** expected category counts for all four scales (RL=12, RW=11, PT=9, OJ=9 for every occupation). No partial-coverage cases. | Simplifies DQ — the per-(occupation × scale) row-count rule is a hard equality, not a range. | @dq-rule-writer: can assert exactness, not tolerance. If a future release introduces partial coverage, the rule will catch it. |
| **~93 "All Other" / Military occupations missing by design** | Of the 138 O*NET codes not in the ETE file (1,016 – 878), ~93 are the "All Other" residual categories and Military codes documented in the main O*NET section. The remaining ~45 are recently-added O*NET codes where the ETE survey has not yet been conducted. | Expected and structurally identical to Work Activities / Work Context. Silver zone should filter these rather than treating their absence as a DQ failure. | @dq-rule-writer: do NOT enforce "every Occupation Data SOC has an ETE row." The main O*NET section's guidance on the 93-residual count applies identically here. |
| **Retail salesperson scalar is 0.75 yr, not 0 yr** | The EDA confirms Retail Salespersons' weighted median lands at cat 5 (0.75 yr), driven by the secondary peak. This is correct — it reflects that while 40% of retail roles need zero experience, 32% need up to a year of prior retail exposure. | Don't hand-tune the UI to expect "0 years" for retail. The tier is entry either way, but the scalar matters for `experience_delta_years`. | @mcp-engineer: surface the scalar faithfully. A user asking "how many years of experience do I need to be a retail salesperson?" should see 0.75 years (or ≈9 months), not "no experience." |
| **One RL row at `data_value = 100.0`** | A single RL-scale row has `data_value = 100.0` — every respondent chose the same education category. Never happens on RW. | Bronze `data_value` range rule should tolerate `≤ 100.0` inclusive. `≤ 100.01` is a defensive widening against float noise. | @dq-rule-writer: exact-100 is valid on RL, impossible on RW in current data. |
| **`n` is always populated** | Spec Raw schema marks `n` as optional; in practice it's 100% populated. The Optional flag is defensive against future O*NET releases. | Silver can safely compute on `n` without null-guarding. | @dq-rule-writer: can lift the Bronze `n` non-null rule from optional to P0 if desired, or leave at P1 to stay aligned with the spec schema. |

### PII Risk: NONE

Same posture as the main O*NET section — ETE publishes **occupation-level aggregate statistics only**, derived from anonymized Department of Labor surveys. No individual respondent identifiers, no worker-level records, no location data, no financial or health PII. The ETE file is narrower than Work Activities/Context in this respect: it contains ONLY percent-frequency distributions per (occupation × scale × category), plus survey metadata (sample size, SE, CI bounds, date, domain_source). Every single field is an aggregate.

License: Creative Commons Attribution 4.0 International (CC BY 4.0). Attribution required on any downstream product that surfaces ETE-derived values — the existing O*NET attribution in MCP responses covers this.

**Notes for @pii-scanner:** `bs:pii-scanner` is formally skipped under the onet-experience-requirements spec with the justification "governance/domain-context.md O*NET ETE section confirms no personal data — all fields are occupation-level aggregates from anonymized DOL surveys. License CC BY 4.0."

### Canonical Source Paths

| Artifact | Path |
|----------|------|
| Ingestor class (8th subclass of `OnetBaseIngestor`) | `src/raw/onet_ingestor.py::OnetExperienceIngestor` |
| Source file (within ZIP) | `Education, Training, and Experience.txt` |
| Local cache | `data/raw/onet_cache/Education, Training, and Experience.txt` (file does not yet exist in cache — extracted on first ingest) |
| ZIP source | `https://www.onetcenter.org/dl_files/database/db_30_2_text.zip` |
| Bronze parquet (sample) | `data/bronze/iceberg_warehouse/bronze/onet_experience/data/00000-0-f09a19fa-5466-46ed-a39d-58f4db0dac5e.parquet` |
| Silver table | `base.onet_experience_profiles` (via `src/silver/onet_experience_transformer.py`) |
| Silver conceptual / logical / physical models | `governance/models/silver-base-onet-experience-{conceptual,logical,physical}.md` |
| EDA report | `governance/eda/raw-onet-experience-eda.md` |
| Spec | `docs/specs/onet-experience-requirements.md` |
| Tier-threshold approval | `governance/approvals/onet-experience-requirements-open-decisions.md` (human-approved 2026-04-16) |
| Business glossary terms | BT-117 (Related Work Experience), BT-118 (Experience Tier) in `governance/business-glossary.json` |

### Concept Mapping Guidance (ETE-Specific Delta)

The O*NET section above already maps `onet_soc_code` → Occupation Identity, `element_id` → Content Model dimensions, and `scale_id` → Measurement Scale. ETE adds no new entity types but introduces four derived business concepts that feed downstream:

| # | Business Concept | Plain English Name | Source | Category | Priority |
|---|------------------|--------------------|--------|----------|----------|
| 1 | experience_years_typical | Typical Years of Prior Experience | weighted median of RW distribution → midpoint lookup → average across O*NET details | Career Gating — Scalar | CORE |
| 2 | experience_tier | Experience Tier | threshold bucketing of `experience_years_typical` (0-1/1-4/4-8/8+) | Career Gating — Classifier | CORE |
| 3 | experience_category_median | RW Weighted Median Category (1-11) | intermediate output of the weighted-median walk | Provenance | EXTENDED |
| 4 | experience_distribution | Full RW Distribution (JSON) | verbatim percent-frequency vector per occupation | Diagnostic / Future Use | OPTIONAL |

**Gold projection:** these concepts surface on `consumable.career_branches` as `related_experience_years` (for the target of a branch), `related_experience_tier`, `source_experience_years` (for the source occupation), and `experience_delta_years = related - source` (NULL-propagating when either side is missing). MCP tool `get_career_branches` exposes all four fields.

### AI-Ready Considerations (ETE-Specific)

| Consideration | Recommendation | Notes for @mcp-engineer |
|--------------|---------------|------------------------|
| Primary user questions | "How much experience do I need for [occupation]?" "What jobs can I get with 2 years of experience?" "What careers unlock at 8+ years?" "How much more experience would I need to move from [A] to [B]?" | Map to `related_experience_years` / `related_experience_tier` / `experience_delta_years` fields on `get_career_branches`. Support filter by `max_experience_years` (exists in `backend/app/services/career_tree.py::build_tree` per spec §Zone 5). |
| Scalar vs. distribution | Return the scalar by default (`experience_years_typical`). Only surface the full distribution JSON if the user asks for a breakdown ("how varied is experience for this role?"). | Keep `experience_distribution` available as an optional detail field on the MCP response but do not render it by default — the scalar is the user-facing number. |
| Bimodal explanation | When a user sees an unexpected "0.75 years" for retail (where their intuition says "no experience"), explain: "Most retail jobs accept zero experience, but roughly a third prefer up to a year of prior retail work. The typical prior experience across the full labor market is about 9 months." | Add a templated "bimodal explanation" response for occupations with distribution split > 20/20 at two peaks. Category-5-or-1-dominant Retail is the archetypal case. |
| Tier interpretation | "entry" ≠ "no experience required"; it means "0-1 years typical." Communicate clearly. | MCP response should spell out the tier range: `"experience_tier": "entry", "experience_tier_range": "0-1 years typical"`. |
| Coverage-gap disclosure | 93 of 832 BLS-SOCs have no ETE data (the "All Other"/Military residuals). A user querying those occupations should be told ETE data is not available, not shown a zero value. | Same guidance as Anthropic coverage-gap handling: do NOT silently substitute zero. Return `"experience_tier": null` and include a `"data_availability": "no_ete_data"` field. |

### Assumptions (All User-Approved)

Unlike most domain-context sections, ETE has **zero user-deferred assumptions**. Every design decision that could have been open is pinned to a human approval:

- **Tier thresholds (0-1/1-4/4-8/8+).** Approved 2026-04-16.
- **"Over 10 years" midpoint = 12.** Approved 2026-04-16.
- **Multi-detail aggregation = unweighted average.** Approved 2026-04-16 (matches existing O*NET Silver precedent).
- **Filter vs. dim branches in the UI.** Deferred to a frontend spec — pipeline-side behavior is filter/hide; visual treatment is a downstream concern.

All four are captured with signatures in `governance/approvals/onet-experience-requirements-open-decisions.md`.

### Confidence Notes (ETE-Specific)

**High confidence:**
- Scale semantics (RL/RW/PT/OJ), element IDs, and category counts — externally defined by O*NET, verified against 35,998 real rows in EDA.
- RW is the right scale for career-tree gating (others are ingested for completeness but unused downstream).
- Weighted-median-across-cumulative algorithm — the only defensible scalar collapse given 85.9% of occupations have no dominant category.
- BLS-SOC truncation-and-collapse pattern — identical to existing O*NET Silver precedent.
- PII posture (none, CC BY 4.0) — occupation-level aggregates only.
- Tier thresholds and "Over 10 years" midpoint — human-approved, pinned in approvals file.
- Row counts (878 O*NET details → 765 BLS-SOC roots) — measured, not estimated.

**Medium confidence:**
- Whether unweighted averaging across O*NET details is the right multi-detail strategy for the 63 BLS SOCs with fan-out. Employment-weighted would be better but requires a BLS cross-join not currently in the pipeline. Acceptable for hackathon; revisit post-hackathon.
- Whether the 8-year senior cutoff is the right UX break. Could plausibly be 7 or 10 years; 8 was chosen to pair cleanly with the decade-bucketing UX narrative ("Your 30s → Your 40s").
- Stability of the 878-occupation ETE coverage footprint across future O*NET releases. Spec documents 800–900 as the Bronze tolerance; real drift could push out of range.

**Low confidence / Needs post-hackathon revisit:**
- Whether to surface `experience_distribution` (the JSON vector) in any user-facing UI or keep it purely as a backend diagnostic.
- Whether the Silver-level `suppress_flag` will ever be TRUE on real data. Zero triggers in O*NET 30.2; chaos-only coverage today.
- Whether to add PT (in-plant training) or OJ (on-the-job training) as secondary signals in a future spec — both are already ingested into Bronze and would require only a new Silver transformation to surface.

---

## EADA (Equity in Athletics Disclosure Act)

> Finalized 2026-04-30 by @bs:domain-context, replacing the provisional 2026-04-30 stub written by @bs:data-analyst during raw-zone EDA for `docs/specs/full-pipeline-eada.md`. The EDA report at `governance/eda/full-pipeline-eada-raw-eda.md` remains the authoritative numeric backing for column pins, distribution stats, and overlap measurements; this section is the synthesis the rest of the pipeline reads.

### Domain Identification
**Domain.** U.S. higher-education intercollegiate athletics financial reporting. Mandated annually by §485g of the Higher Education Act (Equity in Athletics Disclosure Act, 1994) for any postsecondary institution that receives Title IV federal student aid and operates at least one intercollegiate athletics program. The disclosure is institution-level and public.

**Sub-domain.** Institution-totals athletic finance (revenue, expense, recruiting). Per-sport / per-team detail (`Schools.xlsx`, `SPORTSCODE`-keyed) is **not in scope** for FutureProof.

**Why FutureProof cares.** EADA carries the only authoritative institution-level dollar figure for athletic spend nationwide. Combined with IPEDS Finance, it is the input set for the forward-looking `consumable.institution_aura` table — a "brand gravity" signal applied to school cards and the school-picker.

### Provider and Acquisition

| Aspect | Value |
|---|---|
| Provider | U.S. Dept. of Education / Office of Postsecondary Education (OPE) |
| Front-end | `https://ope.ed.gov/athletics/` (Angular SPA, "Custom Data Cutting Tool") |
| Backend (unauthenticated, used by ingestor) | three pinned endpoints below |
| User-Agent observed accepted | `FutureProof/0.1 (jeff@hyenastudios.com)` |
| License | U.S. Government Work — public domain |

The SPA is not the API. The ingestor must hit the SPA backend directly. Three endpoints, all GET, all unauthenticated:

| Endpoint | Returns |
|---|---|
| `GET https://ope.ed.gov/athletics/api/dataFiles/years` | JSON array of available reporting years, e.g. `[2003, 2004, …, 2024]`. |
| `GET https://ope.ed.gov/athletics/api/dataFiles/fileList` | JSON list of every available zip with `FileName`, `Year`, `Format`, `LinkName`, `Description`. |
| `GET https://ope.ed.gov/athletics/api/dataFiles/file?fileName=<FileName>` | The zip itself, `application/octet-stream`. |

Two file packages exist per year:

1. `EADA_<YYYY-YYYY>.zip` (~12 MB) — contains `InstLevel.xlsx` (institution-level totals), `Schools.xlsx` (per-team rows), plus SAS / SPSS / Word codebooks. **This is the package we use.**
2. `EADA_All_Data_Combined_<YYYY-YYYY>_SAS_SPSS_EXCEL.zip` — bundled multi-format institution-only file. Not used.

### File Structure (Critical Modeling Fact)

EADA ships institution totals as a **separate file**, not as a marker subset of a mixed file. This is unlike many federal datasets (where you filter by a sentinel column). Inside `EADA_<YYYY-YYYY>.zip`:

| File | Grain | Rows (2022–23) | Cols | FutureProof? |
|---|---|---:|---:|---|
| `InstLevel.xlsx` | one row per `(unitid, academic_year)` | 2,040 | 168 | **Ingested.** |
| `Schools.xlsx` | one row per `(unitid, SPORTSCODE, academic_year)` | 17,886 | 129 | **Not ingested.** |

**Design implication for @bs:dq-rule-writer and the ingestor:** because we read `InstLevel.xlsx` directly, **no in-pipeline filter is needed**. The earlier spec model "filter mixed file on `SPORT_CODE IS NULL`" was based on an incorrect mental model. RAW-EAD-012 (post-filter row count within 1% of distinct UNITIDs) becomes a tautology under the corrected model and should be dropped or re-targeted.

### Grain
- **Primary grain:** `(unitid, reporting_year)`. 2,040 rows in the 2022–23 cycle (`reporting_year = 2022`, the academic-year start).
- Reporting year has **no in-file column**; it is encoded only in the filename. The ingestor stamps `reporting_year` as a constant per cycle.
- One row per institution per year by construction — no deduplication needed.

### Reporting Cycle
- Academic year, Jul–Jun. Filenames use the `YYYY-YYYY` form (`EADA_2022-2023.zip`).
- We stamp `reporting_year = academic_year_start` (e.g., 2022 for the 2022–23 cycle), matching the College Scorecard / IPEDS finance year convention so all education sources align on the same year axis.
- Submission deadline: Oct 15 of the year following the reporting cycle. Public release: typically the following spring.

### Column Naming Convention (Critical Pin)

EADA mixes lowercase identity columns with uppercase monetary columns within the same file. The 2022–23 column names that the ingestor and downstream consumers must use:

| Concept | Actual column (2022–23) | Type | Notes |
|---|---|---|---|
| IPEDS institutional ID | `unitid` (lowercase) | int-like string | NOT `UNITID`. |
| Institution name | `institution_name` (snake_case) | string | NOT `INSTNM`. |
| Grand-total expense | `GRND_TOTAL_EXPENSE` | double | Renames to `total_athletic_expenses` in raw schema. |
| Grand-total revenue | `GRND_TOTAL_REVENUE` | double | Renames to `total_athletic_revenue` in raw schema. |
| Recruiting expense | `RECRUITEXP_TOTAL` | double | NO `_TOTAL_TOTAL` double suffix. Renames to `recruiting_expenses`. |
| Athletic enrollment FTE | `EFTotalCount` (also `EFMaleCount`, `EFFemaleCount`) | int | IPEDS 12-month enrollment headcount. See architectural-question below. |
| Sport code | `SPORTSCODE` | int | Only in `Schools.xlsx`; **absent from `InstLevel.xlsx`**. Not used. |
| Athletics classification | `ClassificationCode` / `classification_name` | int / string | 19 distinct conference/division values. |
| IPEDS sector | `sector_cd` / `sector_name` | int / string | IPEDS 9-sector taxonomy. |

**The original spec §3 working assumptions (`EXP_TOTAL_TOTAL`, `REV_TOTAL_TOTAL`, `RECRUITEXP_TOTAL_TOTAL`, `UNITID`, `INSTNM`) are wrong on every monetary and identity column.** The corrected names above are the canon.

### Suppression Sentinels

EADA documentation lists three suppression markers that the ingestor coerces to NULL at raw write:

| Sentinel | Meaning |
|---|---|
| Blank / empty cell | Not reported |
| `-1` | Privacy-suppressed (cohort too small) |
| `-2` | Not applicable / category not offered |

**In the institution-totals file (2022–23) none of these are observed** — institution grand totals are 100% populated. The sentinels are a per-sport phenomenon (in `Schools.xlsx`), where small programs have privacy-suppressed roster counts. The ingestor's sentinel-stripping logic is retained as a defensive measure for future cycles and for the per-team file should we ever choose to ingest it.

### Athletics Taxonomy (`classification_name`)

19 distinct conference/division values:

NCAA Division I-FBS · I-FCS · I (no football) · II (with/without football) · III (with/without football) · NAIA Division I · II · NJCAA Division I · II · III · NCCAA Division I · II · CCCAA · NWAC · USCAA · Independent · Other.

Distribution skews small/2-year. Only 127 D1-FBS institutions in 2022–23 vs. ~700 in NCAA D3 + NJCAA + CCCAA combined.

### Cross-Source Bridging

| Bridge | Method | Coverage (2022–23) |
|---|---|---|
| `bronze.eada.unitid` ↔ `bronze.college_scorecard_institution.unitid` | Direct integer match on IPEDS UNITID | **74.5% (1,519 / 2,040)** |
| `bronze.eada.unitid` ↔ `base.ipeds_finance.unitid` | Direct integer match on IPEDS UNITID | Unmeasured (table not yet built); expected ~75% by IPEDS-Finance's 4-year-skew. |
| `bronze.eada.unitid` ↔ `consumable.career_outcomes.unitid` | Direct integer match | Deferred until consumable build. |

**The 521 missing-from-Scorecard institutions are predominantly 2-year colleges**: NJCAA-I 168, NJCAA-II 118, CCCAA 95, NJCAA-III 90, NWAC 10, USCAA 7. College Scorecard's bachelor's Field-of-Study file is structurally 4-year-biased.

**Calibration for BSE-EAD-009.** The spec's 95% cross-source coverage threshold is incompatible with the 74.5% measured ceiling. The base-zone DQ threshold for `fte_source_available` should drop to ~75% against `bronze.college_scorecard_institution`, OR the architectural-question below should be resolved in favor of the in-file FTE source.

### OPEN ARCHITECTURAL QUESTION (BLOCKING for silver-zone implementation)

**The decision:** which FTE source feeds per-FTE athletic-spend derivations in `base.eada_athletic_finance` and downstream `consumable.institution_aura.athletic_spend_per_fte`?

| Option | Source | Coverage of EADA universe | Pros | Cons |
|---|---|---:|---|---|
| **A. Cross-source LEFT JOIN** (current spec §5 Decision 3) | `base.ipeds_finance.total_fte_enrollment` | ~74.5% (probably lower) | Single FTE definition shared across all FutureProof per-FTE metrics; consistent with endowment_per_fte. | 521+ EADA institutions get NULL FTE → NULL `athletic_spend_per_fte`. Most are 2-year — exactly the population for which athletic spend is most policy-relevant (Title IX, NJCAA / CCCAA equity). |
| **B. In-file `EFTotalCount`** | `bronze.eada.EFTotalCount` (IPEDS 12-month enrollment, already in EADA) | ~100% (it's in the same row) | No cross-source join, no coverage cliff. Matches the FTE basis used in Knight Commission per-FTE athletic-spend benchmarks. | Athletic-spend-per-FTE uses one FTE definition while endowment-per-FTE uses another (`base.ipeds_finance.total_fte_enrollment`) — two FTE columns in the aura input set. Risk of methodological inconsistency in `consumable.institution_aura`. |
| **C. Hybrid (COALESCE)** | `COALESCE(base.ipeds_finance.total_fte_enrollment, bronze.eada.EFTotalCount)` | ~100% | Best coverage, primary IPEDS-Finance definition where available. | The two FTE columns are not identical (`EFTotalCount` is 12-month headcount; IPEDS Finance is annualized FTE). Mixing them is methodologically dirty unless explicitly versioned (e.g., `fte_source = 'ipeds_finance' \| 'eada_eftotalcount'`). |

**Recommendation for the orchestrator to surface to the spec author + @bs:semantic-modeler before silver-zone implementation:** Option C with explicit `fte_source` provenance column on `base.eada_athletic_finance`. This preserves the IPEDS-Finance primary while not losing the 521 institutions. Aura-score versioning (`aura_score_version`) absorbs the methodological seam.

**Until this decision is made, BSE-EAD-009 must be HELD.** The 95% threshold in the spec assumes Option A and a 4-year-biased universe; under Option B/C the threshold should be ≥99%, and under Option A it should be ~75%.

### Recruiting Zero Rate

17.8% of institutions (363 / 2,040) report exactly $0 recruiting expense. These are **real zeros**, not suppressions. They concentrate in NJCAA II/III, CCCAA, NWAC — programs that don't recruit off-campus.

**Notes for @bs:dq-rule-writer:** RAW-EAD-006 (`recruiting_expenses ≥ 0`) is the correct rule. Do **not** add a "> 0" rule on recruiting; it would false-flag 1 in 6 institutions. Document the zero rate in the data contract so MCP responses can explain it.

### Structural Quirk: Revenue ≈ Expense at the Grand-Total Level

EADA convention requires institutions to report total revenues at least equal to total expenses; any operating deficit is conventionally booked as "direct institutional support" within the revenue total. Therefore at the `GRND_TOTAL_*` level, `revenue ≈ expense` for ~every row.

**Implication for `athletic_subsidy_ratio`:** the "athletics loses money" insight lives in `direct_institutional_support` (a separate EADA column not in the raw schema), not in `GRND_TOTAL_REVENUE − GRND_TOTAL_EXPENSE`. The current planned derivation `athletic_subsidy_ratio = (GRND_TOTAL_EXPENSE − GRND_TOTAL_REVENUE) / GRND_TOTAL_EXPENSE` will be ~0 for ~every institution and is not a usable signal.

This is one of two reasons `athletic_subsidy_ratio` is **deliberately excluded from the aura-score input set** (see Aura Score section below). It is retained as a context column on `consumable.institution_aura` only, not as an aura input. Flagged for @bs:dq-rule-writer: drop or re-derive BSE-EAD-010 ("subsidy P50 > 0"), it cannot pass under the GRND_TOTAL convention.

### PII Assessment

**No PII.** EADA is institution-level public data published by a federal agency under §485g disclosure mandate. There are no individual-level fields — no names, no rosters with identifying detail, no personal addresses. All numeric fields are dollar totals, FTE counts, or coach FTE counts at the institution grain. The `institution_name` and `unitid` fields refer to legal entities, not natural persons.

**Notes for @pii-scanner:** Skip detailed scanning of `bronze.eada` — the data is institution-level public-domain federal disclosure. Justification for the contract: "governance/domain-context.md EADA PII section confirms no personal data — all fields are institution-level totals from a federally-mandated public disclosure (§485g HEA)." This matches the "no PII" precedent already established for College Scorecard, BLS OOH, O*NET, BEA RPP, and Anthropic Economic Index.

### Aura Score (Forward-Looking — drives `consumable.institution_aura`)

**Aura is a neutral brand-gravity signal — explicitly NOT good or bad.** Higher aura = stronger institutional brand presence and resource gravity. Lower aura = quieter / less resourced institution. The frontend renders aura as a visual treatment (glow / particle density / saturation) on the school card; it does not appear as a "rating" or "score out of 10" anywhere a student might confuse it with quality.

**Composite of three direct, non-inverted inputs (all per-FTE or ratio-form):**

| Input | Source | Direction | Note |
|---|---|---|---|
| `endowment_per_fte` | `base.ipeds_finance` | Higher = more aura | Absolute floor of institutional resource gravity. |
| `marketing_ratio` | `base.ipeds_finance` (marketing / total expense) | Higher = more aura | Brand-spend as a share of operating budget. |
| `athletic_spend_per_fte` | `base.eada_athletic_finance` (this source) | Higher = more aura | Athletic visibility / brand reach. |

All three move in the same direction. **There is no inverted input.** Aura is summed, not netted.

**Deliberately excluded from the aura input set:** `athletic_subsidy_ratio`. Two reasons:

1. **Normative overlap with ROI / ERN.** Subsidy ratio carries an implicit "athletics is a money pit / good investment" judgment that overlaps with the financial-return signals already surfaced via `consumable.career_outcomes` (median earnings, debt, ROI). Aura is supposed to be brand-gravity, not financial efficiency — those should not be conflated. This is the §2 Decisions 10 / 11 stance in `docs/specs/full-pipeline-eada.md`.
2. **Mechanical: the GRND_TOTAL convention nulls the signal.** Per the structural quirk above, `athletic_subsidy_ratio` is ~0 for every institution at the grand-total level. Even if we wanted to include it, the raw input set we ingest doesn't carry the subsidy basis (`direct_institutional_support`).

`athletic_subsidy_ratio` survives on `consumable.institution_aura` as a **context column** (for the MCP server to surface when a Gemma user asks about it directly) but is not an aura input.

**Versioning.** `consumable.institution_aura.aura_score_version` is a string column carrying the aura-formula generation. Initial value: `"v0-draft"` pending the aura-score EDA (Task #10 in this pipeline). When the FTE-source decision above is resolved, when aura-score weighting is finalized, and when the EDA validates the input distribution shapes, the version bumps to `"v1"`. Downstream consumers (frontend, MCP) read both the score and the version; mismatched versions are surfaced as a warning rather than silently merged.

**Notes for @bs:semantic-modeler.** The aura input set is fixed (3 inputs, all positive-direction). The aura *formula* (z-score, percentile, capped log, weighted sum) is open and is the subject of the Aura-score EDA gate. This domain context fixes the inputs; the EDA fixes the formula.

### Source Registry Entry

| Zone | Table | Description |
|---|---|---|
| Bronze (raw) | `bronze.eada` | Institution-level athletic finance, one row per `(unitid, reporting_year)`. Brightsmith bronze=raw; the MCP-facing namespace is `bronze`. |
| Base (planned) | `base.eada_athletic_finance` | Renamed / typed / FTE-joined fact, awaiting FTE-source decision above. |
| Consumable (planned) | `consumable.institution_aura` | Aura composite, joined to IPEDS Finance and Endowment. |

### Recap: Edge Cases for @bs:dq-rule-writer

| Observation | Recommendation |
|---|---|
| All three monetary fields are 100% non-null in 2022–23 | Tighten RAW-EAD-007 / 008 / 009 from ≥95% / ≥95% / ≥80% to ≥99% non-null. |
| 17.8% recruiting at $0 (real zeros) | Keep RAW-EAD-006 as `≥ 0`. Do not add `> 0`. |
| `unitid` 100% non-null, 100% unique | RAW-EAD-002 / 003 trivially hold; consider promoting to P0 invariants. |
| `total_athletic_expenses > $100M` for 60 D1-FBS institutions | RAW-EAD-011 holds with margin. |
| `total_athletic_expenses == 0` is currently 0 rows | Add a P1 rule "expense > $0" to catch future data corruption. |
| RAW-EAD-012 (post-filter row count) | Drop or weaken to "row count == file row count" — the per-team filter is gone. |
| BSE-EAD-009 (95% cross-source FTE coverage) | **Hold pending FTE-source architectural-question above.** |
| BSE-EAD-010 (subsidy P50 > 0) | **Drop or re-derive.** The GRND_TOTAL convention nulls the signal. |

---

## IPEDS Finance (F1A / F2 / F3 + EFIA + HD)

> Finalized 2026-04-30 by @bs:domain-context against the **actually-landed FY2022 bronze table** (`bronze.ipeds_finance`, 2,683 rows, snapshot `982081695100705470`). Supersedes the earlier draft of this section that was written against a hypothetical FY23 cycle (NCES had not yet published FY23 finance files at ingest time — see "Cycle vintage" below). The full EDA at `governance/eda/raw-ingest-ipeds-finance-eda.md` is the authoritative numeric backing for everything below; this section is the synthesis the rest of the pipeline reads.

### Domain Identification

**Domain.** U.S. higher-education institutional finance reporting. Mandated annually for any postsecondary institution participating in Title IV federal student-aid programs. The IPEDS Finance Survey is split into three forms keyed to institutional control + accounting basis, then unioned in this pipeline into a single per-institution-per-fiscal-year row.

**Sub-domain.** Institution-level functional-expense totals (instruction + institutional support), end-of-year endowment value, and 12-month full-time-equivalent (FTE) enrollment. Per-sport, per-program, per-function-sub-category detail (e.g., research, public service, scholarships) is **not in scope** for FutureProof.

**Why FutureProof cares.** IPEDS Finance is the only authoritative source nationwide for institution-level dollar figures on what schools spend on teaching vs. administration. Combined with EFIA (12-Month Instructional Activity), it produces the per-FTE expense ratios and the `marketing_ratio` (institutional support / instruction) signal — a "brand-vs-teaching-spend" lens. The base/consumable per-FTE derivations and `marketing_ratio` interpretation live downstream of this raw zone. The eventual fusion with EADA athletic-finance into `consumable.institution_aura` (forward-looking "brand gravity" composite) is also out of scope here — see `docs/specs/raw-ingest-eada.md`.

Spec: `docs/specs/full-pipeline-ipeds-finance.md` (v1.3-locked).
Pre-flight: `governance/eda/raw-ingest-ipeds-finance-preflight.md` (resolves the v1.2 column-code TBDs).
Full EDA (FY2022 actually-landed): `governance/eda/raw-ingest-ipeds-finance-eda.md`.

### Provider and Acquisition

| Aspect | Value |
|---|---|
| Provider | National Center for Education Statistics (NCES), part of U.S. Dept. of Education |
| Front-end | `https://nces.ed.gov/ipeds/datacenter/` (Compare Institutions → Finance) |
| Backend (used by ingestor) | bulk CSV download per form, URL pattern `https://nces.ed.gov/ipeds/datacenter/data/{name}.zip` (and `_Dict.zip` for dictionaries) |
| User-Agent observed accepted | `FutureProof/0.1 (jeff@hyenastudios.com)` |
| License | U.S. Government Work — public domain |
| Authentication | None — all four file families (F1A / F2 / F3 / EFIA / HD) ungated |

The ingestor pulls **five** zipped CSVs per cycle (three Finance forms + EFIA + HD), unions the three Finance files in raw with a `report_form` column, LEFT JOINs EFIA on UNITID, and applies the HD-derived 4-year-bachelor's-or-above filter. Stops at `bronze.ipeds_finance`.

### Form Mix and Reporting Basis

IPEDS publishes the Finance Survey on three separate forms:

| Form | Population | Accounting basis | FY2022 row count (post-HD-filter) | Pct of post-filter universe |
|---|---|---|---:|---:|
| **F1A** | Public 4-year institutions | GASB (governmental — Statement 34/35 functional-expenses block in Part C) | 803 | 29.9% |
| **F2** | Private nonprofit 4-year institutions | FASB (Section E functional-expenses block) | 1,593 | 59.4% |
| **F3** | Private for-profit institutions | proprietary (narrower schedule, post-2014-15 schedule revision) | 287 | 10.7% |

The accounting-basis distinction matters analytically only at the margins — the line-item dictionary definitions for "Instruction" and "Institutional support" are byte-equivalent across F1A/F2/F3 (FARM ¶703.x for institutional support; the same paragraph anchors instruction). At the grand-total level used here, GASB-vs-FASB differences are immaterial. They do affect what is **categorized into** instruction vs. institutional support at the function level (e.g., GASB rolls some operations-and-maintenance into institutional support that FASB books separately), so cross-form per-form analysis on the marketing_ratio is more interpretable than a single global cut. Consumable layer should preserve `report_form` to enable that segmentation.

12 institutions in F2 carry `CONTROL=1` (public) — these are state-related private hybrids (Penn State, Pitt, Temple-class) that elect FASB and file F2. Expected; matches NCES treatment.

### The Four Bronze Fields (Plain English)

These are the four columns the bronze table carries forward into base. All other functional-expense breakouts (research, public service, academic support, student services, scholarships) are intentionally not pulled — they are out of scope for the FutureProof "what does this school spend on teaching vs. administration" lens.

| Bronze field | Plain English | F1A code | F2 code | F3 code | Source survey |
|---|---|---|---|---|---|
| `instruction_expenses` | Total annual expenses on direct instruction — faculty salaries, instructional materials, departmental research conducted in service of teaching. The "educational product" line. | `F1C011` (Part C, "Instruction – Total") | `F2E011` (Section E, "Instruction – Total") | `F3E011` (post-2014-15; the `1` suffix denotes "Total amount" and was a v1.2 spec error to omit) | IPEDS Finance |
| `institutional_support_expenses` | Total annual expenses on day-to-day operational support — executive direction, fiscal/legal/administrative ops, public relations, fundraising, recruiting/marketing, administrative computing. The "overhead" line. | `F1C071` | `F2E061` | `F3E03C1` (post-2014-15 schedule revision; 100% non-null on FY2022 — the pre-2014-15 belief that F3 omits this is **refuted**) | IPEDS Finance |
| `endowment_value` | End-of-year market value of an institution's endowment funds. | `F1H02` | `F2H02` | **N/A** — F3 has no `F3H` family at all; for-profit institutions do not maintain endowments. NULL for 100% of F3 rows by design. | IPEDS Finance |
| `total_fte_enrollment` | 12-month full-time-equivalent enrollment, computed as `COALESCE(FTEUG,0) + COALESCE(FTEGD,0) + COALESCE(FTEDPP,0)` — undergraduate + graduate + doctor's-professional-practice (med/law/dental/vet). NULL only when all three components are NULL. | `FTEUG`, `FTEGD`, `FTEDPP` | (same EFIA source) | (same EFIA source) | **EFIA** (12-Month Instructional Activity), NOT EFFY (which is headcount) |

The pre-2014-15 belief that "F3 omits institutional support" is **incorrect for modern cycles** — the F3 schedule was revised in the 2014-15 collection cycle to mirror F1A/F2's six functional categories.

### Critical Survey-Choice Pin: EFIA, NOT EFFY, NOT `EFTOTLT`

This is the single highest-risk field-selection decision in the spec, and the v1.2 spec had it wrong. Three sub-points all bite, and any of them ingested wrong produces silently corrupted per-FTE math:

1. **The FTE-bearing file is `EFIA{YYYY}.zip`** (12-Month Instructional Activity). It is published one row per UNITID (FY2022: 6,036 rows / 6,036 distinct UNITIDs; no `LEVEL` / `LSTUDY` / `EFFYALEV` breakdown column present). **No dedup filter required.**
2. **NOT `EFFY{YYYY}.zip`.** That file is the unduplicated 12-month *headcount* file, broken out by `EFFYALEV` / `LSTUDY` (one row per institution per student level, ~17,000 rows for ~6,000 institutions). Joining naively against `EFFY` fans-out finance rows by student level and inflates per-FTE values by ~3×. The v1.2 spec named "EFFY/E12" — the operative file is **EFIA**.
3. **NOT `EF{YYYY}A.EFTOTLT`.** That column is a fall-snapshot **headcount**, not an annualized FTE. Using it would systematically deflate per-FTE values for institutions serving large part-time populations (community colleges, online-heavy schools, R2s with PT graduate cohorts) — exactly the populations FutureProof's robustness rule targets.

There is **no `FTE_TOTAL` or `FTE` column in any IPEDS file**. Total FTE must be computed:

```sql
total_fte_enrollment =
  COALESCE(FTEUG, 0) + COALESCE(FTEGD, 0) + COALESCE(FTEDPP, 0)
-- NULL only if all three components are NULL
```

`FTEDPP` (doctor's-professional-practice) is populated for ~14% of institutions (medical, dental, law, veterinary schools); excluding it would deflate per-FTE values for those institutions by 5–15%. The reported variants `FTEUG/FTEGD/FTEDPP` are preferred over the estimated `EFTEUG/EFTEGD` — the EFIA dictionary states the reported value defaults to the estimate when the institution declines to provide one, so `FTEUG` is "best institution-confirmed value, falling back to NCES estimate." Aggregate national delta between reported and estimated is ~0.1%; per-institution drift is rare.

### HD Filter — IPEDS-Native 4-Year-Bachelor's-or-Above

Pipeline applies `ICLEVEL = 1 AND HLOFFER >= 5` from the **HD** (Header) file, paired by **calendar year matching fiscal year** (FY2022 → `HD2022.csv`).

- `ICLEVEL = 1` means "4 or more years"
- `HLOFFER >= 5` means at least bachelor's, post-bacc cert, master's, post-master's, or doctorate

This is IPEDS-native; no College Scorecard `PREDDEG` dependency (the v1.0 spec mixed taxonomies). Result on FY2022: 2,683 / 6,256 HD UNITIDs (42.9%) pass the filter, narrowing the unioned-finance universe (1,936 F1A + 1,782 F2 + 2,120 F3 = 5,838 source rows) down to the landed 2,683-row bronze table.

### Cycle Vintage — FY2022, Not FY24

The v1.3 spec narrative was written assuming FY24 (the spec's working assumption). **The actually-landed bronze table is FY2022 (academic year 2021-22)** — NCES had not yet published FY24 finance files at ingest time (`F2324_F1A.zip` returns HTTP 200 with a 1.2KB 404-error HTML page as of 2026-04-30). FY2022 is the most-recent fully-published cycle and the year the pre-flight verified column codes against.

The cycle is a **runtime parameter** (`fiscal_year=2022` in `domain/sources/ipeds_finance.yaml`'s `fetch.ipeds_finance.fiscal_year` field, threaded through to the ingestor's constructor argument). Promoting to FY23 or FY24 once NCES publishes is a parameter change, not a code change. NCES publishes Finance on a roughly 16-month lag from fiscal-year end; expect FY24 to land in NCES Data Center around Sep 2026.

| Component | FY2022 file | Pairing window |
|---|---|---|
| Finance F1A / F2 / F3 | `F2122_F{1A,2,3}.zip` | Fiscal year ending 2022 (typically Jul 2021 – Jun 2022) |
| EFIA | `EFIA2022.zip` | Academic year 2021-22 (Jul 2021 – Jun 2022) |
| HD | `HD2022.csv` | Calendar 2022 institutional metadata |

All three reflect the same 12-month window ending June 30, 2022. Pairing convention (`F{YY1}{YY2}` for finance, single-year `{YYYY}` for EFIA/HD) is stable across recent IPEDS revisions.

### The Endowment Imputation Caveat (Methodologically Important)

IPEDS publishes a parallel `X{code}` column for every numeric field, indicating the value's provenance: **R**=reported by institution, **A**=NCES-analytical/derived (typically prior-year ratio applied to current-year revenue, or mean-of-similar-institutions), **P**=prior-year carryforward, **Z**=imputed using zero, **N**=N/A.

On FY2022, the imputation pattern splits into two distinct populations:

| Field family | Imputation prevalence | Interpretation |
|---|---|---|
| `instruction_expenses` (XF1C011/XF2E011/XF3E011) | ≤0.52% A+P+Z across all three forms (≥99.4% R) | Bureau imputation is immaterial. Accepting as raw is methodologically clean. |
| `institutional_support_expenses` (XF1C071/XF2E061/XF3E03C1) | ≤0.14% A+P+Z across all three forms | Same — immaterial. |
| `endowment_value` (XF1H02 on F1A, XF2H02 on F2) | **31.10% on F1A, 25.31% on F2** carry "A" (NCES-analytical/imputed) | **Significantly imputed.** Endowment is a balance-sheet measure with a fixed publication date; institutions that miss the EOY reporting deadline have endowment imputed by NCES from a prior-year value scaled by a market-return factor. The methodology is documented and stable. |

**v1.3 policy (§2 Decision #8): accept bureau-imputed values as raw values per the spec; do not store the X-flag column.** This is well-calibrated for instruction and institutional support (immaterial) and accepted-with-known-tradeoff for endowment (25-31% of non-null F1A/F2 endowment values are model-imputed rather than institution-reported). Suppressing imputed endowment would drop coverage from ~76% non-null to ~56% non-null and force a corresponding loosening of `BSE-IPF-013` to ~50%.

**v1.4 candidate (NOT a v1.3 blocker):** add an `endowment_value_provenance` column to bronze that stores the `XF1H02`/`XF2H02` flag value verbatim (R/A/P), defaulting to NULL on F3. Allows downstream consumers (EADA fusion, longitudinal endowment-trend analyses) to filter to institution-reported values when modeling change-over-time, without losing the imputation-allowed values for current-snapshot benchmarking.

### F3 Sparseness — What's Structural vs. Missing

| F3 field | NULL rate | Interpretation |
|---|---|---|
| `instruction_expenses` | 0.0% (287/287 non-null) | Always reported on the post-2014-15 schedule. |
| `institutional_support_expenses` | 0.0% (287/287 non-null) | Always reported. The pre-2014-15 belief that F3 omits this is refuted. |
| `endowment_value` | **100.0% NULL** (0/287 non-null) | **Structural** — F3 has no `F3H` family at all. For-profit institutions do not maintain endowments. **Not a data quality failure**; not a coverage issue. The NULL cascades correctly through `endowment_per_fte` for F3 rows in base/consumable. |
| `total_fte_enrollment` | 1.4% NULL (4/287) | Newly-opened or late-filer for-profit institutions absent from EFIA. |

The 100%-NULL endowment_value on F3 is the single most important structural-NULL pattern in this domain. Downstream `data_completeness_tier` (per spec §6) must classify F3 rows that are otherwise complete as `medium` (one structurally absent field of four), not `low` or `medium-low`. Future data-product specs that filter or rank by `endowment_per_fte` should explicitly surface F3 rows with N/A treatment, not drop them silently.

### Coverage vs. Career Outcomes (Calibrates CON-IFP-008)

Distinct-UNITID overlap with `consumable.career_outcomes` (the existing FutureProof gold table that already drives the school + major picker):

| Metric | Value |
|---|---:|
| `bronze.ipeds_finance` distinct UNITIDs (FY2022, post-HD-filter) | **2,683** |
| `consumable.career_outcomes` distinct UNITIDs | **2,559** |
| Overlap | **2,313** |
| Overlap rate of CO (CON-IFP-008 numerator: ≥90% target) | **90.39%** |
| Overlap rate of bronze | 86.21% |
| In CO not in bronze (`co_only`) | 246 |
| In bronze not in CO (`bronze_only`) | 370 |

**The 9.61% gap is well-explained and not a data-quality issue.** Of the 246 `co_only` UNITIDs:
- ~50% (122/246) are 4-year institutions that pass our `ICLEVEL=1 AND HLOFFER>=5` filter — IPEDS Finance non-filers for FY2022 (predominantly small graduate-only or specialized for-profit institutions, late filers, or recent merges into a parent UNITID).
- ~5% (13/246) are recently-closed institutions (e.g., ASA College closed 2023-02-24, San Francisco Art Institute closed 2022-07-15) — Scorecard backfills outcomes for cohorts that graduated before closure.
- The remaining ~50% are sub-baccalaureate (associate's-only, 2-year, certificate) — expected misses by the spec's 4-year filter.

Of the 370 `bronze_only` UNITIDs: F2=248, F1A=73, F3=49. F1A/F3 entries are dominated by **state-system administrative offices** (e.g., "University of Alabama System Office", "U California-Hastings College of Law") and **specialized graduate-only institutions** (American Film Institute Conservatory, Berkeley School of Theology) that are real IPEDS entities outside Scorecard's earnings-cohort universe.

**CON-IFP-008 calibration:** keep the threshold at ≥90% (matches measured 90.39%). The pass margin is 39 basis points — tight. Add a P2 watch-line at ≥88% so a future vintage drop signals one cycle of warning before a P0-class incident. Document the 246 known `co_only` UNITIDs in the data contract as known-acceptable gap.

### System-Office Outliers (Recurring Pattern, Future Spec Concern)

A recurring pattern across the FY2022 EDA: **public-system administrative offices** (e.g., "LA CCD Office", "U Colorado System Office", "U Hawaii System Office", "U Illinois System Office", "SUNY-System Office", "Vermont State Colleges Chancellor", "Minnesota State Colleges System Office") appear in IPEDS HD with `ICLEVEL=1, HLOFFER>=5` but they are **administrative entities, not degree-granting campuses** — students belong to member institutions. These produce:

- 34 rows with `instruction_expenses = 0` (legitimate — they have no instruction)
- 21 rows with `marketing_ratio > 10×` (the top 10 of which are all system offices — extreme overhead-relative-to-zero-instruction)
- The F1A `marketing_ratio` MAX of 2,340 (LA CCD: $2M instruction / $225M institutional support) is a system office, not an institutional malfeasance signal.

**These are real IPEDS entities, not data errors.** Approximately 25-40 of these UNITIDs exist nationwide. Future spec versions may filter them out at the bronze→base boundary (matching `name ~~ ' Office' OR ' System' OR 'Chancellor'` with anchor-aware matching) — this would drop ~1% of rows, eliminate the entire `>10×` marketing-ratio outlier class, and improve consumable→career-outcomes overlap by removing rows that have no career-outcome counterpart by construction. **Out of scope for v1.3** because it would alter the bronze grain (UNITID-level, faithful to source). Surface to @bs:semantic-modeler for `consumable.ipeds_finance_profile` shaping or downstream EADA fusion (system offices have no athletic program and will fall out of EADA fusion naturally).

### Joining IPEDS Finance Into Other Tables

| Pair | Method | Coverage (FY2022) |
|---|---|---|
| `bronze.ipeds_finance.unitid` ↔ `consumable.career_outcomes.unitid` | Direct integer match on IPEDS UNITID | **90.39% of CO UNITIDs** find a finance row |
| `bronze.ipeds_finance.unitid` ↔ `bronze.college_scorecard_institution.unitid` | Direct integer match | clean (the two share an HD-derived UNITID universe) |
| `bronze.ipeds_finance.unitid` ↔ `consumable.program_career_paths.unitid` | Direct integer match | clean — `program_career_paths` is keyed on the same UNITID |
| `bronze.ipeds_finance.unitid` ↔ `bronze.eada.unitid` | Direct integer match | unmeasured this cycle; expected ~75% (EADA includes 2-year/sub-baccalaureate institutions the IPEDS-Finance HD filter excludes) |

`unitid` is a **long, 6-digit IPEDS identifier** — the same key used by every existing FutureProof institution-keyed table. **Do NOT use OPEID** (Office of Postsecondary Education identifier — different namespace, 6- or 8-digit, not stable across institutional changes). **Do NOT use IPEDS UnitID-7 or any other variant** — there is one canonical UNITID and it is the 6-digit integer carried in the `unitid` column on every existing bronze/consumable table in this repo.

### What's NOT in This Domain

The bronze layer is intentionally minimal — four payload fields plus identity/provenance. The following all live downstream and are explicitly out of scope here:

| Concept | Lives in | Why not here |
|---|---|---|
| Per-FTE derivations (`instruction_per_fte`, `institutional_support_per_fte`, `endowment_per_fte`) | `base.ipeds_finance` (per spec §5) | Per-FTE is a derivation that depends on a separate field (FTE). Raw zone is faithful-to-source per Brightsmith convention. |
| `marketing_ratio` (institutional support / instruction) and its interpretation | `base.ipeds_finance` (computation), `consumable.ipeds_finance_profile` (interpretation) | Same reason — derived signal, not a raw input. |
| `data_completeness_tier` (high/medium/low/insufficient) | `consumable.ipeds_finance_profile` (per spec §6) | Synthesized from non-null counts of independent raw inputs. Not a CIP→SOC crosswalk-confidence tier despite the name overlap. |
| Fusion with EADA athletic-finance into `consumable.institution_aura` "brand gravity" composite | `docs/specs/raw-ingest-eada.md` (downstream spec) | Cross-source fusion. The IPEDS Finance side exposes raw expense passthroughs at consumable specifically to enable this fusion without back-joining to base. |
| Multi-year SCD2 tracking | Out of scope (post-hackathon) | Single-vintage invariant per spec §2 Decision 6. RAW-IPF-013 enforces. |

### Domain Vocabulary (BT-IPF-* Glossary Anchors)

These are the canonical concept definitions that downstream agents (@bs:data-steward, @bs:cde-tagger, @bs:doc-generator) should treat as authoritative for this source. Final BT-IPF-* IDs are assigned by @bs:data-steward.

| Term | Definition | Notes |
|---|---|---|
| **Instruction expenses** | Total annual expenses on direct instruction — faculty salaries, instructional materials, departmental research conducted in service of teaching. The denominator in the marketing ratio. Per FARM ¶703.x ("educational programs of the institution, including credit and non-credit"). | F1A `F1C011` / F2 `F2E011` / F3 `F3E011`. Byte-equivalent across forms. |
| **Institutional support expenses** | Total annual expenses on day-to-day operational support of the institution — executive direction and planning, legal/fiscal operations, administrative computing, public relations/development. Per FARM ¶703.9. Often a proxy for "marketing and administration overhead" in budget transparency analyses. | F1A `F1C071` / F2 `F2E061` / F3 `F3E03C1`. Byte-equivalent across forms (post-2014-15 schedule revision). |
| **Endowment value (end of year)** | End-of-year market value of an institution's endowment funds. **Imputation caveat:** ~25-31% of non-null F1A/F2 values carry the NCES-analytical "A" flag (model-imputed from prior-year value × market-return factor). v1.3 accepts these as raw values per §2 Decision #8. | F1A `F1H02` / F2 `F2H02`. F3 has no `F3H` family (for-profits don't maintain endowments) — coalesces to NULL for 100% of F3 rows. |
| **Total FTE enrollment** | 12-month full-time-equivalent enrollment, sourced from the **EFIA** (12-Month Instructional Activity) survey, **NOT EFFY** (which is unduplicated 12-month headcount, broken out by student level) and **NOT EF Part A `EFTOTLT`** (which is fall-snapshot headcount). Computed as the NULL-safe three-column sum `COALESCE(FTEUG, 0) + COALESCE(FTEGD, 0) + COALESCE(FTEDPP, 0)`, returning NULL only when all three components are NULL. EFIA is published one row per UNITID, no dedup needed. | The single highest-risk field-selection decision in the spec — getting any of the three sub-points wrong produces silently corrupted per-FTE math downstream. |
| **Per-FTE convention** | Convention for normalizing institution-level financial measures by `total_fte_enrollment`, producing per-student measures comparable across institutions of different size. NULL when either operand is NULL or FTE is 0. **No imputation downstream** of the bureau-level imputation NCES already applies (see endowment imputation caveat). | Lives in `base.ipeds_finance`, not raw. |
| **Marketing ratio** | Ratio of `institutional_support_expenses / instruction_expenses`. Higher = relatively more spending on administration/marketing/recruiting vs. teaching. Bounds vary widely across the institutional universe; FY2022 P50 (table-wide) = 0.55, F2 P99 ≈ 5.3, F1A P99 ≈ 12.8 (driven by public-system administrative offices, not real campuses). Per-form thresholds advised — proposed table-wide P99 < 5.0 fires on legitimate state-system administrative offices. | Lives in `base.ipeds_finance` (formula) and `consumable.ipeds_finance_profile` (interpretation), not raw. |
| **`data_completeness_tier`** | Source-data-completeness signal computed from the count of non-null **independent raw inputs** (`instruction_expenses`, `institutional_support_expenses`, `endowment_value`, `total_fte_enrollment`). Values: `high` (4/4), `medium` (2-3/4), `low` (1/4), `insufficient` (0/4). **This is NOT a CIP→SOC crosswalk-confidence tier** — it measures source-field non-null count, not crosswalk match quality. Renamed from `confidence_tier` in v1.1 of the spec to disambiguate. | Lives in `consumable.ipeds_finance_profile`, not raw. |

### PII Assessment

**No PII.** IPEDS Finance is institution-level public data published by NCES under federal disclosure mandate. There are no individual-level fields — no student records, no employee names, no rosters, no addresses. All numeric fields are dollar totals, FTE counts at the institution grain, or balance-sheet measures. The `institution_name` and `unitid` fields refer to legal entities (universities, colleges, system offices), not natural persons.

**Notes for @pii-scanner:** Skip detailed scanning of `bronze.ipeds_finance` — the data is institution-level public-domain federal disclosure. Justification for the contract: "governance/domain-context.md IPEDS Finance PII section confirms no personal data — all fields are institution-level totals from NCES's IPEDS Finance Survey, a federally-mandated public survey under Title IV reporting requirements." This matches the "no PII" precedent already established for College Scorecard, BLS OOH, O*NET, BEA RPP, Anthropic Economic Index, and EADA.

### Source Registry Entry

| Zone | Table | Description |
|---|---|---|
| Bronze (raw) | `bronze.ipeds_finance` | Institution-level financial expenses + endowment + FTE, one row per `(unitid, fiscal_year)`. UNIONs F1A/F2/F3 with `report_form` column, LEFT JOINs EFIA on UNITID, applies HD `ICLEVEL=1 AND HLOFFER>=5` filter. **Landed: 2,683 rows, FY2022, snapshot `982081695100705470`.** Source: NCES IPEDS Data Center. |
| Base (planned) | `base.ipeds_finance` | Renamed / typed / per-FTE-derived fact. Computes `instruction_per_fte`, `institutional_support_per_fte`, `endowment_per_fte`, `marketing_ratio`. |
| Consumable (planned) | `consumable.ipeds_finance_profile` | Public-facing per-FTE expense ratios + `data_completeness_tier`. Exposes raw dollar passthroughs for downstream EADA fusion. |
| Consumable (downstream — `raw-ingest-eada.md`) | `consumable.institution_aura` | "Brand gravity" composite. Uses `endowment_per_fte` and `marketing_ratio` planks from this source. |

### Recap: Edge Cases for @bs:dq-rule-writer (FY2022-calibrated)

| Observation | Count | Recommendation |
|---|---:|---|
| Post-HD-filter row count = 2,683 (NOT 5,000–8,000) | 2,683 | **Revise RAW-IPF-001 from `5,000–8,000` to `2,500–3,200`** before running DQ rules. The 5,000–8,000 band is a v1.0/v1.1 artifact pre-dating the HD filter. Measured 2,683 lands comfortably mid-band. |
| `instruction_expenses` non-null = 100.0% | 2,683/2,683 | RAW-IPF-009 (≥90%) holds with massive margin. |
| `institutional_support_expenses` non-null = 100.0% | 2,683/2,683 | RAW-IPF-010 (≥90%) holds with massive margin. |
| `total_fte_enrollment` non-null = 97.88% | 2,626/2,683 | RAW-IPF-011 (≥95%) holds; flag if drops below 96%. F1A NULL rate is the worst (5.7%, driven by system offices that have no enrollment); keep table-level not per-form. |
| `endowment_value` non-null = 75.77% | 2,033/2,683 | **Tighten RAW-IPF-012 from ≥60% to ≥70%** (5.77pp headroom against measured baseline). The 24% NULL is structural F3 (100% of 287 rows) + 17.95% small F2 + 9.59% F1A (foundation-held endowments reported separately on F1B). |
| F3 endowment NULL = 100% (structural) | 287/287 | Add NEW RAW-IPF-015: `report_form='F3' AND endowment_value IS NULL` for all F3 rows. Codifies the structural NULL as an invariant; future cycles where F3 starts reporting endowment would surface as a rule failure (and signal NCES schedule change). |
| Form mix: F1A 29.9% / F2 59.4% / F3 10.7% | — | Add NEW RAW-IPF-016: F1A ∈ [700,900], F2 ∈ [1400,1750], F3 ∈ [200,350]. Catches a future form-mix shift. |
| Bureau imputation ≤0.52% on instruction/inst-support; **25-31% on F1A/F2 endowment** | — | §2 Decision #8 (accept imputed values) is well-calibrated for instruction/inst-support. For endowment, document the prevalence and consider v1.4 `endowment_value_provenance` flag column. Do NOT flip the policy in v1.3. |
| 34 rows with `instruction_expenses=0`, 16 with `inst_support=0`, 1 with `endowment=0` | — | RAW-IPF-005/006/007 (≥0) hold; do not change to `>0`. The 34 zero-instruction rows are public-system administrative offices (legitimate). |
| `marketing_ratio` (inst_support / instruction) median by form: F1A 0.36, F2 0.63, F3 0.91; P99 by form: F1A 12.8, F2 5.3, F3 10.3 | — | F3's high ratios are the for-profit marketing-spend signal the consumable layer wants to surface, NOT a data quality issue. **Per-form thresholds for BSE-IPF-015 advised** (proposed F1A < 13, F2 < 5.5, F3 < 11). The proposed table-wide P99 < 5.0 would fire on 1.7% of rows including legitimate state-system administrative offices. |
| Instruction-per-FTE table-wide P99 = $78.8K; sole row > $500K is UT Southwestern Med Center | — | BSE-IPF-017 (P99 < $500K) holds — the threshold is a tripwire for the EFFY-headcount-vs-FTE field-selection bug class, not an EDA-driven percentile. Keep as-is. |
| CON-IFP-008 measured = 90.39% (proposed threshold ≥90%) | 2,313/2,559 | **Tight pass — 39 basis points of margin.** Keep the P1 ≥90% threshold; **add a P2 watch-line at ≥88%** so a future-vintage drop gives one cycle of warning. Document the 246 known `co_only` UNITIDs in the data contract. |
| `data_completeness_tier='high'` projected ≈ 73% (CON-IFP-009 proposed ≥70%) | — | Keep the spec at 70% for headroom; document actual baseline at ~73%. |

### v1.4 Amendment — Endowment Provenance Flag, System-Office Filter, Restored source_load_date, A/N Semantic Correction

> Finalized 2026-05-01. Spec: `docs/specs/ipeds-finance-v1.4.md`. EDA: `governance/eda/ipeds-finance-v1.4-flag-eda.md` (narrow-scope flag EDA). Chaos report: `governance/chaos-reports/ipeds-finance-v1.4-chaos.md` (final form filter validation). The v1.4 amendment is a narrow follow-on to the v1.3-locked spec covering four discrete deferred items; it adds one column at raw + base, one column rename + one row-filter + one restored column at consumable, and the corresponding DQ rules and governance artifacts.

**Item 1 — One new column at raw + base (`endowment_value_flag`).** Bronze ingest now captures `XF1H02` (F1A) and `XF2H02` (F2) as a single coalesced `endowment_value_flag` string column. F3 rows have NULL by structure (no `F3H` family). Base passes the column through verbatim. Validated by RAW-IPF-015 (P0 enum check), BSE-IPF-018 (P0 passthrough fidelity), BSE-IPF-019 (P1 per-form prevalence band — F1A 5–15%, F2 12–25%), BSE-IPF-020 (P0 `A`↔NULL coupling invariant). New bronze snapshot `8612278722865929234`; new base snapshot `5533921477059200416`. Both still 2,675 rows.

**Item 2 — One row-filter at consumable (system-administrative-office filter).** A v1.3 final form 8-pattern AND 4-clause-numeric-proxy filter excludes IPEDS rows representing state-system or district-level administrative offices. The 8 name patterns are: `'% office'`, `'% system'`, `'% system %'`, `'%chancellor%'`, `'%central office%'`, `'%system office%'`, `'%district office%'`, `'%sistema universitario%'`. The 4 numeric-proxy clauses (any of which suffices when paired with a name match): `instruction_expenses IS NULL`, `instruction_expenses < 1000000.0`, `total_fte_enrollment IS NULL`, `total_fte_enrollment < 50`. The AND intersection is the deliberate guardrail against false-positives — small teaching institutions whose name happens to match a pattern survive because they have positive FTE. The 8th pattern (`%sistema universitario%`) was added in v1.1 to catch UNITID 242060 Sistema Universitario Ana G. Mendez (the #1 marketing_ratio outlier in FY2023 at MR=5,265.5×, missed by the 7 English-anchored patterns alone). The 4-clause numeric proxy was extended from a 2-clause v1.0/v1.1/v1.2 form (`instruction NULL OR <$1M`) after the v1.4 chaos pass surfaced 9 admin entities with FTE NULL but `instruction_expenses` between $1.73M and $6.83M (above the original $1M floor). FY2023 result: 45 rows excluded; consumable lands at 2,630 rows (snapshot `950547093607535235`). Validated by CON-IFP-014 (P1) — 0 surviving rows match the exclusion clause. Row-count band [base_count - 50, base_count] enforced by CON-IFP-001a (P0 upper bound) + CON-IFP-001b (P1 lower bound).

**Item 3 — One restored column at consumable (`source_load_date`).** v1.3 dropped `source_load_date` at the base→consumable promote; v1.4 restores it as a vintage-observability passthrough (NOT NULL per CON-IFP-015 P0; within 400 days of `promoted_at` per CON-IFP-016 P1). **Explicitly NOT CDE** per spec §6 Data Contract delta — it is metadata about *when bronze was loaded*, not about *how to interpret an analytical column*. Compare with `endowment_value_provenance` (Item 4 below), which DOES change interpretation and IS CDE. Per the standing CDE bar, only interpretation-changing columns are CDE.

**Item 4 — `A`/`N` semantic correction.** The v1.3 EDA §7 narrative inverted the meanings of `A` and `N` (it described `A` as "NCES analytical / model-imputed" and `N` as "Not applicable"). The IPEDS Finance FY2023 dictionary is the AUTHORITATIVE source — it pins `A` = **Not applicable** and `N` = **Imputed using Nearest Neighbor procedure**. FY2023 empirical evidence is decisive: every `A`-flagged row has `endowment_value IS NULL` (80/80 F1A; 285/285 F2), confirming `A` = "Not applicable" with exact `A`↔NULL coupling. Five spec sections were corrected in v1.4 v1.2: §3 source value-domain table, §4 RAW-IPF-015 description, §6 `endowment_value_provenance` field doc, §6 BT-IPF-ENDOWMENT-PROVENANCE glossary, and §2 Decision H rejected-alternatives narrative. Five governance artifacts also corrected in this v1.3 doc-generator pass: this domain-context entry (the "Endowment Imputation Caveat" subsection above carries the v1.3-EDA inverted wording — DO NOT propagate it; use the corrected semantics from this v1.4 amendment block); the raw, base, and consumable data dictionaries; the BT-IPF-ENDOWMENT-PROVENANCE glossary term; and the consumable data contract YAML. The mechanical "filter to `R` for longitudinal accuracy" guidance is unchanged in mechanism (because of the `A`↔NULL coupling, filtering to `R` is operationally close to filtering to `endowment_value IS NOT NULL`); the *rationale* phrasing is corrected throughout.

**Authoritative endowment-flag domain (v1.4 corrected v1.2 semantics):**

| Code | Meaning (v1.4 v1.2 corrected) | FY2023 prevalence (F1A) | FY2023 prevalence (F2) |
|---|---|---:|---:|
| `R` | Reported by institution (institution-reported value, populated, suitable for analysis without further qualification) | 737 (90.0%) | 1,293 (81.9%) |
| `A` | **Not applicable** (institution has no endowment fund — exact `A`↔NULL coupling on `endowment_value`; e.g., community colleges, tribal colleges, theological seminaries) | 80 (9.77%) | 285 (18.05%) |
| `N` | **Imputed using Nearest Neighbor procedure** | 1 (0.12%) | 0 |
| `P` | Imputed using prior year's data | 1 (0.12%) | 1 (0.06%) |
| `Z` | Imputed using a zero value | 0 | 0 |
| (NULL) | F3 structural — F3 has no `F3H` family on the for-profit schedule | — | — |

The observed FY2023 domain `{R, A, P, Z, N}` is a strict subset of the IPEDS dictionary's 13-code shared `Xvarname` lookup `{A, B, C, D, G, H, J, K, L, N, P, R, Z}`. The remaining 8 codes (`B, C, D, G, H, J, K, L`) are unobserved in FY2023 endowment data but are dictionary-legitimate. Future-cycle appearance is a Significant escalation — RAW-IPF-015 does not silently auto-extend.

**Longitudinal-filter guidance (carried verbatim at the consumable data contract layer in `governance/data-contracts/consumable-ipeds-finance-profile.yaml::consumer_guidance.endowment_provenance`):** consumers running longitudinal endowment analyses should filter to `endowment_value_provenance = 'R'` to limit to institution-reported populated values; this excludes both the no-endowment `A` population and the small imputed-value populations (`N` / `P` / `Z`).

**Cross-references:**
- EDA: `governance/eda/ipeds-finance-v1.4-flag-eda.md` (narrow-scope; verbatim FY2023 dictionary excerpt at §3; per-form FY2023 empirical prevalence at §4)
- Chaos report: `governance/chaos-reports/ipeds-finance-v1.4-chaos.md` (system-office filter validation; final form 4-clause numeric proxy)
- Data contract: `governance/data-contracts/consumable-ipeds-finance-profile.yaml` v1.1.0 (consumer_guidance block carries verbatim longitudinal-filter-to-`R` guidance and the 8-pattern AND 4-clause filter SQL)
- Business glossary: `governance/business-glossary.json` BT-IPF-ENDOWMENT-PROVENANCE (now 7th BT-IPF-* term)
- Data dictionaries: raw / base / consumable dictionaries each carry the new fields with corrected v1.2 semantics
- Models: 9 model files patched (3 zones × {conceptual, logical, physical}) — see file change log

| Date | v1.4 amendment landed | @doc-generator |
|---|---|---|
| 2026-05-01 | v1.4 amendment finalized — `endowment_value_flag` (raw+base) → `endowment_value_provenance` (consumable rename + CDE); system-office row filter at consumable (8-pattern AND 4-clause-numeric-proxy intersection); restored `source_load_date` at consumable (NOT CDE); corrected `A`/`N` semantics throughout; +1 BT-IPF-* term (now 7 total). | @doc-generator |

### v1.4 Amendment — domain-context-agent confirmation (2026-05-02)

CONFIRMED. The doc-generator's v1.4 amendment block correctly covers all four touchpoints (raw+base `endowment_value_flag` column with RAW-IPF-015 / BSE-IPF-018/019/020; consumable system-office 8-pattern AND 4-clause-numeric-proxy filter with CON-IFP-001a/b/014; restored `source_load_date` at consumable as NOT-CDE per CON-IFP-015/016; A/N semantic correction). Dictionary semantics match the EDA §3 verbatim excerpt: `A` = "Not applicable" with exact A↔NULL coupling (FY2023 80/80 F1A, 285/285 F2); `N` = "Imputed using Nearest Neighbor". The v1.3 4-clause numeric proxy (FTE-NULL/<50 disjuncts) is documented as canonical (line 2539) and matches spec §6 SQL exactly. EDA, chaos report, and per-form BSE-IPF-019 bands (F1A 5–15%, F2 12–25%) are correctly cited. No discrepancy. — @domain-context

---
---

# Domain Context: BLS OEWS (Occupational Employment and Wage Statistics — National Wage Distribution)
**Date:** 2026-05-06
**Agent:** @domain-context
**Based On:** governance/eda/raw-bls-oews-eda.md (2026-05-06)
**Spec:** docs/specs/ingest-bls-oews-wage-percentiles.md
**Data Sources:** bls_oews (Bureau of Labor Statistics, Occupational Employment and Wage Statistics — National, all-industries combined, May 2024 reference period)
**Confidence:** High
**Cross-Reference:** This is the SIXTH FutureProof data source. SOC keying is identical to the BLS OOH section above and the O*NET section above — `soc_code` is a direct join across all three (no crosswalk). OEWS is the wage-distribution complement to BLS OOH's projections-only median; together they cover demand (OOH) and price-of-labor (OEWS) per occupation, while O*NET covers task content. OEWS does NOT supersede OOH — see §"Why OEWS is different from BLS OOH" below.

---

## Domain Identification (BLS OEWS)
**Domain:** U.S. Labor Market — Occupation-Level Wage Distribution
**Sub-domain:** BLS Occupational Employment and Wage Statistics, National all-industries snapshot
**Description:** OEWS is the Bureau of Labor Statistics' semi-annual mail survey of approximately 200,000 establishments per panel (six panels rolled into each annual publication, ~1.2M establishment-years on a three-year cycle), producing employment-weighted national wage distributions for ~830 detailed SOC occupations. Each row represents a single detailed occupation with total employment plus six annual wage statistics — p10, p25, median, p75, p90, and mean — and the corresponding hourly figures. The reference period for the current load is May 2024, published by BLS in March 2025. Unlike the BLS OOH (Employment Projections) data, which only publishes the median, OEWS publishes the full quartile/decile shape of the wage distribution. In the FutureProof pipeline, OEWS answers "what is the realistic earnings range for this career?" — replacing program-level Scorecard earnings (which describe what graduates of a major earn, mixed across all jobs) with career-specific p25–p75 ranges (which describe what people doing this specific occupation earn, mixed across all education paths).

---

## Why OEWS is Different from BLS OOH (Critical Disambiguation)

OEWS and OOH are **both BLS occupation tables keyed by SOC**, and they share the same SOC 2018 taxonomy and many of the same occupation titles. They are **not interchangeable**, and small numeric differences between them are expected and must not be reconciled.

| Dimension | BLS OOH (Employment Projections) | BLS OEWS (this section) |
|-----------|----------------------------------|-------------------------|
| Primary purpose | 10-year employment projections (growth rate, openings, education requirements) | Wage distribution (p10/p25/median/p75/p90/mean, hourly + annual) |
| Wage data | Median only | Full distribution (5 percentiles + mean) |
| Refresh cadence | Biennial (full restate, 10-year horizon) | Annual snapshot (May survey, ~10 month lag to publish) |
| Reference period (current) | 2023–2033 projection cycle | May 2024 |
| Survey source | Modeled from CES, CPS, OEWS, and other inputs | Direct mail survey of ~200,000 establishments per panel |
| Top-coding | Median capped at $239,200 | All five annual percentiles individually capped at $239,200; mean published uncapped |
| Suppression sentinel | "N/A" → null (~2–4% of rows, mostly elected officials) | `*` → null (0.6% in May 2024, all five performance-arts SOCs in 27-2xxx) |
| Coverage in May 2024 / current | 832 detailed SOCs | 831 detailed SOCs (45-3031 Fishing and Hunting Workers is in OOH but suppressed by OEWS in May 2024) |
| Use in FutureProof | GRW stat, Ceiling/Market boss scoring, education-requirements display | ERN range, FinancesCard career-specific salary bands, ERN-ceiling potential signal (p75 − p25) |

**Methodology caveat — do NOT reconcile small OOH–OEWS median differences.** The two surveys have different sample frames, different reference periods, and (for OOH) a modeled rather than directly-surveyed median. The May 2024 OEWS Registered Nurses median is $93,600; the corresponding OOH median (2023 reference) is lower. This is **not a data quality failure** — it reflects (a) a one-year wage advance from the OOH reference period to the OEWS reference period, and (b) different survey methodologies. Both are correct for their stated reference period. Downstream consumers should:
- Use OOH for **projections** (growth rate, openings, education requirements, job-outlook narrative)
- Use OEWS for **distribution shape** (p25–p75 range on CareerCard, FinancesCard career-specific salary, ERN-ceiling signal)
- Display OEWS median as the canonical "what does this career pay" number wherever a single salary figure is shown to users (it's the more recent and more directly-surveyed number)
- Never write a DQ rule that compares OOH median to OEWS median — methodology drift is intrinsic, not a quality issue

---

## Domain Vocabulary (BLS OEWS)

### Core Terms
| Term | Definition | Source | Notes for @data-steward |
|------|-----------|--------|------------------------|
| OEWS | Occupational Employment and Wage Statistics — BLS's semi-annual mail-survey-based wage program. Survey covers ~200,000 establishments per panel, six panels per three-year cycle (~1.2M establishment-years). Produces employment-weighted national, state, metropolitan, and industry-level wage estimates. The FutureProof load uses the National all-industries-combined cut. | Bureau of Labor Statistics, Office of Employment and Unemployment Statistics | Auto-approve. Reference: https://www.bls.gov/oes/ |
| Annual Percentile (p10/p25/p50/p75/p90) | The wage at which the stated fraction of workers in the occupation earn less. p10 = 10% earn less, p90 = 10% earn more. Annual figures are computed by BLS from hourly figures × 2,080 hours, except for occupations BLS designates as salary-only (where annual is surveyed directly and hourly is suppressed). | OEWS methodology | Auto-approve. Standard BLS metric. |
| Annual Mean | Employment-weighted arithmetic mean of annual wages. **Published uncapped** even when percentiles are top-coded — see "mean above p90" advisory in Data Quality. | OEWS methodology | Auto-approve. |
| Top-Code Sentinel `#` | Source-file marker indicating the underlying value is at or above the BLS confidentiality ceiling of $239,200/year ($115/hour). Ingestor converts `#` → 239200.0 and sets `wage_capped = True` if ANY annual percentile equals 239200. Cap floor was raised from $208,000 → $239,200 in 2023. | OEWS source-file convention | Propose — sentinel handling is project-specific even though the underlying BLS rule is standard. |
| Suppression Sentinel `*` | Source-file marker indicating BLS suppressed the value due to confidentiality (small sample, single-employer dominance, or methodology — e.g., gig-based compensation in performing arts where annualized wage is not meaningful). Ingestor converts `*` → null. In May 2024, suppression affects 5 SOCs in 27-2xxx (Actors, Dancers, Musicians/Singers, DJs Except Radio, Entertainers/Performers All Other). | OEWS source-file convention | Propose. |
| `wage_capped` | Boolean flag: True iff at least one of the five annual percentiles (p10/p25/median/p75/p90) equals exactly $239,200. Indicates that the upper-tail of this occupation's wage distribution is censored. The flag is **not** set on the basis of the mean (which is published uncapped). 45 SOCs (5.42%) are flagged in May 2024. | Project-specific derivation | Propose — boolean is ours, but the underlying rule is BLS top-coding policy. |
| `wage_hourly_*` | Hourly equivalents of the annual percentiles. Suppressed by BLS for many salaried-only occupations (CEOs, lawyers, physicians) because hourly is not a meaningful unit for those roles. 7.10% null in May 2024 (54 SOCs are annual-published-but-hourly-suppressed). Reference-only column in the FutureProof pipeline; not used downstream. | OEWS methodology | Propose — document the asymmetry; no downstream use. |
| OCC_GROUP | Source-file column distinguishing detail level: `detailed` (one specific SOC, what we ingest), `broad`, `minor`, `major` (rollups). Ingestor filters to `detailed` only. | OEWS source-file convention | Auto-approve. Same filtering pattern as BLS OOH. |
| TOT_EMP | Total national employment in the occupation per OEWS estimation. Suppressed in some publication years; non-null in 100% of May 2024 rows. Used as a sanity floor and as an employment-weighting input for cross-source aggregations. | OEWS methodology | Auto-approve. |
| Reference Period | The single calendar month for which wage estimates are valid. The current load is "May 2024." OEWS is **not** a fiscal-year metric — it is a survey snapshot and the May reference period is fixed by BLS publication policy. | OEWS methodology | Auto-approve. |

### Taxonomy/Classification Systems
| System | Description | Authority | Coverage in Data |
|--------|-------------|-----------|-----------------|
| SOC 2018 | Same Standard Occupational Classification used by BLS OOH and O*NET. Direct join key with no crosswalk required. | OMB | 100% — every row is a detailed SOC 2018 code. |
| BLS Top-Coding Policy | The $239,200/year, $115/hour ceiling above which BLS does not publish individual statistics. Floor was raised from $208,000 → $239,200 in 2023; further increases on a multi-year cadence are possible. | Bureau of Labor Statistics | Affects 45 of 831 SOCs (5.42%) in May 2024. |
| BLS Suppression Policy | Confidentiality, sample-size, and methodological-suitability rules under which BLS publishes a sentinel (`*`) instead of a value. | Bureau of Labor Statistics | Affects 5 of 831 SOCs on annual percentiles (0.6%); 59 of 831 on `wage_hourly_median` (7.1%). |

### Enumerated Values with Business Meaning
| Field | Values | Meaning |
|-------|--------|---------|
| OCC_GROUP (raw) | `detailed` / `broad` / `minor` / `major` | Only `detailed` is retained. Rollups are filtered. |
| Top-code sentinel `#` (raw cell) | `#` | Value is censored at $239,200/year; converted to 239200.0 with wage_capped=True. |
| Suppression sentinel `*` (raw cell) | `*` | Value not published; converted to null. |
| `wage_capped` (typed) | True / False | True iff at least one annual percentile equals 239200.0. |
| source_method | `xlsx_download` | Metadata: ZIP-from-special-requests-page download, XLSX inside. |

---

## Entity Types (BLS OEWS)

### Primary Entities
| Entity Type | Identifier Field(s) | Example | Notes for @entity-resolver |
|-------------|---------------------|---------|---------------------------|
| Detailed Occupation | soc_code | 15-1252 (Software Developers) | **ID-based resolution. Trivial — no fuzzy matching, no name normalization, no probabilistic linkage required.** SOC 2018 is the same taxonomy used by BLS OOH and O*NET, and OEWS publishes a single row per detailed SOC. The entity-resolver step for OEWS reduces to a `soc_code` equality join against the existing Silver OOH and Gold O*NET keys. The only entity-resolution edge case is the 1-row gap between OOH (832 detailed) and OEWS (831 detailed): SOC `45-3031 Fishing and Hunting Workers` is in OOH but not the May 2024 OEWS publication — handle with LEFT JOIN, not INNER JOIN, and let the wage columns be null for that one row. |

### Entity Lifecycle Events
| Event Type | How It Appears in Data | Frequency |
|-----------|----------------------|-----------|
| SOC taxonomy revision | Same as OOH — SOC 2018 → SOC 2028 will change codes. BLS will publish a crosswalk at that time. | Rare (~10-year cycle). |
| Top-code floor change | Numeric value used by `wage_capped` rises (e.g., from $208,000 → $239,200 in 2023). Detectable by a sudden change in the `wage_capped` count or in the top-coded value across percentiles. | Multi-year cadence (last change 2023). DQ rule recommended: alert when `wage_capped` count moves outside [5, 80]. |
| Reference-period advance | Each annual publication carries a new May-of-year reference period. Wage levels generally advance year-over-year (e.g., RN median moved from ~$86K (OOH calibration) to $93,600 (May 2024 OEWS)). | Annual. Expected and not a DQ failure — spot-check windows must be wide enough (~$25K width on RN) to absorb. |
| Suppression-cluster shift | The set of SOCs with `*`-suppressed annual percentiles can change year-over-year as employment levels and survey response rates shift. May 2024 has 5 (all 27-2xxx). | Annual; expected to remain 0–10. DQ rule should accept a small range. |

---

## Temporal Patterns (BLS OEWS)

### Valid Time
| Pattern | Description | Notes for @temporal-modeler |
|---------|-------------|---------------------------|
| Annual snapshot | One reference period (e.g., "May 2024") per ingest. The pipeline carries `source_load_date` (when BLS published, ~March of the following year) and `ingested_at` (wall-clock time of our run). **No bitemporal modeling is required.** No effective-from / effective-to columns, no SCD-Type-2 history table, no as-of-date queries. The Silver/Gold contract is a complete replace on each annual refresh — exactly the same shape as BLS OOH, and simpler than IPEDS Finance because there is no fiscal-year dimension. | Treat as a non-temporal snapshot table for now. If a future requirement demands year-over-year wage-trend analysis, add a `reference_period` dimension (string, e.g., "May 2024") and stop replacing — but that decision is out-of-scope for v1 and should not drive the v1 model. |
| Hourly-vs-annual derivation | For most occupations, BLS computes annual = hourly × 2,080. For salaried-only occupations (CEOs, physicians, lawyers), BLS surveys annual directly and suppresses hourly. The two are **not** independently sampled and should not be treated as cross-validating. | The pipeline keeps hourly columns for reference only. Do not write DQ rules that assume annual ÷ 2,080 = hourly; the relationship breaks for the salaried-only set. |
| Wage-cap cohort drift | When BLS raises the top-code floor (e.g., 2023's $208K → $239,200 jump), the set of capped SOCs and the value of capped percentiles changes simultaneously. Year-over-year wage-distribution trend analyses must account for this discontinuity. | If trend analysis is added later, document the cap floor per reference period in the data dictionary. For v1, no action required. |

### Amendment/Correction Patterns
| Pattern | Description | Frequency |
|---------|-------------|-----------|
| Annual full replacement | Each May reference period is a complete republish. The Bronze/Silver/Gold contract is replace-on-refresh. | Annual. |
| Mid-year corrections | BLS occasionally republishes corrections to the prior May file. Detect by `source_url` checksum changes. | Rare. No formal amendment marker in the data itself — caught by a checksum-based freshness rule, not by a wage-value rule. |

---

## Data Quality Considerations (BLS OEWS)

### Known Edge Cases
| Edge Case | Description | Impact | Notes for @dq-rule-writer |
|-----------|-------------|--------|--------------------------|
| Performance-arts suppression cluster | The 5 SOCs in 27-2xxx (Actors, Dancers, Musicians/Singers, DJs Except Radio, Entertainers/Performers All Other) have all five annual percentiles + mean suppressed. Cause: gig/per-engagement compensation makes annualized wage statistics methodologically inappropriate. | 5 of 831 (0.602%). Stable cluster. | Per-percentile non-null floor of ≥99% (current 99.398%) absorbs one extra row of suppression next refresh. Do **not** require the cluster to be exactly these 5 SOCs — composition can shift. CareerCard fallback logic (per spec §CareerCard Display Logic) renders these as "no career-specific range, fall back to Scorecard." |
| Top-coding (`wage_capped = True`) | Any annual percentile equal to $239,200 indicates the upper tail is censored. 45 SOCs (5.42%) flagged in May 2024 — physicians, surgeons, dentists, federal judges, top managers, pilots, lawyers. p90 is the most-frequently capped (45/45), then p75 (24/45), then median (17/45), then p25 (1/45 — Pediatric Surgeons). | 5.42% of rows. | P0 invariant: `wage_capped = True` IFF at least one annual percentile equals 239200.0 (no null sentinel involvement, exact equality). Spec already carries this rule. P1 range rule: 5 ≤ `wage_capped` count ≤ 80 to detect cap-floor changes. |
| `mean > p90` for top-coded SOCs | 23 SOCs report annual mean > annual p90. All 23 are top-coded. BLS computes the mean **before** applying the top-code, so for capped SOCs the mean exceeds the capped p90 by design (e.g., Cardiologists mean $432,490 vs p90 $239,200). | 23 of 831 (2.77%), all wage_capped=True. | **DO NOT WRITE A DQ RULE** comparing mean to p90. This is a known, expected BLS publishing artifact. Document in the data dictionary instead. Downstream consumers (FinancesCard, ERN ceiling potential, anything that uses mean) must be prepared for `mean > p90` and treat it as informational, not a quality flag. |
| Single-row p25 cap | 29-1243 Pediatric Surgeons has its entire visible distribution at $239,200 (p10 through p90). Spread is exactly $0. | 1 of 831. Expected; surgical sub-specialty. | Spread-derived metrics (p75 − p25 as ERN-ceiling signal) must guard against zero spread on capped SOCs. Either condition the signal on `wage_capped = False`, or define a fallback for the fully-capped tail. |
| Hourly-vs-annual asymmetry | 54 SOCs publish annual but suppress hourly. Salaried-only occupations. | 6.5% extra hourly nulls. | No DQ rule on hourly. The column is reference-only; downstream does not consume it. Document the asymmetry. |
| Reference-period drift on spot-check values | Spot-check expected values from older spec calibrations (e.g., RN median ~$86K) may be stale relative to the new reference period (May 2024 RN median = $93,600). | One row off vs. spec calibration; six others within $5K. | Spot-check DQ rules must use windows wide enough to absorb a single year of wage growth (~$10K–$25K depending on occupation level). The Bronze RN spot-check window of $75K–$100K is the right shape. |
| OOH–OEWS coverage gap (1 SOC) | `45-3031 Fishing and Hunting Workers` is in OOH but suppressed by the May 2024 OEWS publication. After LEFT JOIN, this single SOC has null wage percentiles. | 1 of 832 OOH SOCs (0.12%). | Coverage rule: ≥800 of 832 OOH SOCs have non-null `wage_p25` after Gold join (currently 826/832 = 99.28%). Do **not** require 100% — single-SOC suppression is a normal BLS behavior. |

### Domain-Specific Validity Rules
| Rule | Description | Source |
|------|-------------|--------|
| SOC code format `^\d{2}-\d{4}$` | Identical to OOH and O*NET. Verified: 0 violations in 831 rows. | SOC 2018 standard. |
| SOC code uniqueness | One row per detailed SOC. Verified: 0 duplicates. | OEWS grain definition. |
| Detailed-only filter | OCC_GROUP must equal "detailed". Major/minor/broad rollups must be filtered by the ingestor. Verified: 0 leakage. | OEWS source-file structure. |
| Monotonicity of percentiles | For all rows with full annual percentile data, p10 ≤ p25 ≤ median ≤ p75 ≤ p90. Verified: 826 of 826 pass (100%). | Statistical definition of percentiles. |
| `wage_capped` invariant | `wage_capped = True` iff at least one of {p10, p25, median, p75, p90} equals 239200.0 exactly. Verified: 45/45 capped rows have a percentile at $239,200; 786/786 uncapped rows have no percentile at $239,200. | Project derivation from BLS top-coding policy. |
| Annual percentile non-null rate ≥99% | All five annual percentiles share an identical 99.398% non-null rate. Tighter rule than the spec's 95% floor; recommended by EDA. | EDA recommendation, anchored on the stable 5-row 27-2xxx suppression cluster. |
| `total_employment` non-null = 100% | Currently 0 nulls. BLS may resume employment suppression in future years, so codify the floor as 100% **for May 2024** but allow @dq-engineer to relax to ≥95% if a future load shows TOT_EMP suppression. | EDA recommendation. |
| Wage range bound $20K–$239,200 | When non-null, every annual percentile should fall in [$20,000, $239,200]. Below $20K is implausible (sub-minimum-wage full-time); above $239,200 is impossible (BLS cap). | BLS cap + economic floor. |

---

## Regulatory & Compliance Context (BLS OEWS)

### Applicable Regulations
| Regulation | Relevance | Key Requirements | Notes for @bcbs239-auditor |
|-----------|-----------|-----------------|---------------------------|
| BLS Data Use Terms | Same as OOH. Public domain federal statistical data. Attribution to BLS expected. BLS aggressively blocks bot User-Agents (403 on default Python clients) — ingestor must use browser-like headers or fall back to manual download. | 1. Public domain; free to use. 2. Attribute to BLS (source URL captured in metadata). 3. Respect bot-blocking; do not retry past the cached-fallback path. | No access restrictions on the data itself. Lineage and provenance fully captured (source_url, source_method, ingested_at, source_load_date). |
| OMB Statistical Policy Directives | Background. SOC 2018 is OMB-maintained; OEWS publishes against the OMB-current SOC vintage. | Future SOC 2028 migration will follow OMB process and will affect both OEWS and OOH simultaneously. | Plan reactively, same as OOH. |
| BLS Confidentiality Rules (top-coding + suppression) | The `#` cap and `*` suppression sentinels are not optional editorial decisions — they are required by BLS confidentiality protections under 13 U.S.C. § 9 and BLS internal policy. The pipeline preserves both signals (cap as wage_capped flag, suppression as null) without attempting to recover the underlying values. | 1. Never publish, infer, or reconstruct values BLS suppressed. 2. Always carry the `wage_capped` flag forward so consumers know the upper tail is censored. | Document upstream-imposed top-coding and suppression in any consumer-facing data contract. The Gold zone contract for `consumable.occupation_profiles` should include a `wage_data_caveats` annotation. |

### PII Expectations
| PII Type | Expected? | Sensitivity | Notes for @pii-scanner |
|----------|-----------|-------------|----------------------|
| Personal names | No | N/A | OCCUPATION titles only. |
| Worker identifiers | No | N/A | All data is occupation-aggregate. No individual records. |
| Establishment identifiers | No | N/A | Although OEWS surveys ~200,000 establishments, the published National all-industries cut is **already aggregated**. No establishment-level data reaches the pipeline. |
| Health records | No | N/A | Not applicable. |
| Financial PII | No | N/A | Wages are OCCUPATION-LEVEL DISTRIBUTION STATISTICS, not individual compensation. No personal financial data. |
| Location data | No | N/A | National cut only. State/metro/MSA cuts exist in BLS OEWS but are not part of this load. |

**Summary for @pii-scanner:** This dataset contains **NO PII**. All values are occupation-level wage distribution statistics published by a federal statistical agency at the national, all-industries-combined level. The pipeline should report zero PII findings. Justification: "governance/domain-context.md BLS OEWS PII section confirms no personal data — all fields are occupation-aggregate distribution statistics from a federal agency." Same disposition as the BLS OOH section.

---

## External Data Opportunities (from BLS OEWS perspective)
| External Source | What It Adds | Join Key | Notes for @insight-manager |
|----------------|-------------|----------|---------------------------|
| BLS OOH (already ingested) | Projections, education requirements, openings — the "demand" side of the labor market. | soc_code (direct, no crosswalk) | CRITICAL. OEWS provides price (wage distribution); OOH provides quantity (employment, growth, openings). Together they characterize the full labor-market signal per occupation. |
| O*NET Work Profiles (already ingested) | Task content, skills, knowledge, abilities, AI exposure scoring. | soc_code (direct, via O*NET's bls_soc_code) | HIGH. OEWS p25–p75 spread, when paired with O*NET task complexity, becomes a robust ERN-ceiling signal. Wide spread + high cognitive complexity = high career ceiling. |
| College Scorecard (already ingested) | Program-level graduate earnings (cipcode-keyed). | CIP-to-SOC crosswalk → soc_code | CRITICAL. Resolves the central FutureProof question: does the program-level earnings number (Scorecard) match the career-level wage distribution (OEWS)? Divergence indicates career-switching, geographic effects, or program-specific outcomes that don't align with the modal occupation. |
| BEA Regional Price Parities (already ingested) | State/metro cost-of-living adjustment. | FIPS code (separate join from SOC) | MEDIUM. Pairing OEWS national wages with RPP creates "purchasing-power-adjusted" wage distributions for FutureProof's compare_purchasing_power tool. Note: OEWS state/metro wage data exists at BLS but is not in this load — RPP is the more practical adjustment vector for v1. |
| BLS OEWS state/metro cuts (NOT INGESTED) | State-level and MSA-level wage distributions per occupation. | soc_code + state FIPS / MSA code | MEDIUM-HIGH future opportunity. Would replace RPP-adjusted national wages with directly-surveyed regional wages. Significant ingest cost (~50× the current row count). Not in current scope. |
| Karpathy AI Exposure (already ingested) | Per-SOC AI automation risk score. | soc_code | LOW direct opportunity from OEWS perspective; the wage distribution and the AI score are independent signals. But the **product** of high AI exposure and narrow wage spread (suggesting commodity work) is a strong "career risk" composite — relevant to the Fight AI boss. |
| Anthropic Economic Index (already ingested) | Per-SOC LLM augmentation/automation observations. | soc_code | Same logic as Karpathy — independent signal that composes well with wage spread. |

---

## Concept Mapping Guidance (BLS OEWS)

### Source Codes to Business Concepts
| Source Code Pattern | Maps To | Confidence | Notes for @cde-tagger |
|--------------------|---------|------------|----------------------|
| OCC_CODE (XX-XXXX) | Occupation Identity | Exact | SOC is the authoritative federal occupation taxonomy. Same field used by OOH and O*NET. |
| A_PCT10 / A_PCT25 / A_MEDIAN / A_PCT75 / A_PCT90 | Annual Wage Percentile (parameterized by p) | Exact | Each percentile is a CDE in its own right; they are **not** redundant with each other or with `wage_annual_mean`. |
| A_MEAN | Annual Wage Mean (uncapped) | Exact (with caveat) | Published uncapped even when percentiles are capped. Document the asymmetry; do not silently suppress. |
| `#` sentinel → 239200.0 + wage_capped=True | Top-Code Indicator | Exact | The numeric value alone is meaningless without the flag. Both must propagate together. |
| `*` sentinel → null | Suppression Indicator | Exact | Null is the canonical missing-value representation; the suppression cause is documented in the data dictionary, not encoded in a separate field. |
| TOT_EMP | Occupation Total Employment | Exact | Same concept as OOH employment_current, but a different reference period and survey methodology. Do **not** join across OOH and OEWS on employment — use occupation identity (soc_code) only. |

### Known Mapping Ambiguities
| Source Code | Candidates | Recommended | Rationale |
|------------|-----------|-------------|-----------|
| Median wage (single-figure salary display) | OOH median vs. OEWS median | **OEWS median** for user-facing salary; OOH median is retained but not displayed when OEWS is available | OEWS median is more recent and directly surveyed. OOH median lags by 1–2 years. The CareerCard salary bullet should be OEWS-anchored. |
| "Salary range" | p25–p75 (OEWS) vs. Scorecard graduate-earnings range | **OEWS p25–p75** when career is selected (career-specific); Scorecard range when career is unspecified (program-specific) | This is the core display rule from the spec's §CareerCard Display Logic. OEWS describes the career; Scorecard describes the program. |
| `wage_capped = True` | Display "$X+" vs. "at least $X" | "**at least $X**" in narrative; "$X+" in compact UI | Same convention as OOH. The capped value is a floor, not a point estimate. |
| Mean above p90 | DQ failure vs. expected behavior | **Expected behavior — document, do not flag** | BLS computes mean before capping. Writing a rule against this would generate 23 false positives every refresh. |

---

## Canonical Concept Map (BLS OEWS)

This section defines the wage-distribution concepts that feed into Silver and Gold and onto user-facing surfaces. It composes with the BLS OOH and O*NET concept maps above; OEWS is the wage-shape layer of the per-SOC picture.

**Status:** PROPOSED (Unconfirmed)
**Source:** Agent-proposed based on EDA findings and the spec's stated downstream use (CareerCard p25–p75 range, FinancesCard career-specific salary, ERN ceiling potential).

### Target Business Concepts
| # | Business Concept | Plain English Name | Expected Source Codes | Category | Priority |
|---|-----------------|-------------------|----------------------|----------|-----------|
| 1 | Occupation Wage Distribution | The full shape (p10/p25/median/p75/p90) of annual pay for an occupation | wage_annual_p10..p90 | Compensation Distribution | CORE |
| 2 | Occupation Median Wage (OEWS) | Single-figure annual median (more recent than OOH median) | wage_annual_median | Compensation Metric | CORE |
| 3 | Career-Specific Salary Range | The p25–p75 band used in CareerCard salary bullet and FinancesCard career-specific scenario | wage_annual_p25, wage_annual_p75 | Compensation Range | CORE |
| 4 | Wage Cap Indicator | Boolean signaling that the upper tail is censored at $239,200 | wage_capped | Compensation Caveat | CORE |
| 5 | Occupation Total Employment (OEWS) | Survey-derived employment count (independent estimate from OOH employment_current) | total_employment | Volume Metric | EXTENDED |
| 6 | Wage Mean (uncapped) | Employment-weighted mean, useful for capped occupations where percentiles are floored | wage_annual_mean | Compensation Metric | EXTENDED |
| 7 | Wage Spread (p75 − p25) | Derived: width of the middle 50% of the distribution. Signals career-ceiling potential when paired with O*NET cognitive load. | Derived from p25 + p75 | Derived Metric | EXTENDED |
| 8 | Hourly Wage Reference | Hourly equivalents of the annual percentiles | wage_hourly_* | Reference | OPTIONAL (kept, not displayed) |

### Cross-Source Concept Linkages
| Concept | OEWS Source | OOH Source | O*NET Source | Scorecard Source |
|---------|-------------|------------|--------------|------------------|
| Career-specific salary | wage_annual_median, p25, p75 (PRIMARY for career-specific display) | median_annual_wage (FALLBACK if OEWS row missing for the SOC) | — | — |
| Earnings range on CareerCard | wage_annual_p25..p75 (PRIMARY when career selected) | — | — | earn_mdn_hi_1yr / earn_mdn_hi_2yr (FALLBACK when career not selected) |
| ERN ceiling potential | wage_annual_p75 − wage_annual_p25 (signal) | — | Cognitive complexity from work profiles (composes) | — |
| FinancesCard salary scenario | wage_annual_median (when career selected) | median_annual_wage (when career not selected) | — | program-level earnings (alternative scenario) |

### Concept-to-Code Mapping Rules

```json
{
  "domain": "us_labor_market_wage_distribution",
  "taxonomy": "SOC_2018",
  "reference_period": "May 2024",
  "tiers": {
    "exact": {
      "description": "OCC_CODE (XX-XXXX) directly identifies a detailed occupation; A_PCTxx and A_MEDIAN columns directly carry the named percentile",
      "confidence": 1.0,
      "examples": [
        "15-1252 -> Software Developers",
        "A_MEDIAN -> wage_annual_median",
        "# in any A_PCT cell -> 239200.0 with wage_capped=True"
      ]
    },
    "prefix": {
      "description": "2-digit SOC major group rollup (same as OOH); OEWS publishes major/broad/minor rows but ingestor filters to detailed",
      "confidence": 0.8,
      "example": "29 -> Healthcare Practitioners (filtered out at ingest)"
    },
    "pattern": {
      "description": "Not applicable — OEWS columns are directly typed",
      "confidence": null,
      "example": null
    },
    "heuristic": {
      "description": "Cross-source bridge to CIP via CIP-to-SOC crosswalk (program → occupation → wage distribution)",
      "confidence": 0.6,
      "example": "CIP 11.0701 (Computer Science) -> SOC 15-1252 -> OEWS p25=$103,050, median=$133,080, p75=$169,000"
    }
  }
}
```

### Collision Resolution Rules
| Collision Scenario | Resolution | Rationale |
|-------------------|------------|-----------|
| OOH median vs. OEWS median for the same SOC | OEWS median **wins** for user-facing displays; OOH median is retained as a separate field and used for historical projection alignment | OEWS is more recent (May 2024 vs. typically 2023 for current OOH cycle) and is directly surveyed rather than modeled. The two should not be averaged. |
| OEWS row missing for a SOC that exists in OOH (the `45-3031` case) | LEFT JOIN; null wage percentiles for the missing SOC; CareerCard renders Scorecard fallback | Single-SOC suppression is normal BLS behavior. Forcing INNER JOIN would orphan a valid OOH occupation. |
| Capped p25 (Pediatric Surgeons case) | Retain the value $239,200 and the wage_capped flag; spread = 0 is the truthful answer | The cap is the legitimate published value. Derived "ceiling potential" signals must guard against zero spread on capped SOCs. |
| Mean conflicts with capped p90 | Display both; document the artifact | Both numbers are correct under BLS methodology. Neither should be silently suppressed. |
| OEWS wage available but Scorecard earnings unavailable for the same program | Use OEWS career-specific range; suppress the program-level fallback | OEWS describes the career, which is what the user asked about. |

---

## OEWS-Specific: SOC Code Cross-Source Bridging

Because OEWS shares the SOC 2018 taxonomy with both OOH and O*NET, no crosswalk or fuzzy match is required. The cross-source picture in May 2024:

| Cross-Source Slice | Count | % | Action |
|--------------------|-------|---|--------|
| `silver.bls_ooh` SOCs (OOH detailed) | 832 | 100% (denominator) | — |
| OOH SOCs also in OEWS | 831 | 99.88% | LEFT JOIN; the one orphan is `45-3031`. |
| OOH SOCs in OEWS with non-null `wage_p25` | 826 | 99.28% | Codify as Gold coverage floor ≥ 98%. |
| `consumable.onet_work_profiles` SOCs | 798 | 100% (denominator) | — |
| O*NET SOCs also in OEWS | 772 | 96.7% | LEFT JOIN; 26 O*NET-only SOCs are newer detail rollups OEWS aggregates differently. |

**Net coverage on the SOCs that actually drive FutureProof's Gold tables:** 826 of 832 OOH-Silver SOCs (99.28%) gain non-null wage percentiles after the OEWS join, well above the spec's 90% floor.

---

## OEWS-Specific: Update Cadence and Refresh Strategy

| Aspect | Value |
|--------|-------|
| Survey frequency | Semi-annual (BLS panels in May and November) |
| Publication cadence | Annual (BLS aggregates two panels and publishes once per year) |
| Reference period for current load | May 2024 |
| Publication date for current load | March 2025 |
| Lag from reference period to publication | ~10 months |
| FutureProof refresh strategy | Annual full replace, triggered after BLS publishes the next May reference period (typically March of the following year) |
| Year-over-year wage drift | Expected. RN median moved ~$93,600 (May 2024) vs. ~$86K (older OOH calibration) — a normal 1-year wage advance plus methodology drift |
| Cap-floor change cadence | Multi-year. Most recent change: $208,000 → $239,200 in 2023. Pipeline DQ rule should detect cap moves via `wage_capped` count drift |

**Operational note for @doc-generator and @mcp-engineer:** the data contract for `consumable.occupation_profiles` should expose the OEWS reference period as a metadata field (or via a lineage table) so MCP responses can attribute the salary numbers correctly: "median annual wage of $133,080 for Software Developers (BLS OEWS, May 2024)."

---

## Unanswered Interview Questions (BLS OEWS — Automated Pipeline Run)

Same protocol as the BLS OOH section: the agent ran without an interactive interview because the spec carries directed user context. Each question is documented with the agent's assumption.

### Question 1: OEWS reference-period tracking
**Question:** "OEWS is annual but BLS may correct prior years. Should we (a) replace-on-refresh and lose history, (b) retain the prior `reference_period` as a snapshot, or (c) build full year-over-year wage trend tracking?"
**Status:** UNANSWERED
**Agent Assumption:** (a) replace-on-refresh for v1. Wage trend tracking is out of scope. The spec explicitly treats this as a snapshot.
**Mandatory DQ Rule:** Freshness rule — alert if `source_load_date` is older than 14 months (annual cadence + 2-month buffer).

### Question 2: OEWS vs. OOH median display priority
**Question:** "When both are available, should the user-facing 'salary' figure use OEWS median or OOH median?"
**Status:** UNANSWERED
**Agent Assumption:** OEWS median wins for career-specific user displays (CareerCard, FinancesCard career-specific scenario). OOH median is retained for projection alignment and as a fallback when OEWS data is suppressed for the SOC.
**Mandatory DQ Rule:** None — display preference is a Gold contract decision, not a data quality rule. Document in the consumable-occupation-profiles data contract.

### Question 3: Wage-cap floor change detection
**Question:** "BLS raised the cap from $208K to $239,200 in 2023. The next change could happen with no warning. Should we (a) hardcode $239,200 in DQ rules, (b) detect cap changes via `wage_capped` count drift, or (c) parameterize the cap value per refresh?"
**Status:** UNANSWERED
**Agent Assumption:** (b) — detect via count drift. The `wage_capped` count between 5 and 80 P1 rule will fire when BLS moves the floor (because the count will plummet on the refresh-after-the-change as fewer SOCs reach the new higher cap). For v1 we hardcode $239,200 in the `wage_capped` invariant; if the cap changes, @dq-engineer updates the constant.
**Mandatory DQ Rule:** P1 — `5 ≤ wage_capped count ≤ 80`. Already in the spec.

### Question 4: Suppression-cluster stability
**Question:** "May 2024 has exactly 5 suppressed SOCs, all in 27-2xxx. Should DQ rules require that specific cluster?"
**Status:** UNANSWERED
**Agent Assumption:** No. Require only the **count range** (≥99% non-null on annual percentiles, allowing 0–8 suppressed rows). Composition can shift year-over-year without being a quality issue.
**Mandatory DQ Rule:** P0 — `wage_annual_median` non-null rate ≥99% (tightened from spec's 95%).

### Question 5: Hourly wage column retention
**Question:** "`wage_hourly_*` columns have 7.10% nulls (vs. 0.6% for annual) due to BLS suppressing hourly for salaried-only roles. Keep them, drop them, or treat them as separate tables?"
**Status:** UNANSWERED
**Agent Assumption:** Keep them as reference columns in Bronze and Silver. Do not propagate to Gold (`consumable.occupation_profiles` should not gain hourly columns in v1). If a future feature needs hourly, promote them then.
**Mandatory DQ Rule:** None on hourly columns. Document the asymmetry in the data dictionary.

### Question 6: Use of `wage_annual_mean`
**Question:** "OEWS publishes a mean uncapped, even when percentiles are capped. For 23 capped SOCs the mean exceeds p90 by design. Should the pipeline expose mean to user-facing surfaces?"
**Status:** UNANSWERED
**Agent Assumption:** Retain mean in Bronze and Silver; do not expose on CareerCard or FinancesCard. The mean is informationally valuable for capped SOCs (where it's the only signal that percentiles are floored) but is not the right user-facing salary number for a general audience. If a future "true average pay" surface is added, surface it there with a caveat about top-coding.
**Mandatory DQ Rule:** None. Mean is documented as advisory-only in the data dictionary.

---

## Assumptions (User-Deferred) — BLS OEWS

| # | Assumption | Basis | Confidence | Risk if Wrong |
|---|-----------|-------|------------|---------------|
| 1 | Annual full replace; no historical reference-period retention | Spec § Zone 1 | HIGH | Low — matches BLS publication model. |
| 2 | OEWS median preferred over OOH median in user-facing displays | More recent + directly surveyed | HIGH | Low — both are retained; this only affects default display. |
| 3 | $239,200 cap hardcoded in `wage_capped` invariant for v1 | Stable since 2023 | MEDIUM | Medium — when BLS next raises the floor, the invariant will need a code update. The P1 count rule will alert. |
| 4 | Suppression cluster of 5 SOCs is a count range, not a fixed set | Composition can shift | HIGH | Low. |
| 5 | Hourly columns kept in Bronze/Silver; not promoted to Gold | Spec says hourly is reference-only | HIGH | Low — easy to promote later if needed. |
| 6 | Mean is advisory-only, not user-facing | Mean above p90 for capped SOCs is intuitive only with explanation | MEDIUM | Low — easy to surface later with caveat. |
| 7 | No state/metro OEWS in v1 | National-only is sufficient with RPP adjustment | HIGH | Low — adding state/metro is a future enhancement, not a v1 gap. |
| 8 | LEFT JOIN OEWS to OOH (allow nulls for `45-3031`-style gaps) | Single-SOC suppression is normal | HIGH | Low — alternative (INNER JOIN) would lose 1 of 832 valid OOH SOCs. |
| 9 | OEWS treated as non-temporal snapshot in Silver/Gold (no bitemporal model) | Annual replace pattern matches OOH precedent | HIGH | Low — if year-over-year trends are added later, retrofit is straightforward (add `reference_period` column, stop replacing). |
| 10 | Zero PII | All occupation-aggregate data from federal agency | HIGH | Very low. |

---

## AI-Ready Considerations (BLS OEWS)
| Consideration | Recommendation | Notes for @mcp-engineer |
|--------------|---------------|------------------------|
| Primary user questions OEWS unlocks | "What's the salary range for [occupation]?" "Is [occupation] a flat-pay or wide-spread career?" "What does the top 10% earn?" "Is the wage of [occupation] capped?" | Surface p25, median, p75, p90 + wage_capped on the per-occupation MCP response. Title/SOC fuzzy-match same as OOH. |
| Career-specific vs. program-specific salary | OEWS gives career-specific (per-SOC) salary; Scorecard gives program-specific (per-CIP) graduate earnings. They answer different questions. | When the user has selected a career (SOC), use OEWS. When the user is exploring a program (CIP) without a chosen career, use Scorecard. The MCP server should not collapse these into a single ambiguous "salary" — keep them separable. |
| Top-coding disclosure | Always disclose when wage_capped is true. "Surgeons earn at least $239,200 annually (BLS does not publish wages above this confidentiality cap)." | wage_capped flag must propagate from Bronze through to MCP. Do not silently present $239,200 as the median. |
| Mean above p90 disclosure | When the user asks for "average" pay on a capped occupation, the mean is informative but needs caveat. "Cardiologists' average annual pay is $432,490, while the published 90th-percentile is capped at $239,200 — most cardiologists earn well above the cap, but BLS does not publish individual values above it." | Optional MCP expansion. For v1, do not surface mean unless the user explicitly asks for "average." |
| Suppression disclosure | When a user asks about Actors/Dancers/Musicians/DJs/Entertainers-All-Other, the response should explain the suppression rather than just returning null. | "BLS does not publish annual wage statistics for [occupation] because compensation in this field is dominated by gig and per-engagement work, where annualized wages are not meaningful." |
| Salary-range narrative | "Half of Software Developers earn between $103,050 and $169,000 (the middle 50%). The bottom 10% earn under $86,460; the top 10% earn over $211,450." | The p25–p75 range is the "typical" range; p10 and p90 frame the tails. |
| OOH–OEWS reconciliation | If a user notices OOH median ≠ OEWS median for the same occupation, the response should explain methodology drift, not flag it as an error. | "These are two different BLS surveys. The Employment Projections median ($X) is based on [year] data and a modeled estimate; the OEWS median ($Y) is from the May 2024 establishment survey. Both are correct for their reference periods." |
| Reference-period attribution | Every wage figure surfaced via MCP should carry the OEWS reference period and the publication source. | Include "reference_period: May 2024" or "BLS OEWS (May 2024)" in any structured response. |

---

## Confidence Notes (BLS OEWS)

**High confidence:**
- Domain identification — unambiguous from spec, EDA, and source-file structure. OEWS is a well-known BLS publication.
- No PII — all occupation-level aggregates from federal agency at the National all-industries cut.
- SOC 2018 taxonomy — direct join to OOH and O*NET, no crosswalk.
- Top-coding rules ($239,200 ceiling, capping pattern across percentiles, `wage_capped` invariant, mean published uncapped).
- Suppression rules (`*` sentinel, 27-2xxx performance-arts cluster).
- Monotonicity (100% in EDA — all 826 rows with full data satisfy p10 ≤ p25 ≤ median ≤ p75 ≤ p90).
- Annual-snapshot temporal model (no bitemporal needed).
- Trivial entity resolution (SOC equality, no fuzzy matching).
- Cross-source coverage (831/832 OOH-Silver SOCs covered by OEWS; 99.28% of OOH SOCs have non-null wage_p25 after join).

**Medium confidence:**
- $239,200 cap floor stability — held since 2023 but BLS may raise it again; the count-drift DQ rule is the primary detection.
- Future composition of the suppression cluster — currently 5 SOCs all in 27-2xxx, expected to remain small (0–8) but not pinned to those specific codes.
- OEWS-vs-OOH median preference for user-facing displays — proposed by agent based on freshness; user has not confirmed.
- ERN ceiling potential signal (p75 − p25) — sound for uncapped SOCs; degrades on capped SOCs and requires guard logic.
- Wage spot-check window widths — RN $75K–$100K accommodated this refresh, but may need widening for occupations with very fast wage growth.

**Low confidence / Needs human validation:**
- Whether to expose `wage_annual_mean` on user-facing surfaces (especially for capped SOCs where it's the only un-floored signal). Currently agent-recommended advisory-only.
- Whether to retain prior reference periods for year-over-year trend analysis. Currently agent-recommended replace-on-refresh.
- Whether state/metro OEWS cuts will be ingested in a future iteration. Out of scope for v1.
- Whether the `consumable.program_career_paths` join should propagate all four wage percentiles (p10, p25, p75, p90) or just the user-facing pair (p25, p75). Spec says all four; downstream consumer needs may differ.
