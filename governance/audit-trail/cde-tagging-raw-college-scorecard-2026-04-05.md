## CDE/PII Tagging Report: raw-ingest-college-scorecard
**Date:** 2026-04-05
**Agent:** @cde-tagger
**Contract:** governance/data-contracts/raw-college-scorecard.yaml
**Zone:** Bronze (Raw)
**Table:** raw.college_scorecard

### Domain Context Referenced
- governance/domain-context.md (2026-04-05) -- Higher Education Outcomes domain
- Regulatory context: FERPA (privacy suppression explains null patterns), HEA (public data mandate), Gainful Employment rules (debt-to-earnings ratios)
- PII expectations: Domain context confirms NO PII in this dataset. All fields are institutional identifiers, program codes, or cohort-level aggregate statistics. Privacy is enforced at the source by Department of Education suppression rules.
- Business context: FutureProof uses this data to map education programs to career outcomes. The CIP-to-SOC crosswalk in Silver zone depends on grain fields from this table. Earnings and debt metrics are the core business value.

### Columns Flagged as CDE
| Column | Table | Rationale |
|--------|-------|-----------|
| unitid | raw.college_scorecard | Grain field -- uniquely identifies the institution. Required for entity resolution, downstream joins, and all aggregations. |
| cipcode | raw.college_scorecard | Grain field -- identifies the academic program. Foundation for the CIP-to-SOC crosswalk that enables career outcome mapping. |
| credlev | raw.college_scorecard | Grain field -- defines credential level dimension. Validates CREDLEV=3 filter correctness. Part of dedup grain. |
| earn_mdn_hi_1yr | raw.college_scorecard | Primary business metric -- median earnings 1yr post-completion. Core to FutureProof career guidance value proposition. |
| earn_mdn_hi_2yr | raw.college_scorecard | Primary business metric -- median earnings 2yr post-completion. Multi-horizon graduate outcome view. |
| debt_all_stgp_eval_mdn | raw.college_scorecard | Primary business metric -- median student debt. Required for debt-to-earnings analysis and program cost-benefit assessment. |

### Columns Flagged as PII
| Column | Table | Rationale |
|--------|-------|-----------|
| (none) | | Domain context confirms zero PII. All data is institutional/aggregate. |

### Columns Evaluated -- Not Flagged
| Column | Table | Reason Not Critical/Sensitive |
|--------|-------|-------------------------------|
| instnm | raw.college_scorecard | Display label only; UNITID is the authoritative identifier. Not used for joins or grain. |
| cipdesc | raw.college_scorecard | Display label for CIP code. 1:1 mapping with cipcode. Descriptive, not operational. |
| creddesc | raw.college_scorecard | Display label for credlev. Redundant with credlev in MVP (always "Bachelor's Degree"). |
| md_earn_wne | raw.college_scorecard | Structurally 100% null at this grain. Institution-level metric that does not populate in field-of-study data. No downstream value. |
| ipedscount1 | raw.college_scorecard | Program size context metric. Useful but not a primary decision driver or regulatory requirement. |
| ipedscount2 | raw.college_scorecard | Second measurement window completions count. Highly correlated with ipedscount1. Supporting metric only. |
| ingested_at | raw.college_scorecard | Pipeline metadata -- operational, not business-critical. |
| source_url | raw.college_scorecard | Pipeline metadata -- provenance tracking only. |
| source_method | raw.college_scorecard | Pipeline metadata -- provenance tracking only. |
| load_date | raw.college_scorecard | Pipeline metadata -- operational, not business-critical. |

### Summary
- **Total columns evaluated:** 16
- **CDEs flagged:** 6 (3 grain fields + 3 business metrics)
- **PII flagged:** 0
- **CDE density:** 37.5% (expected for a bronze zone table with metadata columns)
