## PII Scan Report: bronze.bls_oews
**Date:** 2026-05-06
**Agent:** @pii-scanner
**Domain:** U.S. Labor Market — Occupation-Level Wage Distribution (BLS OEWS sub-domain)
**Spec:** docs/specs/ingest-bls-oews-wage-percentiles.md
**Source:** Bureau of Labor Statistics, Occupational Employment and Wage Statistics (OEWS) Survey — National all-industries combined, May 2024 reference period
**Source URL:** https://www.bls.gov/oes/special-requests/oesm24nat.zip
**License:** U.S. Government Work — public domain
**Records Scanned:** 831 (full Bronze table; all detailed-SOC rows in May 2024 publication)
**PII Instances Found:** 0
**Verdict:** **NO_PII**

---

### Findings
| # | Field | PII Category | Sensitivity | Confidence | Sample (Redacted) | Recommended Action |
|---|-------|--------------|-------------|------------|-------------------|--------------------|
| — | — | — | — | — | — | No PII detected in any field |

---

### Field-by-Field Analysis (15 columns in `bronze.bls_oews`)
| Field | Data Type | PII Risk | Assessment |
|-------|-----------|----------|------------|
| `soc_code` | VARCHAR (XX-XXXX) | None | Standard Occupational Classification 2018 code. Federal taxonomy identifier maintained by OMB, not a personal identifier. 100% of rows match `^\d{2}-\d{4}$` (verified). Same join key used by BLS OOH and O*NET — none of those carry PII either. |
| `occupation_title` | VARCHAR | None | Occupation category label (e.g., "Registered Nurses", "Software Developers", "Tire Repairers and Changers", "Septic Tank Servicers and Sewer Pipe Cleaners"). Random sample of 25 rows confirms every value is a SOC-taxonomy job category, not a personal name. False-positive risk for NER name detectors is addressed below. |
| `total_employment` | BIGINT | None | National aggregate count of workers in the occupation (e.g., 632,430 LPN/LVNs). No individual-level resolution. |
| `wage_annual_p10` | DOUBLE | None | National 10th-percentile annual wage for the occupation. A distribution statistic across the full employment-weighted national sample, not an individual's compensation. |
| `wage_annual_p25` | DOUBLE | None | Same as above (p25). |
| `wage_annual_median` | DOUBLE | None | Same as above (median). |
| `wage_annual_p75` | DOUBLE | None | Same as above (p75). |
| `wage_annual_p90` | DOUBLE | None | Same as above (p90). May be top-coded at 239200.0; flagged via `wage_capped`. |
| `wage_annual_mean` | DOUBLE | None | Employment-weighted national mean wage for the occupation. Aggregate. |
| `wage_hourly_median` | DOUBLE | None | Hourly equivalent of the median wage; reference-only column. Aggregate. |
| `wage_capped` | BOOLEAN | None | Derived flag indicating BLS top-coding (≥$239,200). Carries a methodology disclosure, not personal data. |
| `ingested_at` | TIMESTAMP | None | Pipeline wall-clock metadata (ingest run time). Not a personal date — not a DOB, not a transaction date for any individual. |
| `source_url` | VARCHAR | None | Single distinct value: `https://www.bls.gov/oes/special-requests/oesm24nat.zip` — public BLS download endpoint. |
| `source_method` | VARCHAR | None | Single distinct value: `xlsx_download`. Pipeline provenance metadata. |
| `load_date` | DATE | None | Date the publication was ingested. Provenance metadata, not a personal date. |

**Total fields scanned:** 15. **Fields containing PII:** 0.

---

### Summary by Sensitivity
| Level | Count | Fields Affected |
|-------|-------|-----------------|
| 1 (Public) | 0 | — |
| 2 (Internal) | 0 | — |
| 3 (Confidential) | 0 | — |
| 4 (Restricted) | 0 | — |

---

### False Positive Candidates
| Field | Detected As | Why It's Likely False | Recommendation |
|-------|-------------|----------------------|----------------|
| `occupation_title` | Could trigger NER personal-name detection on multi-word titles such as "Marine Engineers and Naval Architects" or "Captains, Mates, and Pilots of Water Vessels" | These are SOC-taxonomy occupation category labels published by a federal statistical agency. They describe job classes, not individuals. The full domain (831 distinct values) is enumerated by OMB and contains zero personal names. | No action needed — confirmed non-PII. |
| `wage_annual_*`, `wage_hourly_median`, `wage_annual_mean` | Could trigger financial-PII heuristics (dollar-amount columns) | These are occupation-level distribution statistics across the full employment-weighted national sample. They are not linked to individuals and are published openly by BLS as aggregate statistics. | No action needed — confirmed non-PII. |
| `total_employment` | Could trigger headcount-PII heuristics | National employment counts in thousands of workers per occupation. No establishment-level or individual-level resolution. | No action needed — confirmed non-PII. |

---

