## CDE/PII Tagging Report: silver-base-college-scorecard
**Date:** 2026-04-06
**Agent:** @cde-tagger
**Spec:** docs/specs/silver-base-college-scorecard.md
**Contract:** governance/data-contracts/base-college-scorecard.yaml
**Physical Model:** governance/models/silver-base-college-scorecard-physical.md

### Domain Context Referenced
- **Domain:** Higher Education Outcomes (College Scorecard Field of Study)
- **Regulatory context:** FERPA (privacy suppression already applied at source); Gainful Employment rules (debt-to-earnings ratios use earnings and debt fields); HEA (public data, no access restrictions)
- **PII scan result:** Zero PII detected (governance/pii-scans/silver-base-college-scorecard-pii-scan.md). All fields are institutional identifiers, program codes, or cohort-level aggregates.
- **CDE drivers:** Earnings and debt fields are the primary business metrics powering FutureProof career guidance. unitid is the institutional identity anchor required for all downstream joins.

### Columns Flagged as CDE
| Column | Table | Rationale |
|--------|-------|-----------|
| unitid | base.college_scorecard | Natural key component identifying the institution. Required for all downstream joins (CIP-to-SOC crosswalk, Gold zone program comparisons, institution-level aggregations). Incorrect or missing values would orphan rows from institutional context and break grain integrity. |
| earnings_1yr_median | base.college_scorecard | Primary business metric -- median earnings 1yr post-completion. Core to FutureProof career guidance. Feeds program rankings, debt-to-earnings ratios (Gainful Employment), and Gold zone products. |
| earnings_2yr_median | base.college_scorecard | Primary business metric -- median earnings 2yr post-completion. Multi-horizon view of graduate outcomes central to career guidance. Feeds Gold zone ranking and trend analysis. |
| debt_median | base.college_scorecard | Primary business metric -- median federal loan debt at completion. Required for debt-to-earnings ratio analysis and cost-benefit assessment. Central to student decision-making use case. |

### Columns Flagged as PII
| Column | Table | Rationale |
|--------|-------|-----------|
| (none) | -- | Zero PII. All fields are institutional/aggregate. PII scan confirmed zero findings. Domain context states: "This dataset contains NO PII." |

### Columns Evaluated -- Not Flagged
| Column | Table | Reason Not Critical/Sensitive |
|--------|-------|-------------------------------|
| record_id | base.college_scorecard | Derived surrogate key (hash of grain fields). Technical artifact, not a business-critical data element. |
| institution_name | base.college_scorecard | Display label only; unitid is the authoritative identifier. Not consumed by downstream calculations or regulatory reports. |
| institution_control | base.college_scorecard | Segmentation dimension useful for analysis but not critical to core business metrics or regulatory filings. |
| cipcode | base.college_scorecard | Natural key component and crosswalk join key. Important for data integrity but evaluated as non-CDE at this Silver base layer because its criticality is realized at the Gold zone crosswalk join. Physical model concurs (is_cde: false). |
| program_name | base.college_scorecard | Display label for cipcode. Not consumed by downstream calculations. |
| cip_family | base.college_scorecard | Derived grouping code. Useful for aggregation but not critical to individual business decisions or regulatory metrics. |
| cip_family_name | base.college_scorecard | Display label for cip_family. |
| credential_level | base.college_scorecard | Natural key component but constant (=3) in MVP. Not directly consumed by downstream business metrics. |
| credential_description | base.college_scorecard | Display label for credential_level. |
| completions_count_1 | base.college_scorecard | Program size indicator. Drives small_cohort_flag but is not itself a primary decision metric. |
| completions_count_2 | base.college_scorecard | Supplementary completions count. Highly correlated with count_1. Not a primary decision metric. |
| small_cohort_flag | base.college_scorecard | Derived quality indicator. Useful for filtering but not a business metric itself. |
| source_load_date | base.college_scorecard | Pipeline metadata. No business criticality. |
| ingested_at | base.college_scorecard | Pipeline metadata. No business criticality. |

### Consistency Check
- **Physical model alignment:** 4 CDEs (unitid, earnings_1yr_median, earnings_2yr_median, debt_median) -- matches physical model exactly.
- **PII scan alignment:** 0 PII fields -- matches PII scan exactly.
- **Bronze contract alignment:** Bronze contract flags cipcode, credlev, and unitid as CDE (grain fields at raw layer). Silver contract flags unitid as CDE but not cipcode/credlev because CDE flags are independent per zone. At the Silver base layer, cipcode and credential_level are structural grain components but their downstream criticality is realized at the Gold zone crosswalk, not at this layer.
