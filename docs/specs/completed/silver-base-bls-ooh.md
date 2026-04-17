# Spec: silver-base-bls-ooh

**Status:** COMPLETE
**Zone:** Silver
**Primary Agent:** @primary-agent
**Created:** 2026-04-07

## Problem Statement

Transform raw BLS Employment Projections data from the Bronze zone into a clean, modeled Silver base table. This is the second Silver table in the FutureProof pipeline and the first occupation-level data to reach Silver — making it the anchor point for the CIP→SOC crosswalk that bridges College Scorecard programs to career outcomes.

The Silver transformation must normalize SOC codes for cross-source joining, handle the 7 rolled-up broad occupation codes, flag the 70 "all other" catch-all categories, classify occupations into the 22 SOC major groups with human-readable names, and shape the data for downstream Gold zone stat computation (ERN, GRW, Ceiling boss fight).

## Success Criteria

- [ ] `base.bls_ooh` Iceberg table exists with clean, modeled data
- [ ] SOC codes validated and normalized (XX-XXXX format preserved, no mutations)
- [ ] 7 rolled-up/broad occupation codes flagged via `broad_occupation_flag`
- [ ] 70 "all other" catch-all categories flagged via `catchall_flag`
- [ ] SOC major group code and name derived for every row
- [ ] Null-wage occupations (23 rows) preserved with `wage_available` flag — not dropped
- [ ] Employment figures validated as actual counts (already converted from thousands in Bronze)
- [ ] Education, experience, and training codes validated against known BLS ranges
- [ ] Grain integrity enforced: one row per SOC code (zero duplicates)
- [ ] Idempotent promote pattern used (re-runs produce 0 new rows)
- [ ] Deterministic `record_id` via `compute_grain_id()`
- [ ] Business glossary terms defined for all Silver fields
- [ ] Conceptual, logical, and physical models approved
- [ ] DQ rules written, executed, and passing (no P0 failures)
- [ ] Data contract produced for `base.bls_ooh`

## Source Data

- **Source Table:** `raw.bls_ooh` (Bronze zone)
- **Row Count:** 832 rows (detailed + broad occupations)
- **Grain:** soc_code (one row per occupation)
- **Projection Cycle:** 2024–2034
- **Key characteristics from Bronze hardening:**
  - 832 unique SOC codes, 100% valid XX-XXXX format
  - 23 null-wage occupations (17 physicians/surgeons, 5 performers, 1 fishing/hunting)
  - 232 declining occupations (27.9%)
  - 7 rolled-up/broad codes (ending in 0): 13-1020, 13-2020, 29-2010, 31-1120, 39-7010, 47-4090, 51-2090
  - 70 true "all other" catch-all categories (title contains "all other", case-insensitive — corrected from initial estimate of 46 after Silver EDA)
  - Max wage $238,380 — no capped wages in interactive export
  - Education codes 1–8, work experience codes 1–3, training codes 1–6

## Technical Design

### Iceberg Table: base.bls_ooh

- **Grain:** One row per occupation (soc_code)
- **Dedup grain fields:** [soc_code]
- **Promote pattern:** Use `brightsmith.infra.promote.promote()` for idempotent writes
- **Record ID:** `compute_grain_id(row, ['soc_code'], prefix='ooh')`

### Schema

#### Identity Fields
| Field | Type | Source Field | Required | Notes |
|-------|------|-------------|----------|-------|
| record_id | string | derived | yes | Deterministic grain hash (prefix: `ooh`) |
| soc_code | string | soc_code | yes | SOC occupation code, XX-XXXX format. Primary join key for O*NET and CIP-SOC crosswalk. |
| occupation_title | string | occupation_title | yes | Official BLS occupation name |
| soc_major_group | string | derived | yes | 2-digit SOC major group code (first 2 chars of soc_code) |
| soc_major_group_name | string | derived | yes | Major group description (e.g., "Management", "Computer and Mathematical") |