### Source-Document Review
The OEWS publication is BLS's national, all-industries-combined wage distribution. By BLS publication policy, the public release contains:
- **No individual respondent data.** OEWS surveys ~200,000 establishments per panel, but published outputs are aggregated to the national/state/metro level. The National all-industries cut ingested here is the most-aggregated cut.
- **No establishment identifiers.** The published file contains SOC code, occupation title, total employment, and the six wage statistics — no `RESPONDENT_ID`, `ESTABLISHMENT_NAME`, address, or NAICS-keyed firm record reaches the pipeline.
- **Confidentiality protections already applied upstream.** Per 13 U.S.C. § 9 and BLS internal policy, the source file already top-codes values at $239,200 (sentinel `#`) and suppresses small-cell values (sentinel `*`). The Bronze ingestor preserves both signals (`wage_capped` flag for the cap, NULL for the suppression) without attempting to recover the underlying values.

The source file therefore cannot leak PII regardless of how the pipeline parses it: there is no PII in the source to leak. This is the same disposition documented for `bronze.bls_ooh` (BLS Employment Projections — also national, also occupation-aggregate, also zero PII).

---

### Cross-Table Risk
The downstream join surface is:
```
base.bls_oews
  → consumable.occupation_profiles  (LEFT JOIN on soc_code)
    → consumable.program_career_paths
```
SOC code is the only join key. The tables on the receiving end of these joins are all occupation-aggregate or program-aggregate data:
- `bronze.bls_ooh` / `base.bls_ooh` — occupation aggregates, **NO_PII** (per `governance/pii-scans/raw-ingest-bls-ooh-pii-scan.md`).
- `bronze.onet_*` / `base.onet_*` — task-level occupation data, **NO_PII** (per `governance/pii-scans/raw-ingest-onet-pii-scan.md`).
- `bronze.karpathy_ai_exposure` — SOC-keyed AI exposure scores, **NO_PII** (per `governance/pii-scans/raw-ingest-karpathy-ai-exposure-pii-scan.md`).
- `consumable.occupation_profiles`, `consumable.program_career_paths` — Gold-zone occupation/program aggregates; downstream contracts already flag `is_pii: false` on every column (per spec §"CDE/PII Classification (Gold)").

Joining `bronze.bls_oews` with any of these introduces no new PII because no contributing table contains PII to introduce. SOC is a federal taxonomy code and cannot become PII through joining.

The College Scorecard surfaces (`bronze.college_scorecard`, `bronze.college_scorecard_institution`) are reachable two hops downstream via the CIP→SOC crosswalk but contain only institutional and program-aggregate data with privacy suppression already applied by the U.S. Department of Education (FERPA-driven). Their existing PII scans confirm zero PII as well.

**Conclusion:** No cross-table join path introduces PII into a row originating from `bronze.bls_oews`.

---

### Domain Context Cross-Check
`governance/domain-context.md` §"Regulatory & Compliance Context (BLS OEWS)" → "PII Expectations" (lines 2725–2735) declares zero PII across all six PII categories considered (personal names, worker identifiers, establishment identifiers, health records, financial PII, location data) with the summary: *"This dataset contains NO PII. All values are occupation-level wage distribution statistics published by a federal statistical agency at the national, all-industries-combined level. The pipeline should report zero PII findings."*

This scan **confirms** that declaration against the actual landed `bronze.bls_oews` data. No discrepancies between declaration and observed data.

---

### Regulatory Implications
No PII was detected. No privacy regulations (GDPR, HIPAA, CCPA, FERPA) apply to this dataset. All data is published aggregate statistics from the Bureau of Labor Statistics, a federal statistical agency, under public-domain release. BLS confidentiality protections (top-coding, small-cell suppression) under 13 U.S.C. § 9 are already enforced upstream by the source publisher and preserved by the ingestor (`wage_capped` flag, NULL suppression).

---

### Recommendations
1. **No PII remediation required.** All 15 fields in `bronze.bls_oews` are occupation-level aggregate statistics, federal taxonomy codes, or pipeline provenance metadata. Zero individual-level data.
2. **No column masking or RLS policies needed** for PII reasons. Access controls, if any, should be based on business requirements (e.g., licensing, attribution) rather than privacy requirements.
3. **@policy-engineer:** Skip PII-based policy generation for `bronze.bls_oews`, `base.bls_oews`, and the four new wage columns (`wage_p10`, `wage_p25`, `wage_p75`, `wage_p90`) on `consumable.occupation_profiles` / `consumable.program_career_paths`. Retain the `is_cde: true`, `is_pii: false` classification declared in the spec.
4. **@cde-tagger:** Confirm `is_pii: false` on all four new Gold wage columns at contract version-bump time (`consumable-occupation-profiles` 1.0.0→1.1.0, `consumable-program-career-paths` 1.1.0→1.2.0).
5. **Justification reference:** `governance/domain-context.md` BLS OEWS PII section confirms zero PII. This scan empirically verifies the declaration against 831 of 831 landed Bronze rows.
