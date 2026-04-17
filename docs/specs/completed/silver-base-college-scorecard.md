# Spec: silver-base-college-scorecard

**Status:** COMPLETE
**Zone:** Silver
**Primary Agent:** @primary-agent
**Created:** 2026-04-06

## Problem Statement
Transform raw College Scorecard data into clean, modeled base tables in the Silver zone. This includes CIP code normalization (4-digit to XX.XXXX format), dropping the structurally empty `md_earn_wne` field, applying business-meaningful column names, and enforcing grain integrity. The result is a trusted, query-ready `base.college_scorecard` table that downstream Gold zone products can build on.

## Success Criteria
- [ ] `base.college_scorecard` Iceberg table exists with clean, modeled data
- [ ] CIP codes normalized to XX.XXXX format (dot inserted at position 2)
- [ ] `md_earn_wne` column dropped (100% null at field-of-study grain)
- [ ] All "PrivacySuppressed" handling preserved from raw (already null)
- [ ] Grain integrity enforced: unitid x cipcode x credlev (zero duplicates)
- [ ] Idempotent promote pattern used (re-runs produce 0 new rows)
- [ ] Deterministic `record_id` via `compute_grain_id()`
- [ ] Programs with < 30 completers flagged (not excluded) via `small_cohort_flag` boolean
- [ ] Business glossary terms defined for all Silver fields
- [ ] Conceptual, logical, and physical models approved
- [ ] DQ rules written, executed, and passing (no P0 failures)
- [ ] Data contract produced for `base.college_scorecard`

## Source Data
- **Source Table:** `raw.college_scorecard` (Bronze zone)
- **Row Count:** 69,947 rows
- **Grain:** unitid x cipcode x credlev (all credlev=3 in MVP)

## Technical Design

### Iceberg Table: base.college_scorecard
- **Grain:** One row per institution (unitid) x program (cipcode) x credential level (credlev)
- **Dedup grain fields:** [unitid, cipcode, credlev]
- **Promote pattern:** Use `brightsmith.infra.promote.promote()` for idempotent writes
- **Record ID:** `compute_grain_id(row, ['unitid', 'cipcode', 'credlev'], prefix='cs')`

