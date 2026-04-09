## Governance Review: raw-ingest-college-scorecard
**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-05
**Verdict:** APPROVED

---

### Checklist Results

#### 1. Required Sections

| Section | Status | Notes |
|---------|--------|-------|
| Problem Statement | PASS | Clear: ingest College Scorecard field-of-study data into bronze zone as foundation for AI career guidance |
| Success Criteria | PASS | 9 measurable criteria including table landing, dedup, metadata, privacy handling, filter, chunking, EDA, domain context, DQ |
| Data Source | PASS | Source, method, URL, entities, size, User-Agent all specified |
| Technical Design | PASS | Iceberg table name, grain, dedup grain, schema table, ingestor class and location defined |
| Schema | PASS | 16 fields with types, required flags, and notes |
| Agent Workflow | PASS | 11-step workflow listed with agent names |
| DQ Rules | PASS | 5 expected focus areas identified; rules to be written post-EDA by @dq-rule-writer |
| Governance Artifacts | PASS | 6 artifact paths listed with expected output locations |

#### 2. Schema Match: Spec vs. Ingestor Skeleton

The spec defines 16 fields. The `get_schema()` method in `src/raw/college_scorecard_ingestor.py` defines 16 fields. Field-by-field comparison:

| Field | Spec Type | Ingestor Type | Required Match | Status |
|-------|-----------|---------------|----------------|--------|
| unitid | long | LongType | yes/yes | PASS |
| instnm | string | StringType | yes/yes | PASS |
| cipcode | string | StringType | yes/yes | PASS |
| cipdesc | string | StringType | no/no | PASS |
| creddesc | string | StringType | no/no | PASS |
| credlev | int | IntegerType | yes/yes | PASS |
| md_earn_wne | double | DoubleType | no/no | PASS |
| earn_mdn_hi_1yr | double | DoubleType | no/no | PASS |
| earn_mdn_hi_2yr | double | DoubleType | no/no | PASS |
| debt_all_stgp_eval_mdn | double | DoubleType | no/no | PASS |
| ipedscount1 | long | LongType | no/no | PASS |
| ipedscount2 | long | LongType | no/no | PASS |
| ingested_at | timestamp | TimestampType | yes/yes | PASS |
| source_url | string | StringType | yes/yes | PASS |
| source_method | string | StringType | yes/yes | PASS |
| load_date | string | StringType | yes/yes | PASS |

**Result: PASS** -- All 16 fields match in name, type, and required flag between the spec and the ingestor skeleton.

#### 3. Grain Definition

| Check | Status | Notes |
|-------|--------|-------|
| Grain clearly stated | PASS | "One row per institution (UNITID) x program (CIPCODE) x credential level (CREDLEV)" |
| Dedup grain matches | PASS | Dedup grain listed as `[unitid, cipcode, credlev]` -- consistent with grain definition |
| Grain makes domain sense | PASS | College Scorecard field-of-study data is published at institution x program x credential level. This is the natural grain of the source. |
| Grain documented in ingestor | PASS | Ingestor docstring states: "Grain: institution (UNITID) x program (CIPCODE) x credential level (CREDLEV)" |

#### 4. Agent Workflow Alignment with Bronze Zone Pipeline

Comparing spec workflow to Brightsmith CLAUDE.md Bronze Zone Pipeline:

| Brightsmith Pipeline Step | Spec Step | Status | Notes |
|---------------------------|-----------|--------|-------|
| 1. @governance-reviewer (pre) | 1. @governance-reviewer | PASS | |
| 2. @primary-agent (implement) | 2. @primary-agent | PASS | |
| 3. @data-analyst (EDA) | 3. @data-analyst | PASS | |
| 4. @domain-context (synthesize) | 4. @domain-context | PASS | |
| 5. @dq-rule-writer (write rules) | 5. @dq-rule-writer | PASS | |
| 6. @dq-engineer (execute, scorecard) | 6. @dq-engineer | PASS | |
| 7. @chaos-monkey (adversarial) | -- | WARN | See Issue #1 below |
| 8. @lineage-tracker | 7. @lineage-tracker | PASS | |
| 9. @cde-tagger | 8. @cde-tagger | PASS | |
| 10. @doc-generator | 9. @doc-generator | PASS | |
| 11. @governance-reviewer (post) | 10. @governance-reviewer | PASS | |
| 12. @staff-engineer (final) | 11. @staff-engineer | PASS | |

#### 5. Data Source Completeness

