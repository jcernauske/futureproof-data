# Spec: raw-ingest-onet

**Status:** DRAFT
**Zone:** Raw (Bronze)
**Primary Agent:** @primary-agent
**Created:** 2026-04-07

## Problem Statement

Ingest the O*NET database into the Bronze zone. O*NET is the third and final primary data source for FutureProof. It is the richest and most complex source — 40 files covering 886 occupations with task-level work data, work context, work activities, skills, and career transition matrices.

FutureProof does not need all 40 files. This spec targets the **7 files** that directly feed FutureProof's five-stat system, boss fights, and Stage 3 career branching. The remaining files can be added post-hackathon.

## What O*NET Feeds in FutureProof

| FutureProof Element | O*NET File(s) | What It Provides |
|---------------------|---------------|------------------|
| **RES stat** (AI Resilience) | Task Statements, Work Activities | Task-level data for AI automation exposure scoring |
| **HMN stat** (Human Edge) | Work Activities | Work activity dimensions — human-skill intensity |
| **Burnout boss fight** | Work Context | Hours, stress, time pressure, schedule regularity |
| **AI boss fight** | Task Statements, Work Activities | Task automation susceptibility (combined with Karpathy scores) |
| **Stage 3 branching** | Career Changers Matrix, Related Occupations | Occupation-to-occupation transition paths |
| **Gemma career descriptions** | Occupation Data, Task Statements | Occupation definitions, specific task lists |
| **Skill tree generation** | Work Activities | What skills/activities this career requires |

## O*NET Files to Ingest (7 of 40)

### Tier 1: MUST SHIP (directly power stats and bosses)

| # | File | Description | Grain | Est. Rows | FutureProof Use |
|---|------|-------------|-------|-----------|-----------------|
| 1 | **Occupation Data** | O*NET-SOC code, title, description for each occupation | O*NET-SOC code | ~886 | Master occupation reference. Join key for all other files. |
| 2 | **Task Statements** | Occupation-specific task descriptions | O*NET-SOC × task_id | ~19,000 | "What tasks does this job involve?" Backs RES (which tasks can AI do?) and AI boss fight. |
| 3 | **Work Activities** | Generalized work activity ratings per occupation (importance + level) | O*NET-SOC × element_id × scale_id | ~71,000 | Backs HMN stat (human-skill dimensions). 41 generalized work activities rated per occupation. |
| 4 | **Work Context** | Physical/social work environment ratings per occupation | O*NET-SOC × element_id × scale_id | ~49,000 | Backs Burnout boss fight (hours, stress, time pressure, schedule). 57 context elements. |

### Tier 2: MUST SHIP (power Stage 3 branching)

| # | File | Description | Grain | Est. Rows | FutureProof Use |
|---|------|-------------|-------|-----------|-----------------|
| 5 | **Career Changers Matrix** | For each occupation, up to 10 related occupations that workers commonly transition to | source_soc × related_soc | ~8,000 | Stage 3 career branching — "where do people in this career go next?" |
| 6 | **Career Starters Matrix** | For each occupation, up to 10 related entry-point occupations | source_soc × related_soc | ~8,000 | Stage 3 branching and career path reconstruction |
| 7 | **Related Occupations** | For each occupation, 10 primary + 10 supplemental related occupations | source_soc × related_soc | ~17,000 | Broader career exploration, fallback for branching when changers/starters data is thin |

### Not In Scope (Post-Hackathon)

Skills, Knowledge, Abilities, Interests, Work Styles, Work Values, Tools & Technology, Education, Emerging Tasks, DWA/IWA references, Technology Skills, alternate titles. These enrich the product but aren't required for the five stats, boss fights, or Stage 3 branching.

## Data Source

- **Source:** O*NET 30.2 Database (current as of 2026)
- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0)
- **Method:** Bulk download — tab-delimited text files in ZIP archive
- **URL:** `https://www.onetcenter.org/dl_files/database/db_30_2_text.zip`
- **Format:** Tab-delimited text files with headers
- **Occupations:** 886 O*NET-SOC coded occupations
- **SOC Code Format:** O*NET uses extended SOC codes: `XX-XXXX.XX` (8-digit with 2-digit suffix). The base 6-digit SOC (`XX-XXXX`) maps to BLS. The `.XX` suffix distinguishes O*NET-specific detailed occupations within a BLS occupation.
- **User-Agent:** Standard browser-like headers (O*NET is less aggressive than BLS on bot blocking)
- **Fallback:** If download fails, read from `data/raw/onet_cache/` directory containing the extracted text files