### Schema
| Field | Type | Source Field | Required | Notes |
|-------|------|-------------|----------|-------|
| record_id | string | derived | yes | Deterministic grain hash |
| institution_control | string | control (source CSV) | yes | Public, Private nonprofit, or Private for-profit. Values: 1=Public, 2=Private nonprofit, 3=Private for-profit. Requires raw schema update to include CONTROL field. |
| unitid | long | unitid | yes | IPEDS institution ID (6-digit) |
| institution_name | string | instnm | yes | Official institution name |
| cipcode | string | cipcode | yes | CIP code normalized to XX.XXXX format |
| program_name | string | cipdesc | yes | Human-readable program description |
| credential_level | int | credlev | yes | Credential level (3=Bachelor's) |
| credential_description | string | creddesc | yes | "Bachelor's Degree" |
| earnings_1yr_median | double | earn_mdn_hi_1yr | no | Median earnings, 1yr post-completion (null = privacy suppressed) |
| earnings_2yr_median | double | earn_mdn_hi_2yr | no | Median earnings, 2yr post-completion (null = privacy suppressed) |
| debt_median | double | debt_all_stgp_eval_mdn | no | Median debt at graduation (null = privacy suppressed) |
| completions_count_1 | long | ipedscount1 | no | IPEDS completions (first major) |
| completions_count_2 | long | ipedscount2 | no | IPEDS completions (second major) |
| small_cohort_flag | boolean | derived | yes | True if completions_count_1 < 30 (privacy suppression likely) |
| cip_family | string | derived | yes | 2-digit CIP family code (first 2 chars of normalized cipcode) |
| cip_family_name | string | derived | yes | CIP family description (e.g., "Business, Management, Marketing") |
| source_load_date | date | load_date | yes | Date of source data load |
| ingested_at | timestamp | generated | yes | Silver zone ingestion timestamp |

### Raw Schema Dependency
The CONTROL field (institution control type: 1=Public, 2=Private nonprofit, 3=Private for-profit) exists in the source CSV (column 4) but was not included in the Bronze ingestor schema. The Silver transformer must either:
- (a) Update the raw ingestor to include CONTROL and re-ingest, or
- (b) Read CONTROL directly from the source CSV during Silver transformation

Option (a) is preferred for pipeline integrity.

### Dropped Fields (with justification)
| Field | Reason |
|-------|--------|
| md_earn_wne | 100% null — institution-level metric that does not populate in field-of-study file. Confirmed by user. |
| source_url | Raw metadata — not needed in Silver |
| source_method | Raw metadata — not needed in Silver |

### Transformations
1. **CIP code normalization:** Insert dot at position 2 (e.g., "5202" -> "52.02")
2. **CIP family extraction:** First 2 characters of normalized cipcode (e.g., "52")
3. **CIP family name lookup:** Map 2-digit CIP family to description using CIP taxonomy
4. **Low confidence flag:** `completions_count_1 is not null and completions_count_1 < 30` -> True
5. **Column rename:** Apply business-meaningful names per schema above
6. **Record ID:** Compute deterministic grain hash
7. **Drop md_earn_wne:** Remove structurally empty field

### Transformer
- **Module:** `src/silver/college_scorecard_transformer.py`
- **Function:** `transform()`
- **Registration:** `domain/manifest.yaml` under `pipeline.zones.silver`
- **Pattern:** Read from `raw.college_scorecard`, transform, promote to `base.college_scorecard`

## Agent Workflow (Greenfield)
1. @governance-reviewer — Pre-implementation review
2. @data-steward — Identify business terms from spec
3. @semantic-modeler — Propose conceptual model -> HUMAN APPROVAL GATE
4. @semantic-modeler — Propose logical model -> HUMAN APPROVAL GATE
5. @semantic-modeler — Generate physical model from approved logical
6. @data-analyst — EDA on source data (profile raw.college_scorecard for Silver thresholds)
7. @dq-rule-writer — Write base DQ rules from EDA + logical model
8. @primary-agent — Implement transformer (must match approved physical model)
9. @dq-engineer — Execute all rules against real data, produce scorecard
10. @chaos-monkey — 5-cycle adversarial hardening
11. @lineage-tracker — OpenLineage capture
12. @cde-tagger — CDE mapping update
13. @doc-generator — Dictionary + contracts update
14. @governance-reviewer — Post-implementation completeness check
15. @staff-engineer — Final quality review

## DQ Rules
To be written by @dq-rule-writer based on @data-analyst EDA findings.

Expected areas of focus:
- Grain uniqueness (unitid x cipcode x credlev = zero duplicates)
- CIP code format validation (XX.XXXX pattern after normalization)
- CIP family referential integrity (2-digit prefix must be valid CIP family)
- Null rates on earnings/debt fields (expect 60-65%, alert above 70%)
- Record count consistency with raw (69,947 rows expected, allow +/- 15%)
- Earnings range validation ($1,000-$250,000)
- Debt range validation ($1,000-$100,000)
- credlev = 3 (hard constraint)
- small_cohort_flag flag accuracy (must match completions_count_1 < 30)
- Institution count (2,200-3,000 distinct unitid values)

## Governance Artifacts
- [ ] Business glossary: `governance/business-glossary.json` (terms for Silver fields)
- [ ] Conceptual model: `governance/models/silver-base-college-scorecard-conceptual.md`
- [ ] Logical model: `governance/models/silver-base-college-scorecard-logical.md`
- [ ] Physical model: `governance/models/silver-base-college-scorecard-physical.md`
- [ ] EDA report: `governance/eda/silver-college-scorecard-eda.md`
- [ ] DQ rules: `governance/dq-rules/silver-base-college-scorecard.json`
- [ ] DQ scorecard: `governance/dq-scorecards/silver-base-college-scorecard-scorecard.md`
- [ ] Chaos manifest: `governance/chaos-manifests/silver-base-college-scorecard-chaos.md`
- [ ] Lineage: `governance/lineage/silver-base-college-scorecard-{timestamp}.json`
- [ ] Data contract: `governance/data-contracts/base-college-scorecard.yaml`
- [ ] Staff review: `governance/reviews/silver-base-college-scorecard-staff-review.md`

## User-Confirmed Decisions
These were confirmed by the user in the domain context interview follow-up:
1. CIP codes normalized to XX.XXXX in Silver (insert dot at position 2)
2. Drop md_earn_wne (structurally empty at this grain)
3. Minimum cohort size = 30 completers (flag below 30, don't exclude)
4. Institution count range 2,200-3,000 is fine for completeness check
5. 2yr < 1yr earnings is NOT an anomaly (different cohorts)
6. Full table replace for data refresh strategy
7. MCP target questions confirmed as the 5 assumed questions

## Future Integration Notes
This Silver base table is the foundation for:
- **CIP-to-SOC crosswalk** (separate Silver spec) — maps programs to occupations
- **Gold zone data products** — debt-to-earnings ratios, program rankings, institution comparisons
- **MCP server** — AI-queryable career guidance endpoint