| Detail | Status | Value |
|--------|--------|-------|
| Source name | PASS | U.S. Department of Education College Scorecard (Field of Study) |
| Method | PASS | Bulk CSV download |
| URL | PASS | `https://ed-public-download.app.cloud.gov/downloads/Most-Recent-Cohorts-Field-of-Study.csv` |
| Size estimate | PASS | ~500MB |
| Contact/User-Agent | PASS | `FutureProof/0.1 (jeff@hyenastudios.com)` |
| Entities/filter | PASS | All institutions x programs, filtered to CREDLEV=3 |

#### 6. DQ Rule Areas Identified

| Area | Status | Notes |
|------|--------|-------|
| Null rates on earnings/debt | PASS | Expected high due to privacy suppression -- good domain awareness |
| CIPCODE format validation | PASS | XX.XXXX pattern |
| CREDLEV value range | PASS | 1-6 range, MVP expects only 3 |
| UNITID referential integrity | PASS | Against IPEDS |
| Duplicate detection on grain | PASS | On grain fields |

Five areas identified. These cover the standard DQ categories for raw data (completeness, validity, volume/referential, uniqueness). Rules will be written post-EDA by @dq-rule-writer, which is the correct Bronze zone approach.

#### 7. Governance Artifact Paths

| Artifact | Path Listed | Status |
|----------|-------------|--------|
| EDA report | `governance/eda/raw-college-scorecard-eda.md` | PASS |
| Domain context | `governance/domain-context.md` | PASS |
| DQ rules | `governance/dq-rules/raw-ingest-college-scorecard.json` | PASS |
| DQ scorecard | `governance/dq-scorecards/raw-ingest-college-scorecard-scorecard.md` | PASS |
| Lineage | `governance/lineage/raw-ingest-college-scorecard-{timestamp}.json` | PASS |
| Data dictionary entries | Referenced (no explicit path) | PASS -- dictionary is a shared file |

#### 8. Bronze Zone Gate (Data Models)

**PASS (Not Applicable)** -- This is a Bronze zone spec. Per governance rules, Bronze zone specs skip the data model gate. Raw tables use physical-only models (data lands as-is). No business terms, conceptual models, logical models, or concept normalization required.

---

### Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | ADVISORY | Spec workflow omits **@chaos-monkey** (step 7 in Brightsmith Bronze pipeline). The framework requires 5-cycle adversarial hardening between @dq-engineer and @lineage-tracker. The spec should list @chaos-monkey explicitly to avoid silent omission during execution. | Add @chaos-monkey as a step between @dq-engineer and @lineage-tracker in the Agent Workflow section. Not blocking -- the pipeline gate will enforce this at runtime regardless. |
| 2 | ADVISORY | The spec lists `@primary-agent` as the primary agent in the header. This is correct for Bronze zone but could be more specific (the ingestor class name is `CollegeScorecardIngestor`). Minor readability note only. | No action required. |

---

### Decision Rationale

This spec is **APPROVED** for implementation. The rationale:

1. **Completeness:** All 8 required sections are present with substantive content. The problem statement is clear, success criteria are measurable, and the technical design is implementation-ready.

2. **Schema consistency:** The spec schema and ingestor skeleton `get_schema()` are in perfect alignment -- all 16 fields match in name, type, and required flag. This eliminates a common class of implementation drift.

3. **Grain clarity:** The grain (UNITID x CIPCODE x CREDLEV) is well-defined, matches the natural grain of the College Scorecard field-of-study data, and is consistent between the spec, the ingestor docstring, and the dedup grain definition.

4. **Agent workflow:** The workflow matches the Brightsmith Bronze Zone Pipeline with one advisory gap (@chaos-monkey omitted from the spec listing). This is not blocking because the pipeline gate enforces step ordering programmatically, but the spec should be updated for completeness.

5. **Data source:** All required details are present including URL, method, size estimate, and User-Agent for the download request.

6. **DQ readiness:** Five DQ focus areas are identified spanning completeness, validity, range, referential integrity, and uniqueness. Rules will be written post-EDA, which is the correct Bronze zone approach (data must be profiled before thresholds can be set).

7. **Bronze zone scope:** The spec correctly stays within Bronze zone boundaries -- no data modeling, business terms, or concept normalization are attempted. Future integration notes appropriately defer the CIP-to-SOC crosswalk to Silver zone.

The single advisory issue (@chaos-monkey omission) does not block implementation. The pipeline gate will enforce the chaos-monkey step at runtime. However, the spec author should add it to maintain spec-as-source-of-truth integrity.