## Technical Design

### Ingestor Architecture

Unlike College Scorecard (single file) and BLS OOH (single file), O*NET is **7 files from one ZIP archive**. The ingestor should:

1. Download the ZIP archive once
2. Extract the 7 target files
3. Parse each tab-delimited file
4. Land each as a separate Iceberg table in the `raw` namespace

### Iceberg Tables (7 tables)

#### 1. raw.onet_occupations
- **Source File:** `Occupation Data.txt`
- **Grain:** onet_soc_code
- **Schema:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| onet_soc_code | string | yes | O*NET-SOC code (XX-XXXX.XX format) |
| title | string | yes | Occupation title |
| description | string | yes | Occupation description/definition |
| ingested_at | timestamp | yes | Ingestion timestamp |
| source_url | string | yes | Download URL |
| source_method | string | yes | "bulk_zip_download" |
| load_date | date | yes | Date of load |

#### 2. raw.onet_task_statements
- **Source File:** `Task Statements.txt`
- **Grain:** onet_soc_code × task_id
- **Schema:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| onet_soc_code | string | yes | O*NET-SOC code |
| task_id | long | yes | Unique task identifier |
| task | string | yes | Task description text |
| task_type | string | no | "Core" or "Supplemental" |
| incumbents_responding | int | no | Number of survey respondents for this task |
| date | string | no | Data collection date |
| domain_source | string | no | "Occupational Expert" or "Incumbent" |
| ingested_at | timestamp | yes | |
| source_url | string | yes | |
| source_method | string | yes | |
| load_date | date | yes | |

#### 3. raw.onet_work_activities
- **Source File:** `Work Activities.txt`
- **Grain:** onet_soc_code × element_id × scale_id
- **Schema:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| onet_soc_code | string | yes | O*NET-SOC code |
| element_id | string | yes | Content Model element ID (e.g., "4.A.1.a.1") |
| element_name | string | yes | Activity name (e.g., "Getting Information") |
| scale_id | string | yes | "IM" (importance) or "LV" (level) |
| data_value | double | yes | Rating value (1-5 for IM, 0-7 for LV) |
| n | int | no | Sample size |
| standard_error | double | no | |
| lower_ci_bound | double | no | |
| upper_ci_bound | double | no | |
| recommend_suppress | string | no | "Y" or "N" — O*NET recommendation on data quality |
| not_relevant | string | no | "Y", "N", or "n/a" |
| date | string | no | |
| domain_source | string | no | |
| ingested_at | timestamp | yes | |
| source_url | string | yes | |
| source_method | string | yes | |
| load_date | date | yes | |

#### 4. raw.onet_work_context
- **Source File:** `Work Context.txt`
- **Grain:** onet_soc_code × element_id × scale_id
- **Schema:** Same structure as Work Activities (above). 57 context elements rated per occupation. Includes hours worked, time pressure, physical demands, social environment.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| onet_soc_code | string | yes | O*NET-SOC code |
| element_id | string | yes | Content Model element ID (e.g., "4.C.1.a.2.a") |
| element_name | string | yes | Context dimension name (e.g., "Time Pressure") |
| scale_id | string | yes | Scale identifier (context-specific) |
| data_value | double | yes | Rating value |
| n | int | no | Sample size |
| standard_error | double | no | |
| lower_ci_bound | double | no | |
| upper_ci_bound | double | no | |
| recommend_suppress | string | no | |
| not_relevant | string | no | |
| date | string | no | |
| domain_source | string | no | |
| category | int | no | Response category (for categorical context items) |
| ingested_at | timestamp | yes | |
| source_url | string | yes | |
| source_method | string | yes | |
| load_date | date | yes | |

#### 5. raw.onet_career_changers
- **Source File:** `Career Changers Matrix.txt`
- **Grain:** onet_soc_code × related_onet_soc_code
- **Schema:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| onet_soc_code | string | yes | Source occupation |
| related_onet_soc_code | string | yes | Related occupation (transition target) |
| index | int | yes | Rank (1-10, lower = more related) |
| ingested_at | timestamp | yes | |
| source_url | string | yes | |
| source_method | string | yes | |
| load_date | date | yes | |

