# Spec: crosswalk-cip-soc

**Status:** COMPLETE
**Zone:** Bronze + Silver (single spec covers both — small dataset, simple transformation)
**Primary Agent:** @primary-agent
**Created:** 2026-04-08

## Problem Statement

Ingest and normalize the NCES CIP-to-SOC crosswalk — the bridge table that connects College Scorecard programs (CIP codes) to BLS OOH and O*NET occupations (SOC codes). This is the final data pipeline component needed before the unified cross-source Gold product can be built.

Without this crosswalk, the three data sources are islands: College Scorecard knows about school+major earnings but not occupations, BLS OOH knows about occupation growth but not programs, O*NET knows about tasks and context but not schools. The crosswalk connects them: **CIP → SOC → everything else.**

## Data Source

- **Source:** NCES CIP 2020 to SOC 2018 Crosswalk
- **Publisher:** National Center for Education Statistics (NCES) + Bureau of Labor Statistics (BLS)
- **URL:** `https://nces.ed.gov/ipeds/cipcode/Files/CIP2020_SOC2018_Crosswalk.xlsx`
- **Format:** XLSX (single sheet, two columns + titles)
- **License:** Public domain (U.S. government publication)
- **Schema version:** CIP 2020 × SOC 2018
- **Relationship type:** Many-to-many. One CIP code can map to multiple SOC codes and vice versa.
- **Basis:** Expert judgment by NCES and BLS statisticians, NOT empirical data on actual graduate employment. The crosswalk says "this program typically prepares graduates for these occupations" — not "this is where graduates actually end up."
- **Coverage:** Not every CIP code has a SOC match (some programs are not career-oriented, e.g., "Liberal Arts"). Not every SOC code has a CIP match (some occupations don't require postsecondary education). CIP codes with no match are coded as SOC 99-9999.

## What This Crosswalk File Contains

The XLSX has 4 columns per the NCES documentation:

| Column | Description | Example |
|--------|-------------|---------|
| CIP Code | 6-digit CIP code in XX.XXXX format | 52.0201 |
| CIP Title | Program name | Business Administration and Management, General |
| SOC Code | 6-digit SOC code in XX-XXXX format | 11-1021 |
| SOC Title | Occupation name | General and Operations Managers |

Expected row count: ~3,000–5,000 (many-to-many pairs).

## Technical Design

### Bronze: raw.cip_soc_crosswalk

Simple ingest — download the XLSX, parse, land as-is.

**Grain:** cipcode × soc_code (one row per CIP-SOC pairing)

**Schema:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| cipcode | string | yes | CIP code in XX.XXXX format |
| cip_title | string | yes | Program name from crosswalk |
| soc_code | string | yes | SOC code in XX-XXXX format (or 99-9999 for "no match") |
| soc_title | string | yes | Occupation name from crosswalk (or "No Match" sentinel) |
| ingested_at | timestamp | yes | |
| source_url | string | yes | |
| source_method | string | yes | "xlsx_download" |
| load_date | date | yes | |

**Ingestor:**
- **Class:** CipSocCrosswalkIngestor (extends BaseIngestor)
- **Location:** `src/raw/cip_soc_crosswalk_ingestor.py`
- **Implementation:** Use `openpyxl` to read the XLSX. Parse 4 data columns. Add metadata fields. Land in `raw.cip_soc_crosswalk`.
- **Fallback:** If download fails, read from `data/raw/xlsx_cache/CIP2020_SOC2018_Crosswalk.xlsx`

### Silver: base.cip_soc_crosswalk

Light transformation — validate formats, exclude "no match" rows, add join-readiness flags.

**Grain:** cipcode × soc_code (one row per valid CIP-SOC pairing)

**Schema:**

| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| record_id | string | derived | yes | `compute_grain_id(row, ['cipcode', 'soc_code'], prefix='xw')` |
| cipcode | string | raw.cip_soc_crosswalk | yes | CIP code in XX.XXXX format. Joins to `base.college_scorecard.cipcode`. |
| cip_title | string | raw.cip_soc_crosswalk | yes | Program name |
| cip_family | string | derived | yes | 2-digit CIP family (first 2 chars). Matches `base.college_scorecard.cip_family`. |
| soc_code | string | raw.cip_soc_crosswalk | yes | SOC code in XX-XXXX format. Joins to `base.bls_ooh.soc_code` and `base.onet_occupations.bls_soc_code`. |
| soc_title | string | raw.cip_soc_crosswalk | yes | Occupation name |
| soc_major_group | string | derived | yes | 2-digit SOC major group (first 2 chars of soc_code). Matches `base.bls_ooh.soc_major_group`. |
| has_scorecard_match | boolean | derived | yes | True if cipcode exists in `base.college_scorecard`. Validates that the crosswalk CIP code has actual program data. |
| has_bls_match | boolean | derived | yes | True if soc_code exists in `base.bls_ooh`. Validates that the crosswalk SOC code has BLS projection data. |
| has_onet_match | boolean | derived | yes | True if soc_code exists in `base.onet_occupations`. Validates that the crosswalk SOC code has O*NET profile data. |
| match_quality | string | derived | yes | See derivation below |
| source_load_date | date | raw | yes | |
| ingested_at | timestamp | generated | yes | |

### Match Quality Derivation

| Quality | Criteria | Interpretation |
|---------|----------|----------------|
| full | has_scorecard_match AND has_bls_match AND has_onet_match | This CIP-SOC pair connects program data to full occupation data. Best quality for FutureProof. |
| partial_no_onet | has_scorecard_match AND has_bls_match AND NOT has_onet_match | Program links to BLS growth/wage but no O*NET task/activity/context data. Missing HMN and Burnout. |
| partial_no_bls | has_scorecard_match AND NOT has_bls_match AND has_onet_match | Program links to O*NET profile but no BLS projections. Missing GRW and Market. |
| scorecard_only | has_scorecard_match AND NOT has_bls_match AND NOT has_onet_match | Program has earnings data but no occupation-level data. Can compute ERN/ROI but not GRW/HMN/bosses. |
| no_scorecard | NOT has_scorecard_match | Crosswalk pair exists but no College Scorecard programs match this CIP. The pair is valid but won't be reached by student queries (no school+major data). |

### Filtering

- **Exclude "no match" rows** where soc_code = "99-9999" — these are CIP codes that the crosswalk explicitly says have no SOC correspondence
- **Preserve all other rows** including those where has_scorecard_match = False. These are valid crosswalk relationships that may become useful as College Scorecard coverage expands.
- **Do NOT attempt to match CIP codes at different granularity levels.** The crosswalk uses 6-digit CIP codes (XX.XXXX). College Scorecard Silver uses the same format. If a College Scorecard CIP doesn't match a crosswalk CIP, it's a coverage gap — don't try to fuzz-match at the 4-digit or 2-digit level in this spec. That's a Gold-zone enrichment.

### Transformations (Silver)

1. **Read Bronze** `raw.cip_soc_crosswalk`
2. **Filter out "no match" rows** (soc_code = "99-9999")
3. **Validate CIP format** — XX.XXXX pattern
4. **Validate SOC format** — XX-XXXX pattern
5. **Derive cip_family** — first 2 characters of cipcode
6. **Derive soc_major_group** — first 2 characters of soc_code
7. **Check has_scorecard_match** — LEFT JOIN to `base.college_scorecard` on cipcode, check if match exists (at least one row). Note: Scorecard has multiple rows per CIP (one per school), so use `EXISTS` or `DISTINCT cipcode`, not a full join.
8. **Check has_bls_match** — lookup soc_code in `base.bls_ooh`
9. **Check has_onet_match** — lookup soc_code in `base.onet_occupations`
10. **Derive match_quality** — from the three match flags per the rules above
11. **Compute record_id** and promote

### Transformer

- **Module:** `src/silver/cip_soc_crosswalk_transformer.py`
- **Function:** `transform()`
- **Pattern:** Read from `raw.cip_soc_crosswalk`, validate, join against 3 Silver tables for match flags, promote to `base.cip_soc_crosswalk`

## Success Criteria

- [ ] `raw.cip_soc_crosswalk` Bronze table exists
- [ ] `base.cip_soc_crosswalk` Silver table exists
- [ ] "No match" rows (soc_code = 99-9999) excluded from Silver
- [ ] CIP format validated: 100% XX.XXXX
- [ ] SOC format validated: 100% XX-XXXX
- [ ] has_scorecard_match, has_bls_match, has_onet_match flags populated correctly
- [ ] match_quality derived from flags
- [ ] Grain integrity: cipcode × soc_code = zero duplicates
- [ ] Idempotent promote
- [ ] DQ rules passing
- [ ] Data contract for `base.cip_soc_crosswalk`

## DQ Rules

Expected areas of focus:

**Bronze:**
- CIP format: 100% match XX.XXXX (allow for some edge cases — "99.9999" may appear)
- SOC format: 100% match XX-XXXX (including 99-9999 "no match" codes)
- Row count: 3,000–5,000 range
- Grain uniqueness: cipcode × soc_code = zero duplicates
- No nulls on any field

**Silver:**
- All "no match" rows excluded (0 rows with soc_code containing "99")
- cipcode format: 100% XX.XXXX
- soc_code format: 100% XX-XXXX
- cip_family: must be one of the valid 2-digit CIP families (check against `base.college_scorecard` distinct cip_family values)
- soc_major_group: must be one of 22 valid SOC major group codes
- match_quality: must be one of 5 valid values
- has_scorecard_match TRUE count: expect 60-90% of rows (most crosswalk CIPs should have Scorecard data)
- has_bls_match TRUE count: expect 70-95% of rows (most crosswalk SOCs should have BLS data)
- has_onet_match TRUE count: expect 65-90% of rows (O*NET covers fewer occupations than BLS)
- match_quality = "full" should be the plurality (ideally majority)

**Cross-table referential integrity (informational, not blocking):**
- Count of distinct cipcodes in crosswalk that match `base.college_scorecard` cipcodes
- Count of distinct soc_codes in crosswalk that match `base.bls_ooh` soc_codes
- Count of distinct soc_codes in crosswalk that match `base.onet_occupations` bls_soc_codes
- Report coverage gaps in both directions (Scorecard CIPs with no crosswalk entry, BLS SOCs with no crosswalk entry)

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @data-steward — Identify business terms
3. @semantic-modeler — Conceptual model → HUMAN APPROVAL GATE
4. @semantic-modeler — Logical model → HUMAN APPROVAL GATE
5. @semantic-modeler — Physical model
6. @primary-agent — Implement ingestor (Bronze) + transformer (Silver)
7. @data-analyst — EDA on Bronze data + Silver match analysis
8. @dq-rule-writer — DQ rules for both zones
9. @dq-engineer — Execute rules, produce scorecard
10. @chaos-monkey — 5-cycle hardening
11. @lineage-tracker — OpenLineage capture
12. @doc-generator — Dictionary + contracts
13. @governance-reviewer — Post-implementation check
14. @staff-engineer — Final review

## Conditionally Skippable Agents

| Agent | Decision | Justification |
|-------|----------|---------------|
| @entity-resolver | SKIP | CIP and SOC codes are deterministic identifiers from authoritative taxonomies. No fuzzy matching needed. |
| @pii-scanner | SKIP | Public taxonomy crosswalk. No individual data. |
| @temporal-modeler | SKIP | Static crosswalk (CIP 2020 × SOC 2018). Updated only when taxonomy versions change (~10 year cycles). |
| @adversarial-auditor | RUN | The match quality flags are the foundation for downstream confidence scoring. Need to verify the cross-table lookups work correctly and edge cases are handled. |

## Open Decisions for Human Approval

1. **CIP granularity mismatch handling.** College Scorecard may have CIP codes at 4-digit granularity (XX.XX) that don't exist in the 6-digit crosswalk (XX.XXXX). This spec does NOT attempt to match at different granularity levels. Should it? The alternative is a Gold-zone fallback that matches 4-digit CIPs to the most common 6-digit child in the crosswalk. For hackathon, leaving this to Gold or Gemma estimation seems right.

2. **Many-to-many cardinality impact.** One CIP code maps to multiple SOCs and vice versa. When a student picks Business Administration (CIP 52.0201), they'll see multiple career outcomes (Financial Analyst, Marketing Manager, Operations Manager, etc.). This is by design — it's the "career distribution" from the PRD. But it means the frontend/Gemma needs to present multiple outcomes, not one. Confirm this UX approach.

3. **Coverage gap reporting.** The EDA should report: (a) how many College Scorecard CIP codes have no crosswalk entry (students who pick these majors get no occupation data), and (b) how many BLS/O*NET SOC codes have no crosswalk entry (occupations that can't be reached from any program). These gaps should be documented and considered for Gemma estimation fallback.

## Governance Artifacts

- [ ] Business glossary: `governance/business-glossary.json` (crosswalk terms: CIP-SOC match, match quality)
- [ ] Conceptual model: `governance/models/crosswalk-cip-soc-conceptual.md`
- [ ] Logical model: `governance/models/crosswalk-cip-soc-logical.md`
- [ ] Physical model: `governance/models/crosswalk-cip-soc-physical.md`
- [ ] EDA report: `governance/eda/crosswalk-cip-soc-eda.md`
- [ ] DQ rules: `governance/dq-rules/crosswalk-cip-soc.json`
- [ ] DQ scorecard: `governance/dq-scorecards/crosswalk-cip-soc-scorecard.md`
- [ ] Chaos manifest: `governance/chaos-manifests/crosswalk-cip-soc-chaos.md`
- [ ] Lineage: `governance/lineage/crosswalk-cip-soc-{timestamp}.json`
- [ ] Data contract: `governance/data-contracts/base-cip-soc-crosswalk.yaml`
- [ ] Coverage gap report: `governance/reviews/crosswalk-coverage-gaps.md`
- [ ] Staff review: `governance/reviews/crosswalk-cip-soc-staff-review.md`

## What This Unlocks

With the crosswalk in Silver, the full join chain is complete:

```
Student picks: Indiana State University + Business Administration
                         |
            base.college_scorecard (cipcode = "52.0201")
                         |
                 base.cip_soc_crosswalk
                    /        |        \
           SOC 11-1021   SOC 13-1111   SOC 13-2051   (multiple careers)
              |              |              |
     base.bls_ooh    base.bls_ooh    base.bls_ooh     (growth, wage)
              |              |              |
  consumable.         consumable.    consumable.
  occupation_         occupation_    occupation_       (GRW, Market scores)
  profiles            profiles       profiles
              |              |              |
  consumable.         consumable.    consumable.
  onet_work_          onet_work_     onet_work_        (HMN, Burnout scores)
  profiles            profiles       profiles
              |              |              |
  consumable.career_transitions                        (Stage 3 branches)
```

The next spec after this is the **unified cross-source Gold product** that executes this join chain and produces a single queryable table powering the full FutureProof loop. Then `/bs:serve`.