#### Classification Flags
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| broad_occupation_flag | boolean | derived | yes | True for 7 rolled-up/broad codes (SOC ending in 0 at position 5-6 where it combines detailed codes). These need special handling in crosswalk — may map to multiple O*NET detailed codes. |
| catchall_flag | boolean | derived | yes | True for occupations with "all other" in title (70 rows per Silver EDA). These are residual categories with weaker crosswalk signal. |

#### Employment & Projections
| Field | Type | Source Field | Required | Notes |
|-------|------|-------------|----------|-------|
| employment_current | long | employment_current | no | Current employment (actual count, already converted from thousands in Bronze) |
| employment_projected | long | employment_projected | no | Projected employment 2034 (actual count) |
| employment_change | long | employment_change | no | Absolute change in employment. Can be negative. |
| employment_change_pct | double | employment_change_pct | no | Percent change in employment. Can be negative. Backs GRW stat. |
| openings_annual_avg | long | openings_annual_avg | no | Average annual job openings (actual count) |
| growth_category | string | derived | yes | Bucketed employment_change_pct — see derivation rules below |

#### Compensation
| Field | Type | Source Field | Required | Notes |
|-------|------|-------------|----------|-------|
| median_annual_wage | double | median_annual_wage | no | Median annual wage in dollars. Null for 23 occupations. Backs ERN stat. |
| median_wage_capped | boolean | median_wage_capped | yes | True if Bronze flagged this as top-coded. Preserved even though interactive export had 0 capped wages — protects against future data source changes. |
| wage_available | boolean | derived | yes | True if median_annual_wage is not null. Convenience flag for downstream filtering. |

