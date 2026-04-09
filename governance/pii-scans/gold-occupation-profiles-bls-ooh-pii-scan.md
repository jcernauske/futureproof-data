## PII Scan Report: gold-occupation-profiles-bls-ooh
**Date:** 2026-04-07
**Agent:** @pii-scanner
**Domain:** BLS Employment Projections (Occupational Outlook Handbook)
**Zone:** Gold (Consumable)
**Spec:** docs/specs/gold-occupation-profiles-bls-ooh.md
**Records Scanned:** 832 (schema-level scan; one row per occupation)
**PII Instances Found:** 0

### Findings
| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|-------------------|
| -- | -- | -- | -- | -- | -- | No PII detected in any field |

### Summary by Sensitivity
| Level | Count | Fields Affected |
|-------|-------|----------------|
| 1 - Public | 0 | -- |
| 2 - Internal | 0 | -- |
| 3 - Confidential | 0 | -- |
| 4 - Restricted | 0 | -- |

### Field-by-Field Analysis

All 31 columns in `consumable.occupation_profiles` were evaluated against PII detection categories.

| Field | Data Type | PII Risk | Rationale |
|-------|-----------|----------|-----------|
| record_id | VARCHAR | None | Deterministic hash (SHA-256 truncated, prefix `op`). Not derived from personal data. Grain key is soc_code (a public taxonomy code). |
| soc_code | VARCHAR | None | Standard Occupational Classification code (XX-XXXX). Public federal taxonomy maintained by OMB/BLS. Identifies occupations, not individuals. |
| occupation_title | VARCHAR | None | Official BLS occupation names (e.g., "Software Developers", "Registered Nurses"). Standardized occupation labels, not personal names. |
| soc_major_group | VARCHAR | None | 2-digit SOC major group code. Public taxonomy. |
| soc_major_group_name | VARCHAR | None | Human-readable SOC group label (e.g., "Management"). Public taxonomy. |
| broad_occupation_flag | BOOLEAN | None | Derived classification flag. No personal data. |
| catchall_flag | BOOLEAN | None | Derived classification flag. No personal data. |
| employment_current | BIGINT | None | Aggregate employment count across all workers in an occupation nationally. Not individual-level. |
| employment_projected | BIGINT | None | Aggregate projected employment count. Not individual-level. |
| employment_change_pct | DOUBLE | None | Percentage change in aggregate employment. Not individual-level. |
| openings_annual_avg | BIGINT | None | Aggregate annual job openings. Not individual-level. |
| growth_category | VARCHAR | None | Derived categorical tier from aggregate growth percentage. |
| grw_score | DOUBLE | None | Derived score (1-10 scale) from aggregate employment_change_pct via piecewise linear function. No personal data input. |
| grw_score_rounded | INTEGER | None | ROUND(grw_score). Derived from aggregate data. No personal data. |
| median_annual_wage | DOUBLE | None | Occupation-level median wage. Statistical aggregate across all workers in the occupation, not any individual's compensation. |
| wage_available | BOOLEAN | None | Derived convenience flag. No personal data. |
| wage_percentile_overall | DOUBLE | None | Derived percentile rank from occupation-level median wages. Not individual compensation ranking. |
| wage_percentile_education_tier | DOUBLE | None | Derived percentile rank within education tier from occupation-level medians. Not individual compensation ranking. |
| wage_tier | VARCHAR | None | Categorical bucketing of wage_percentile_overall. Derived from aggregate data. |
| education_code | INTEGER | None | BLS occupation-level education requirement code (1-8). Not any individual's educational attainment. |
| education_level_name | VARCHAR | None | Normalized label for occupation education requirement. Not individual-level. |
| work_experience_code | INTEGER | None | BLS occupation-level experience requirement code (1-3). Not individual work history. |
| training_code | INTEGER | None | BLS occupation-level training requirement code (1-6). Not individual training records. |
| market_score | DOUBLE | None | Derived composite score (1-10) from aggregate growth and openings data. No personal data input. |
| market_score_rounded | INTEGER | None | ROUND(market_score). Derived from aggregate data. No personal data. |
| confidence_tier | VARCHAR | None | Data quality classification ("high", "medium", "low"). Pipeline metadata, not personal data. |
| data_completeness | DOUBLE | None | Non-null core field ratio (0.0-1.0). Pipeline metadata, not personal data. |
| backs_stats | VARCHAR | None | Static FutureProof mapping string ("ERN,GRW"). Application metadata. |
| backs_bosses | VARCHAR | None | Static FutureProof mapping string ("Market,Ceiling"). Application metadata. |
| source_load_date | DATE | None | Pipeline metadata date. Not a personal date of birth or other personal date. |
| promoted_at | TIMESTAMP | None | Gold zone promotion timestamp. Pipeline metadata, not personal data. |

### Re-identification Risk Assessment

