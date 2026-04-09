## PII Scan Report: raw.college_scorecard
**Date:** 2026-04-05
**Agent:** @pii-scanner
**Spec:** raw-ingest-college-scorecard
**Domain:** Higher Education Outcomes (U.S. Department of Education College Scorecard)
**Records Scanned:** 69,947
**Columns Scanned:** 16
**PII Instances Found:** 0

---

### Scan Methodology

1. **Domain context review:** Read `governance/domain-context.md` (PII Expectations section) which confirms: "This dataset contains NO PII. All values are institutional identifiers, program codes, and aggregate statistical measures."
2. **Data sampling:** Inspected sample rows across all 16 columns to verify field contents match expected types (institution names, program codes, aggregate statistics, system metadata).
3. **Pattern matching:** Scanned all 69,947 rows across all 6 string columns (`instnm`, `cipcode`, `cipdesc`, `creddesc`, `source_url`, `source_method`) for PII patterns:
   - Email addresses: 0 matches
   - Social Security Numbers (NNN-NN-NNNN): 0 matches
   - Phone numbers: 0 matches
   - Standalone ZIP codes: 0 matches
4. **Contextual analysis:** Confirmed that all numeric fields (`unitid`, `credlev`, `md_earn_wne`, `earn_mdn_hi_1yr`, `earn_mdn_hi_2yr`, `debt_all_stgp_eval_mdn`, `ipedscount1`, `ipedscount2`) are institutional identifiers, categorical codes, or aggregate statistics -- not individual-level data.

### Findings

| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|-------------|-------------|------------|-------------------|-------------------|
| -- | -- | -- | -- | -- | -- | -- |

**No PII detected in any field.**

### Column-by-Column Assessment

| Column | Type | Assessment | Rationale |
|--------|------|------------|-----------|
| unitid | long | Not PII | IPEDS institutional identifier (6-digit code assigned to institutions, not individuals) |
| instnm | string | Not PII | Institution names (e.g., "California State University-Fresno") -- public organizational entities |
| cipcode | string | Not PII | Classification of Instructional Programs codes (e.g., "1107") -- academic taxonomy codes |
| cipdesc | string | Not PII | Program descriptions (e.g., "Computer Science.") -- public taxonomy labels |
| creddesc | string | Not PII | Credential description -- single value: "Bachelor's Degree" |
| credlev | int | Not PII | Credential level code -- single value: 3 |
| md_earn_wne | double | Not PII | Median earnings (institution-level) -- 100% null at this grain; structurally empty |
| earn_mdn_hi_1yr | double | Not PII | Aggregate median earnings (1-year post-completion) -- cohort-level statistic, not individual |
| earn_mdn_hi_2yr | double | Not PII | Aggregate median earnings (2-year post-completion) -- cohort-level statistic, not individual |
| debt_all_stgp_eval_mdn | double | Not PII | Aggregate median debt -- cohort-level statistic, not individual |
| ipedscount1 | long | Not PII | Aggregate completions count -- not individual-level |
| ipedscount2 | long | Not PII | Aggregate completions count -- not individual-level |
| ingested_at | timestamp | Not PII | System metadata (pipeline ingestion timestamp) |
| source_url | string | Not PII | System metadata (public government download URL) |
| source_method | string | Not PII | System metadata (single value: "bulk_csv_download") |
| load_date | date | Not PII | System metadata (pipeline load date) |

### Summary by Sensitivity

| Level | Count | Fields Affected |
|-------|-------|----------------|
| 1 - Public | 16 | All fields -- institutional and aggregate data from a public government dataset |
| 2 - Internal | 0 | None |
| 3 - Confidential | 0 | None |
| 4 - Restricted | 0 | None |

### False Positive Candidates

| Field | Detected As | Why It's Likely False | Recommendation |
|-------|-------------|----------------------|----------------|
| instnm | Could be flagged as "personal names" | Values are institution names (universities, colleges), not individual names. Confirmed by field context and sampling. | No action needed |
| unitid | Could be flagged as "identifier" | IPEDS institutional ID, not a personal identifier. Assigned to organizations, not individuals. | No action needed |

### Privacy Suppression Note

The Department of Education applies FERPA-compliant privacy suppression at the source. Programs with small cohorts (approximately fewer than 30 completers) have earnings and debt values suppressed (set to null) to prevent re-identification of individual students. This affects 60-64% of earnings/debt rows. The ingestor correctly converts "PrivacySuppressed" source values to null. **This is source-side FERPA compliance, not PII in our pipeline.**

### Regulatory Implications

- **FERPA:** Already handled at the data source. The Department of Education suppresses small-cohort data before publication. No additional FERPA action required by this pipeline.
- **GDPR:** Not applicable. This is U.S. institutional data with no European personal data.
- **CCPA:** Not applicable. No California consumer personal information present.
- **HIPAA:** Not applicable. No health records.
- **PCI DSS:** Not applicable. No payment card data.

### Recommendations

1. **No PII remediation needed.** All 16 columns contain public institutional data, aggregate statistics, or system metadata.
2. **No column masking required.** @policy-engineer can skip RLS and column masking for this table.
3. **No access restrictions based on PII.** Standard access controls sufficient.
4. **Privacy suppression is handled.** Null values in earnings/debt fields represent FERPA compliance by the data source. Do not attempt to reverse or fill suppressed values.
5. **Classification: Level 1 (Public).** This dataset is published by the U.S. government for public consumption. All fields can be treated as public data.