#### Education & Entry Requirements
| Field | Type | Source Field | Required | Notes |
|-------|------|-------------|----------|-------|
| education_typical | string | education_typical | no | Typical entry-level education label |
| education_code | int | education_code | no | BLS education level code (1=Doctoral, 2=Master's, 3=Bachelor's, 4=Associate's, 5=Postsecondary nondegree, 6=Some college, 7=High school, 8=No formal) |
| education_level_name | string | derived | no | Normalized education level name from code. Ensures consistent labeling. |
| work_experience | string | work_experience | no | Work experience requirement label |
| work_experience_code | int | work_experience_code | no | BLS work experience code (1=5+ years, 2=Less than 5 years, 3=None) |
| training_typical | string | training_typical | no | Typical on-the-job training label |
| training_code | int | training_code | no | BLS training code (1=Internship/residency, 2=Apprenticeship, 3=Long-term OJT, 4=Moderate-term OJT, 5=Short-term OJT, 6=None) |

#### Metadata
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| source_load_date | date | load_date | yes | Date of Bronze load |
| ingested_at | timestamp | generated | yes | Silver zone ingestion timestamp |

### SOC Major Group Lookup

| Code | Name |
|------|------|
| 11 | Management |
| 13 | Business and Financial Operations |
| 15 | Computer and Mathematical |
| 17 | Architecture and Engineering |
| 19 | Life, Physical, and Social Science |
| 21 | Community and Social Service |
| 23 | Legal |
| 25 | Educational Instruction and Library |
| 27 | Arts, Design, Entertainment, Sports, and Media |
| 29 | Healthcare Practitioners and Technical |
| 31 | Healthcare Support |
| 33 | Protective Service |
| 35 | Food Preparation and Serving Related |
| 37 | Building and Grounds Cleaning and Maintenance |
| 39 | Personal Care and Service |
| 41 | Sales and Related |
| 43 | Office and Administrative Support |
| 45 | Farming, Fishing, and Forestry |
| 47 | Construction and Extraction |
| 49 | Installation, Maintenance, and Repair |
| 51 | Production |
| 53 | Transportation and Material Moving |

### Growth Category Derivation

| Category | Range | Interpretation |
|----------|-------|----------------|
| declining_fast | employment_change_pct < -10.0 | Rapidly shrinking field |
| declining | -10.0 ≤ pct < -1.0 | Contracting field |
| stable | -1.0 ≤ pct < 1.0 | Flat employment |
| growing | 1.0 ≤ pct < 10.0 | Expanding field |
| growing_fast | 10.0 ≤ pct < 20.0 | Strong growth |
| booming | pct ≥ 20.0 | Exceptional growth |
| null | employment_change_pct is null | Insufficient data |

These thresholds are based on BLS convention — average growth across all occupations is typically 3-5% over a 10-year projection cycle, so ±1% is "stable" and ≥10% is notably strong.

### Education Level Name Lookup

| Code | Name |
|------|------|
| 1 | Doctoral or professional degree |
| 2 | Master's degree |
| 3 | Bachelor's degree |
| 4 | Associate's degree |
| 5 | Postsecondary nondegree award |
| 6 | Some college, no degree |
| 7 | High school diploma or equivalent |
| 8 | No formal educational credential |

### Broad Occupation Flag Logic

A SOC code is flagged as `broad_occupation_flag = True` when it represents an aggregation of multiple detailed occupations rather than a single specific occupation. The 7 known broad codes from the Bronze SOC audit are:

- 13-1020, 13-2020, 29-2010, 31-1120, 39-7010, 47-4090, 51-2090

Detection logic: these are the SOC codes identified in `governance/reviews/raw-bls-ooh-soc-codes.md` as "Rolled-Up / Broad Occupation Codes." They end in `0` at the detail level but are NOT major group summaries (those were already filtered in Bronze). Hardcode the list from the audit rather than pattern-matching — pattern matching would produce false positives (e.g., 29-2010 ends in 0 but so does 35-2011 which is a legitimate detailed code ending in 1, the trailing 0 in 29-2010 is at position 7, not a reliable heuristic).

**ConceptNormalizer implication:** In the CIP→SOC crosswalk and O*NET join, these 7 codes need special handling:
- They may match O*NET as parent codes with multiple children (e.g., 13-1020 → 13-1021 + 13-1022 in O*NET)
- The crosswalk should flag any joins through broad codes as lower-confidence
- Downstream Gold stat computation should note when stats derive from a broad rather than detailed occupation

### Catchall Flag Logic

`catchall_flag = True` when `occupation_title` contains the substring "all other" (case-insensitive). These are legitimate BLS categories representing residual occupations not individually classified within a minor group. They exist at the detail level (not summary level) and have real employment/wage data, but they're inherently heterogeneous — "Managers, all other" (11-9199) could be anything from a winery manager to a laundromat manager.

**Downstream implication:** Career guidance generated from catchall categories should carry a lower confidence tier. A student mapped to "Business operations specialists, all other" (13-1199) gets less actionable guidance than one mapped to "Management analysts" (13-1111).

### Transformations

1. **Read Bronze table** `raw.bls_ooh` via DuckDB
2. **Validate SOC code format** — confirm XX-XXXX pattern. Any violations are hard failures (0 expected based on Bronze hardening, but defend against future data changes)
3. **Derive SOC major group** — first 2 characters of soc_code
4. **Derive SOC major group name** — lookup from the 22-group table above
5. **Derive broad_occupation_flag** — match against hardcoded list of 7 broad SOC codes
6. **Derive catchall_flag** — case-insensitive substring match for "all other" in occupation_title
7. **Derive growth_category** — bucket employment_change_pct per thresholds above
8. **Derive wage_available** — `median_annual_wage IS NOT NULL`
9. **Derive education_level_name** — lookup from education_code
10. **Rename fields** — apply business-meaningful names (most already clean from Bronze; load_date → source_load_date)
11. **Compute record_id** — `compute_grain_id(row, ['soc_code'], prefix='ooh')`
12. **Promote** to `base.bls_ooh` via idempotent promote pattern

### Dropped Fields (from Bronze, with justification)

| Field | Reason |
|-------|--------|
| source_url | Raw metadata — not needed in Silver |
| source_method | Raw metadata — not needed in Silver |

### Transformer

- **Module:** `src/silver/bls_ooh_transformer.py`
- **Function:** `transform()`
- **Registration:** `domain/manifest.yaml` under `pipeline.zones.silver`
- **Pattern:** Read from `raw.bls_ooh`, transform, promote to `base.bls_ooh`

## Cross-Source Integration: The CIP→SOC Bridge

This Silver table is the first occupation-coded data in the pipeline. It establishes the SOC-side anchor for the CIP→SOC crosswalk.

### How the Crosswalk Works

The NCES/BLS CIP-SOC crosswalk is a published many-to-many mapping between CIP program codes and SOC occupation codes. It answers: "What occupations are associated with this academic program?"

- **College Scorecard Silver** (`base.college_scorecard`) has CIP codes (XX.XXXX format)
- **BLS OOH Silver** (`base.bls_ooh`, this spec) has SOC codes (XX-XXXX format)
- The crosswalk joins them: CIP → [crosswalk table] → SOC

### Crosswalk Implementation Decision

The CIP→SOC crosswalk table itself is a **separate Silver spec** (not part of this spec). It will:
- Ingest the published NCES CIP-SOC crosswalk file as a Bronze source
- Normalize to a Silver join table with `cipcode` and `soc_code` as the composite grain
- Enable joining `base.college_scorecard.cipcode` → crosswalk → `base.bls_ooh.soc_code`

This spec prepares the SOC side by ensuring:
- SOC codes are clean, validated, and in the correct format for joining
- Broad occupation codes are flagged so the crosswalk can handle them appropriately
- Catchall categories are flagged so downstream confidence scoring accounts for them
- The soc_major_group field enables fallback grouping when detailed crosswalk matches fail

### What This Enables in Gold

Once the crosswalk exists and O*NET reaches Silver, the Gold zone can produce:
- **ERN stat:** `median_annual_wage` from this table, linked to school+major via crosswalk
- **GRW stat:** `employment_change_pct` and `growth_category` from this table
- **Ceiling boss fight:** wage trajectory data (this table provides the entry-level anchor; BLS experience-level salary data — if available as a separate source — provides the progression)
- **Market boss fight:** `employment_change_pct` + `openings_annual_avg`
- **Education requirement context:** what level of education the occupation typically requires (helps Gemma generate "what to do in school" guidance)

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @data-steward — Identify business terms from spec
3. @semantic-modeler — Propose conceptual model → HUMAN APPROVAL GATE
4. @semantic-modeler — Propose logical model → HUMAN APPROVAL GATE
5. @semantic-modeler — Generate physical model from approved logical
6. @data-analyst — EDA on source data (profile raw.bls_ooh for Silver thresholds)
7. @dq-rule-writer — Write base DQ rules from EDA + logical model
8. @primary-agent — Implement transformer (must match approved physical model)
9. @dq-engineer — Execute all rules against real data, produce scorecard
10. @chaos-monkey — 5-cycle adversarial hardening
11. @lineage-tracker — OpenLineage capture
12. @cde-tagger — CDE mapping update
13. @doc-generator — Dictionary + contracts update
14. @governance-reviewer — Post-implementation completeness check
15. @staff-engineer — Final quality review

## Conditionally Skippable Agents

| Agent | Decision | Justification |
|-------|----------|---------------|
| @entity-resolver | SKIP | Single-source transformation. Cross-source entity resolution happens in the crosswalk spec, not here. |
| @pii-scanner | SKIP | Aggregated occupation-level statistics. No individual data. BLS public data. |
| @temporal-modeler | SKIP | Single-snapshot (2024–2034 projection cycle). Full table replace on refresh. No SCD needed yet. |
| @adversarial-auditor | RUN | This is the first occupation-level Silver table. The SOC codes, flags, and derived categories need adversarial scrutiny since they're the foundation for all downstream joins. |

## DQ Rules

To be written by @dq-rule-writer based on @data-analyst EDA findings.

Expected areas of focus:

**Grain & Identity**
- Grain uniqueness: soc_code = zero duplicates (832 expected unique)
- SOC code format: 100% valid XX-XXXX pattern
- Occupation title: 0% null, no truncation
- SOC major group: must be one of 22 valid codes
- SOC major group name: referential integrity against lookup table

**Classification Flags**
- broad_occupation_flag: exactly 7 True values (hardcoded list)
- catchall_flag: exactly 70 True values (title contains "all other", case-insensitive — corrected from 46 after Silver EDA)
- No overlap violations: broad_occupation_flag and catchall_flag can both be true for the same row (check if any of the 7 broad codes are also catchalls)

**Employment & Projections**
- employment_current: positive for all non-null rows
- employment_projected: positive for all non-null rows
- employment_change: can be negative (232 declining occupations expected)
- employment_change_pct: range check (-100.0 to +200.0) — anything outside this is suspect
- openings_annual_avg: >= 0 (4 tiny occupations with 0 openings per Bronze hardening)
- growth_category: must be one of the 7 valid values (including null)
- growth_category null only when employment_change_pct is null

**Compensation**
- median_annual_wage: range $15,000–$250,000 when not null
- median_annual_wage null count: exactly 23 (from Bronze hardening)
- wage_available: must match `median_annual_wage IS NOT NULL` exactly
- median_wage_capped: 0 True values expected (interactive export uses nulls, not caps)

**Education & Requirements**
- education_code: range 1–8 when not null
- education_level_name: referential integrity against lookup table
- work_experience_code: range 1–3 when not null
- training_code: range 1–6 when not null

**Row Count**
- Total rows: 832 (exact match with Bronze, allow +/- 0 — no rows should be added or dropped in Silver)

## Golden Dataset

At least 3 independently verifiable values from well-known occupations:

1. **Software Developers (15-1252)** — verify median wage, growth category (should be "growing" or higher), education_code = 3 (Bachelor's)
2. **Registered Nurses (29-1141)** — verify employment figures, education_code = 3, growth category
3. **A declining occupation** (e.g., from Office and Administrative Support group) — verify negative employment_change_pct maps to correct growth_category

Each golden value must be traceable: Bronze row → Silver derivation → expected output.

## Governance Artifacts

- [ ] Business glossary: `governance/business-glossary.json` (Silver-specific terms: SOC major group, broad occupation, catchall category, growth category)
- [ ] Conceptual model: `governance/models/silver-base-bls-ooh-conceptual.md`
- [ ] Logical model: `governance/models/silver-base-bls-ooh-logical.md`
- [ ] Physical model: `governance/models/silver-base-bls-ooh-physical.md`
- [ ] EDA report: `governance/eda/silver-bls-ooh-eda.md`
- [ ] DQ rules: `governance/dq-rules/silver-base-bls-ooh.json`
- [ ] DQ scorecard: `governance/dq-scorecards/silver-base-bls-ooh-scorecard.md`
- [ ] Chaos manifest: `governance/chaos-manifests/silver-base-bls-ooh-chaos.md`
- [ ] Lineage: `governance/lineage/silver-base-bls-ooh-{timestamp}.json`
- [ ] Data contract: `governance/data-contracts/base-bls-ooh.yaml`
- [ ] Staff review: `governance/reviews/silver-base-bls-ooh-staff-review.md`

## Open Decisions for Human Approval

1. **Growth category thresholds** — the buckets above are proposed based on BLS convention. Confirm or adjust before implementation.
2. **Broad occupation handling strategy** — this spec flags them. The crosswalk spec will need to decide: fan out to O*NET children, match as-is, or exclude? Flag here, decide there.
3. **Null-wage occupations** — this spec preserves them with a flag. Gold zone will need to decide how to handle ERN stat for careers that map to null-wage occupations (physicians especially — high-earning but no wage data in this source).

## Future Integration Notes

This Silver base table is the second of three base tables needed before Gold can produce cross-source data products:

1. **`base.college_scorecard`** — COMPLETE (69,947 rows, CIP codes)
2. **`base.bls_ooh`** — THIS SPEC (832 rows, SOC codes)
3. **`base.onet`** — PENDING (O*NET task/activity/pathway data, SOC codes)
4. **CIP→SOC crosswalk table** — PENDING (separate Silver spec, joins tables 1 and 2)

Once all four exist, Gold can produce the career outcomes data product that powers FutureProof's core loop: school + major → occupations → stats → boss fights → branches.
