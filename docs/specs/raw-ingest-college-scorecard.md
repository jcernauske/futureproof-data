# Spec: raw-ingest-college-scorecard

**Status:** DRAFT
**Zone:** Raw
**Primary Agent:** @primary-agent
**Created:** 2026-04-05

## Problem Statement
Ingest U.S. Department of Education College Scorecard field-of-study-level data into the bronze zone as the first step in the FutureProof pipeline. This data maps institutions and programs to career outcomes (median earnings, debt, employment) — the foundation for AI career guidance analysis.

## Success Criteria
- [ ] Raw data lands in Iceberg table `raw.college_scorecard`
- [ ] Dedup prevents duplicate records on subsequent runs
- [ ] Metadata fields populated (ingested_at, source_url, source_method, load_date)
- [ ] Privacy-suppressed values ("PrivacySuppressed") converted to null
- [ ] MVP filter applied: CREDLEV=3 (bachelor's degree only)
- [ ] Chunked reading handles ~500MB CSV without memory issues
- [ ] @data-analyst EDA report produced
- [ ] @domain-context document produced from EDA findings
- [ ] DQ rules written and passing

## Data Source
- **Source:** U.S. Department of Education College Scorecard (Field of Study)
- **Method:** Bulk CSV download
- **URL:** https://ed-public-download.app.cloud.gov/downloads/Most-Recent-Cohorts-Field-of-Study.csv
- **Entities:** All institutions x programs, filtered to CREDLEV=3 (bachelor's)
- **Size:** ~500MB, requires chunked reading
- **User-Agent:** FutureProof/0.1 (jeff@hyenastudios.com)

## Technical Design

### Iceberg Table: raw.college_scorecard
- **Grain:** One row per institution (UNITID) x program (CIPCODE) x credential level (CREDLEV)
- **Dedup grain:** [unitid, cipcode, credlev]

### Schema
| Field | Type | Required | Notes |
|-------|------|----------|-------|
| unitid | long | yes | Institution IPEDS ID |
| instnm | string | yes | Institution name |
| cipcode | string | yes | CIP program code (XX.XXXX) |
| cipdesc | string | no | Program description |
| creddesc | string | no | Credential description |
| credlev | int | yes | Credential level (3=bachelor's) |
| md_earn_wne | double | no | Median earnings (privacy-suppressed -> null) |
| earn_mdn_hi_1yr | double | no | Median earnings, 1yr post-completion |
| earn_mdn_hi_2yr | double | no | Median earnings, 2yr post-completion |
| debt_all_stgp_eval_mdn | double | no | Median debt at graduation |
| ipedscount1 | long | no | Completions count (first major) |
| ipedscount2 | long | no | Completions count (second major) |
| ingested_at | timestamp | yes | Ingestion timestamp |
| source_url | string | yes | Download URL |
| source_method | string | yes | "bulk_csv_download" |
| load_date | string | yes | Date of load (YYYY-MM-DD) |

### Ingestor
- **Class:** CollegeScorecardIngestor (extends BaseIngestor)
- **Location:** src/raw/college_scorecard_ingestor.py
- **Key implementation notes:**
  - Use `pandas.read_csv(..., chunksize=50_000)` for memory-safe reading
  - Replace "PrivacySuppressed" with None across all columns before type coercion
  - CIPCODE must remain a string (XX.XXXX format) — do not let pandas coerce to float
  - Set `User-Agent` header on download request

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
- Null rates on earnings/debt fields (expected high due to privacy suppression)
- CIPCODE format validation (XX.XXXX pattern)
- CREDLEV value range (1-6, MVP expects only 3)
- UNITID referential integrity against IPEDS
- Duplicate detection on grain fields

## Governance Artifacts
- [ ] EDA report: `governance/eda/raw-college-scorecard-eda.md`
- [ ] Domain context: `governance/domain-context.md`
- [ ] DQ rules: `governance/dq-rules/raw-ingest-college-scorecard.json`
- [ ] DQ scorecard: `governance/dq-scorecards/raw-ingest-college-scorecard-scorecard.md`
- [ ] Lineage: `governance/lineage/raw-ingest-college-scorecard-{timestamp}.json`
- [ ] Data dictionary entries for all raw table fields

## Future Integration Notes
This is the first of three data sources for FutureProof:
1. **College Scorecard** (this spec) — program-level outcomes, CIP codes
2. **BLS OOH** (future) — occupation descriptions and projections, SOC codes
3. **O*NET** (future) — task-level occupation data, SOC codes

The critical Silver zone challenge is the **CIP-to-SOC crosswalk** — mapping education
programs (CIP) to occupations (SOC) via the NCES/BLS crosswalk table. This enables
the core FutureProof question: "If I study X at school Y, what career outcomes can I expect?"