#### 6. raw.onet_career_starters
- **Source File:** `Career Starters Matrix.txt`
- **Grain:** onet_soc_code × related_onet_soc_code
- **Schema:** Same structure as Career Changers Matrix.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| onet_soc_code | string | yes | Source occupation |
| related_onet_soc_code | string | yes | Related occupation (entry point) |
| index | int | yes | Rank (1-10, lower = more related) |
| ingested_at | timestamp | yes | |
| source_url | string | yes | |
| source_method | string | yes | |
| load_date | date | yes | |

#### 7. raw.onet_related_occupations
- **Source File:** `Related Occupations.txt`
- **Grain:** onet_soc_code × related_onet_soc_code
- **Schema:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| onet_soc_code | string | yes | Source occupation |
| related_onet_soc_code | string | yes | Related occupation |
| related_index | int | yes | Rank position |
| is_primary | boolean | yes | True for primary (1-10), False for supplemental (11-20) |
| ingested_at | timestamp | yes | |
| source_url | string | yes | |
| source_method | string | yes | |
| load_date | date | yes | |

### Ingestor Implementation

- **Class:** OnetIngestor (extends BaseIngestor)
- **Location:** `src/raw/onet_ingestor.py`
- **Key implementation notes:**
  - Single class handles all 7 files — parameterized by file config
  - Downloads ZIP once, extracts to `data/raw/onet_cache/`, parses each file
  - Tab-delimited parsing (not XLSX) — use Python `csv` module with `delimiter='\t'`
  - O*NET-SOC codes must remain as strings (XX-XXXX.XX format) — do not strip the `.XX` suffix in Bronze. Silver will handle SOC code normalization for cross-source joining.
  - The `recommend_suppress` and `not_relevant` fields are O*NET metadata flags — preserve them in Bronze, filter in Silver
  - Work Context has an extra `Category` column that Work Activities does not
  - Career matrices may have varying row counts across releases (~7,000–9,000)
  - Related Occupations has 20 rows per occupation (10 primary + 10 supplemental)

### Multi-Table Ingestor Pattern

This is the first multi-table ingestor in the pipeline. The ingestor should either:
- **(a)** Have a single `ingest()` method that processes all 7 files sequentially, or
- **(b)** Have a `ingest_file(file_config)` method called 7 times with different configs

Option (b) is preferred — it matches Brightsmith's pattern of one ingestor per table, but all share the same ZIP download. The `fetch()` method downloads and caches the ZIP; `flatten()` is called per file.

If Brightsmith's BaseIngestor pattern requires one ingestor per table, then create 7 thin ingestor subclasses that share a common `OnetBaseIngestor` parent handling the ZIP download.

## Success Criteria

- [ ] All 7 raw tables exist with correct schemas
- [ ] O*NET-SOC codes preserved in XX-XXXX.XX format (no truncation)
- [ ] Dedup prevents duplicate records on re-runs (per table grain)
- [ ] Metadata fields populated (ingested_at, source_url, source_method, load_date)
- [ ] Rating values preserved with full precision (doubles, not rounded)
- [ ] recommend_suppress and not_relevant flags preserved as-is
- [ ] @data-analyst EDA report produced (can be a single report covering all 7 tables)
- [ ] @domain-context document produced (append O*NET section)
- [ ] DQ rules written and passing for all 7 tables

## Expected Row Counts

| Table | Expected Rows | Notes |
|-------|---------------|-------|
| raw.onet_occupations | ~886 | One per O*NET-SOC occupation |
| raw.onet_task_statements | ~19,000 | Variable per occupation (5-30 tasks each) |
| raw.onet_work_activities | ~71,000 | ~886 occupations × 41 activities × 2 scales |
| raw.onet_work_context | ~49,000 | ~886 occupations × ~57 context elements × scales |
| raw.onet_career_changers | ~7,000–9,000 | Up to 10 transitions per occupation |
| raw.onet_career_starters | ~7,000–9,000 | Up to 10 entry points per occupation |
| raw.onet_related_occupations | ~17,000 | 20 per occupation (10 primary + 10 supplemental) |

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @primary-agent — Implement ingestor (fetch ZIP, extract, parse all 7 files)
3. @data-analyst — EDA + domain discovery (single comprehensive report)
4. @domain-context — Synthesize domain knowledge (append O*NET section to domain-context.md)
5. @dq-rule-writer — Write raw DQ rules from EDA (rules per table)
6. @dq-engineer — Execute rules, produce scorecard
7. @chaos-monkey — 5-cycle adversarial hardening
8. @lineage-tracker — OpenLineage capture (7 lineage events)
9. @cde-tagger — Initial CDE mapping
10. @doc-generator — Data dictionary entries (all 7 tables)
11. @governance-reviewer — Post-implementation check
12. @staff-engineer — Final review

