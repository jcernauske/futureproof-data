# Spec: raw-ingest-bls-ooh

**Status:** COMPLETE
**Zone:** Raw
**Primary Agent:** @primary-agent
**Created:** 2026-04-07

## Problem Statement
Ingest Bureau of Labor Statistics Employment Projections data (the structured backbone of the Occupational Outlook Handbook) into the bronze zone. This data provides occupation-level salary, growth projections, and education requirements keyed by SOC code — the second data source in the FutureProof pipeline, enabling the CIP-to-SOC bridge that connects college programs to career outcomes.

## Success Criteria
- [ ] Raw data lands in Iceberg table `raw.bls_ooh`
- [ ] Dedup prevents duplicate records on subsequent runs
- [ ] Metadata fields populated (ingested_at, source_url, source_method, load_date)
- [ ] Median wage special values handled (`>=239,200` → 239200.0 with capped flag; `N/A` → null)
- [ ] Employment figures converted from "in thousands" to actual counts
- [ ] SOC code validated as XX-XXXX format
- [ ] @data-analyst EDA report produced
- [ ] @domain-context document produced from EDA findings
- [ ] DQ rules written and passing

## Data Source
- **Source:** Bureau of Labor Statistics, Employment Projections program
- **Method:** XLSX download from EP data tables
- **URL:** https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm
- **Fallback:** Manual export from interactive database at https://data.bls.gov/projections/occupationProj
- **Entities:** ~832 detailed occupations, SOC 2018 classification
- **Size:** Small (~1MB XLSX), no chunking needed
- **User-Agent:** FutureProof/0.1 (jeff@hyenastudios.com)
- **Gotcha:** BLS aggressively blocks bot User-Agents with 403. Ingestor must use browser-like headers or fall back to reading a manually-downloaded file from `data/raw/xlsx_cache/`.

## Technical Design

### Iceberg Table: raw.bls_ooh
- **Grain:** One row per detailed occupation (SOC code)
- **Dedup grain:** [soc_code]

### Schema
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| soc_code | string | yes | SOC occupation code (XX-XXXX format) |
| occupation_title | string | yes | Occupation name |
| employment_current | long | no | Current employment (converted from thousands to actual) |
| employment_projected | long | no | Projected employment (converted from thousands to actual) |
| employment_change | long | no | Numeric change (converted from thousands to actual) |
| employment_change_pct | double | no | Percent change in employment |
| openings_annual_avg | long | no | Annual average openings (converted from thousands to actual) |
| median_annual_wage | double | no | Median annual wage in dollars; N/A → null |
| median_wage_capped | boolean | yes | True if original value was `>=239,200` (top-coded) |
| education_typical | string | no | Typical entry-level education (e.g., "Bachelor's degree") |
| education_code | int | no | BLS education level code (1-8) |
| work_experience | string | no | Work experience in related occupation |
| work_experience_code | int | no | BLS work experience code |
| training_typical | string | no | Typical on-the-job training |
| training_code | int | no | BLS training code |
| ingested_at | timestamp | yes | Ingestion timestamp |
| source_url | string | yes | Download URL |
| source_method | string | yes | "xlsx_download" |
| load_date | date | yes | Date of load (YYYY-MM-DD) |

### Ingestor
- **Class:** BlsOohIngestor (extends BaseIngestor)
- **Location:** src/raw/bls_ooh_ingestor.py
- **Key implementation notes:**
  - Use `openpyxl` for XLSX parsing (read_only mode)
  - Flexible column header matching via substring patterns — handles both interactive export and static table formats
  - Median wage handling:
    - `">=239,200"` or `"or more"` → 239200.0 with `median_wage_capped = True`
    - `"N/A"`, null, or missing → null with `median_wage_capped = False`
    - Numeric values (from interactive export) → parse directly, `median_wage_capped = False`
    - Note: interactive export uses null for high earners (not `>=` notation), so capped wages may be rare
  - Employment figures are reported "in thousands" — multiply by 1000 and round to long
  - SOC code must remain string format (XX-XXXX) — do not strip hyphens
  - Summary rows (SOC ending in 0000) filtered during fetch, not flatten
  - Education/experience/training codes derived from string labels when code columns are absent (the interactive export omits code columns; static EP tables include them)
  - If HTTP download returns 403, fall back to reading from `data/raw/xlsx_cache/bls_ooh.xlsx`
  - Set browser-like `User-Agent` and `Accept` headers on download request
  - Source data is 2024-2034 projection cycle (updated from initial 2023-2033 assumption)

## Agent Workflow
1. @governance-reviewer — Pre-implementation review
2. @primary-agent — Implement ingestor (fetch, flatten, get_schema)
3. @data-analyst — EDA + domain discovery
4. @domain-context — Synthesize domain knowledge
5. @dq-rule-writer — Write raw DQ rules from EDA
6. @dq-engineer — Execute rules, produce scorecard
7. @lineage-tracker — OpenLineage capture
8. @cde-tagger — Initial CDE mapping
9. @doc-generator — Data dictionary entries
10. @governance-reviewer — Post-implementation check
11. @staff-engineer — Final review

## DQ Rules
To be written by @dq-rule-writer based on @data-analyst EDA findings.

Expected areas of focus:
- SOC code format validation (XX-XXXX pattern, no trailing decimals)
- Median wage null rate and distribution (expect some N/A for non-standard-pay occupations)
- Capped wage flag consistency (median_wage_capped=True only when wage=239200)
- Employment figures must be positive (except employment_change which can be negative)
- Education code range validation (1-8)
- Duplicate detection on soc_code
- Occupation title completeness (expect 0% null)

## Governance Artifacts
- [ ] EDA report: `governance/eda/raw-bls-ooh-eda.md`
- [ ] Domain context: `governance/domain-context.md` (append BLS OOH section)
- [ ] DQ rules: `governance/dq-rules/raw-ingest-bls-ooh.json`
- [ ] DQ scorecard: `governance/dq-scorecards/raw-ingest-bls-ooh-scorecard.md`
- [ ] Lineage: `governance/lineage/raw-ingest-bls-ooh-{timestamp}.json`
- [ ] Data dictionary entries for all raw table fields

## Cross-Source Integration Notes
This is the second of three data sources for FutureProof:
1. **College Scorecard** (COMPLETE) — program-level outcomes, CIP codes
2. **BLS OOH** (this spec) — occupation projections and requirements, SOC codes
3. **O*NET** (future) — task-level occupation data, SOC codes

The SOC code in this table is the **primary join key** for Silver zone integration:
- **CIP-to-SOC crosswalk** links College Scorecard programs to BLS occupations
- **SOC direct join** links BLS OOH to O*NET task-level data (same SOC taxonomy)
- SOC 2018 classification is the current standard; watch for SOC 2028 migration

This enables FutureProof's core question: "If I study X at school Y, what career outcomes
can I expect?" by bridging education programs (CIP) → occupations (SOC) → outcomes/projections.