| Risk Vector | Assessment | Rationale |
|-------------|-----------|-----------|
| Direct identifiers | None | No names, SSNs, emails, addresses, or other direct identifiers present. |
| Quasi-identifiers | None | SOC codes identify occupations (832 nationwide categories), not individuals. No geographic, demographic, or temporal dimensions that could enable triangulation. |
| Sensitive categories | None | Occupation titles describe career categories, not individual employment status. No health, financial, or protected-class data about individuals. |
| Re-identification via linkage | None | Aggregated national-level statistics at the occupation grain. Even if linked to other datasets, no individual-level records exist to re-identify. The smallest unit is an occupation category containing thousands of workers nationally. |

### False Positive Candidates
| Field | Detected As | Why It's Likely False | Recommendation |
|-------|-------------|----------------------|----------------|
| occupation_title | Personal Names (NER) | Occupation titles may contain words that overlap with name patterns (e.g., "Baker" in "Bakers", "Cook" in "Cooks"). These are standardized BLS occupation labels, not personal names. | No action required. Zero risk. |
| median_annual_wage | Financial PII | Wage values are occupation-level statistical medians published by a federal agency, not any individual's compensation. | No action required. Zero risk. |
| grw_score / market_score | Sensitive metrics | Derived scores from aggregate public data. Not performance evaluations of individuals. | No action required. Zero risk. |
| wage_percentile_overall / wage_percentile_education_tier | Individual financial ranking | These rank occupations against each other, not individuals. Input data is public BLS medians. | No action required. Zero risk. |

### Regulatory Implications

**No PII-related regulations apply to this dataset.**

- **FERPA:** Not applicable. No student-level data.
- **HIPAA:** Not applicable. No health records or patient data. Healthcare occupation titles (e.g., "Registered Nurses") describe occupational categories, not patients or providers.
- **CCPA/CPRA:** Not applicable. No California consumer personal information.
- **GDPR:** Not applicable. No EU personal data. All data is U.S. aggregate occupation statistics.
- **PCI DSS:** Not applicable. No payment card data.
- **EEOC/Employment law:** Not applicable. No individual employment records.

The BLS Employment Projections data is produced by a federal statistical agency and published as public domain data. The Gold transformations (GRW score, market score, wage percentiles, wage tier, confidence tier) are derived entirely from these public aggregates, introducing no new personal data. No privacy protections are required beyond standard data governance practices.

### Lineage from Silver Scan

The upstream Silver table `base.bls_ooh` was scanned and confirmed PII-free (see `governance/pii-scans/silver-base-bls-ooh-pii-scan.md`). The Gold transformation introduces 12 derived columns, all computed from the same aggregate public data. No external data sources are joined. No individual-level data is introduced at any point in the pipeline.

### Recommendations

1. **No PII remediation needed.** All 31 fields contain either public taxonomy codes, aggregate statistical measures, derived scores/percentiles from public data, classification flags, or pipeline metadata.
2. **No column masking required.** @policy-engineer can skip PII-based column masking policies for this table.
3. **No RLS policies needed for PII reasons.** Access controls should be based on business need, not PII sensitivity.
4. **Standard access controls sufficient.** This table can be classified as Sensitivity Level 1 (Public) for all fields -- the source data is publicly available from BLS and all derivations are from that public data.
5. **Domain context confirms finding.** The `governance/domain-context.md` BLS OOH PII section explicitly states: "This dataset contains NO PII. All values are occupation-level aggregates published by a federal statistical agency."
6. **Silver scan confirms upstream is clean.** The Silver-zone PII scan found zero PII in `base.bls_ooh` (25 fields), and this Gold product adds only derived fields from those same aggregates.

### Scan Methodology

- **Schema analysis:** All 31 columns evaluated against 9 PII categories (Personal Names, Addresses, Government IDs, Financial Accounts, Contact Information, Health Information, Dates of Birth, Biometric Data, Location Data).
- **Domain calibration:** Scanning expectations set from `governance/domain-context.md` BLS OOH PII section, which confirms no personal data is expected.
- **Upstream lineage:** Silver scan report reviewed to confirm no PII was detected in the source table (`base.bls_ooh`, 25 columns). Gold adds 12 derived columns and drops 6 Silver columns; net gain of 6 columns, all derived from public aggregates.
- **Re-identification risk assessment:** Four-vector analysis (direct identifiers, quasi-identifiers, sensitive categories, linkage risk) performed. All vectors assessed as zero risk.
- **Data characteristics:** 832 rows at one-row-per-occupation grain. All data is aggregate national-level statistics. No individual-level records exist in this dataset.
- **Source provenance:** Data originates from BLS Employment Projections (public federal statistical data). Silver transformation adds normalization and flags. Gold transformation adds scores, percentiles, tiers, and metadata -- all derived from the same public data.
- **False positive review:** Four field groups (occupation_title, median_annual_wage, score fields, percentile fields) evaluated for false positive risk and cleared.