## DQ Rules

To be written by @dq-rule-writer based on @data-analyst EDA findings.

Expected areas of focus per table:

**raw.onet_occupations:**
- O*NET-SOC code format: XX-XXXX.XX
- 0% nulls on code, title, description
- ~886 unique occupations

**raw.onet_task_statements:**
- O*NET-SOC code format validation
- Task description not null, not truncated
- Referential integrity: all onet_soc_codes exist in raw.onet_occupations

**raw.onet_work_activities:**
- Rating value ranges: IM scale 1-5, LV scale 0-7
- recommend_suppress distribution (expect mostly "N")
- Referential integrity to raw.onet_occupations

**raw.onet_work_context:**
- Rating value ranges (context-specific scales)
- Category field populated for categorical items
- Referential integrity to raw.onet_occupations

**raw.onet_career_changers / career_starters:**
- Index values 1-10
- Both SOC codes must be valid XX-XXXX.XX format
- Referential integrity: both codes exist in raw.onet_occupations
- No self-references (source ≠ related)

**raw.onet_related_occupations:**
- 20 rows per occupation (10 primary + 10 supplemental)
- is_primary flag consistency with index ranges

## Cross-Source Integration Notes

This is the third of three primary data sources for FutureProof:
1. **College Scorecard** (COMPLETE through Gold) — CIP codes, program outcomes
2. **BLS OOH** (COMPLETE through Gold) — SOC codes, occupation projections
3. **O*NET** (this spec) — O*NET-SOC codes, task/activity/context/pathway data

**SOC Code Alignment:**
- O*NET uses XX-XXXX.XX (8-digit). BLS uses XX-XXXX (6-digit).
- Most O*NET codes map to BLS as XX-XXXX.00 (base occupation)
- Some O*NET codes split a BLS occupation into details (e.g., BLS 29-1229 "Physicians, all other" → O*NET 29-1229.01, 29-1229.02, etc.)
- Silver zone will handle this mapping — truncating O*NET codes to 6-digit for BLS joining, preserving full codes for O*NET-internal joins
- The 7 rolled-up BLS broad codes may match multiple O*NET detailed codes — consistent with the Silver spec's broad_occupation_flag handling

## Governance Artifacts

- [ ] EDA report: `governance/eda/raw-onet-eda.md` (comprehensive, all 7 tables)
- [ ] Domain context: `governance/domain-context.md` (append O*NET section)
- [ ] DQ rules: `governance/dq-rules/raw-ingest-onet.json` (rules for all 7 tables)
- [ ] DQ scorecard: `governance/dq-scorecards/raw-ingest-onet-scorecard.md`
- [ ] Chaos manifest: `governance/chaos-manifests/raw-ingest-onet-chaos.md`
- [ ] Lineage: `governance/lineage/raw-ingest-onet-{timestamp}.json`
- [ ] Data dictionary: `governance/data-dictionary.json` (entries for all 7 tables)
- [ ] SOC code alignment audit: `governance/reviews/raw-onet-soc-codes.md`
- [ ] Staff review: `governance/reviews/raw-ingest-onet-staff-review.md`

## Open Decisions for Human Approval

1. **Multi-table ingestor pattern** — single class with per-file config, or 7 thin subclasses sharing a ZIP downloader? Depends on Brightsmith's BaseIngestor constraints.
2. **EDA as single report vs. 7 reports** — single comprehensive report is recommended for efficiency (one EDA pass covers all files), but check if Brightsmith expects one EDA per table.
3. **Row count tolerances** — O*NET updates quarterly and row counts shift. Set wide tolerances (±15%) on row count DQ rules for the matrix files, tighter (±5%) for occupation data.
