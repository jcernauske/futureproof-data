# LICENSE_SOURCES.md

This file is the consolidated license ledger for every external dataset used
in the FutureProof pipeline. Each source section lists: license type, canonical
URL, required attribution string, citation requirement, and the Iceberg tables
or Gold data products that the source powers. When adding a new source to the
pipeline, add its section here and link from the Bronze data contract's
`license:` block.

**Maintained by:** @doc-generator
**Last updated:** 2026-04-16
**Governance cross-references:**
- `governance/data-contracts/` — per-table `license:` blocks mirror the sections below
- `governance/cde-tagging/` — CDE flags on source_release / data_year / load_date fields carry per-record provenance

---

## College Scorecard (Field of Study)

- **Source:** https://collegescorecard.ed.gov/data/
- **Publisher:** U.S. Department of Education
- **License:** Public domain (U.S. Government work, 17 U.S.C. § 105).
  No attribution legally required, but good-faith citation expected for
  academic use.
- **Citation:** "U.S. Department of Education, College Scorecard Field of
  Study dataset, Most Recent Cohorts."
- **Used in:**
  - `raw.college_scorecard` — 69,947 program-institution rows
  - `base.college_scorecard` — normalized program data
  - `consumable.career_outcomes` — ERN/ROI pentagon stat, effort slider
  - `consumable.program_career_paths` — school+major -> career lookup (core table)
- **Attribution requirement:** Optional but recommended in any published
  FutureProof analysis or report.

## College Scorecard (Institution)

- **Source:** https://collegescorecard.ed.gov/data/
- **Publisher:** U.S. Department of Education
- **License:** Public domain (U.S. Government work).
- **Citation:** "U.S. Department of Education, College Scorecard Institution
  dataset, Most Recent Cohorts."
- **Used in:**
  - `raw.college_scorecard_institution` — institution-level rows
  - `base.college_scorecard_institution` — normalized institution data
- **Attribution requirement:** Optional but recommended.

## BLS Occupational Outlook Handbook (OOH)

- **Source:** https://www.bls.gov/ooh/
- **Publisher:** U.S. Bureau of Labor Statistics
- **License:** Public domain (U.S. Government work).
- **Citation:** "U.S. Bureau of Labor Statistics, Occupational Outlook
  Handbook."
- **Used in:**
  - `raw.bls_ooh` — 832 occupation rows
  - `base.bls_ooh` — normalized occupation data
  - `consumable.occupation_profiles` — GRW stat, Ceiling boss, Market boss
- **Attribution requirement:** Optional but recommended when wages or
  occupation projections are cited.

## O*NET (Occupational Information Network)

- **Source:** https://www.onetonline.org/
- **Publisher:** O*NET Resource Center, sponsored by the U.S. Department of
  Labor, Employment and Training Administration (USDOL/ETA).
- **License:** CC BY 4.0 (Creative Commons Attribution 4.0 International).
- **Citation:** "O*NET OnLine, developed under the sponsorship of the
  U.S. Department of Labor/Employment and Training Administration (USDOL/ETA)."
- **Used in:**
  - `raw.onet_occupations` — 923 O*NET occupations
  - `raw.onet_task_statements` — 19,530 task statements
  - `raw.onet_work_activities` — work activity profiles
  - `raw.onet_work_context` — work context profiles
  - `raw.onet_related_occupations` — related occupation transitions
  - `raw.onet_experience` — experience/education/training requirements
  - `base.onet_occupations`, `base.onet_activity_profiles`,
    `base.onet_context_profiles`, `base.onet_career_transitions`,
    `base.onet_experience_profiles`
  - `consumable.onet_work_profiles` — HMN stat, Burnout boss
  - `consumable.career_transitions`, `consumable.career_branches` —
    Stage 3 branching graph
- **Attribution requirement:** **Required.** Any published analysis, product
  feature, or API response that surfaces O*NET-derived content must credit
  O*NET. The MCP `get_task_breakdown` and `get_career_branches` tools SHOULD
  include "Source: O*NET OnLine (CC BY 4.0)" in their response metadata.

## CIP-SOC Crosswalk

- **Source:** https://nces.ed.gov/ipeds/cipcode/
- **Publisher:** National Center for Education Statistics (NCES), U.S.
  Department of Education.
- **License:** Public domain (U.S. Government work).
- **Citation:** "NCES, Classification of Instructional Programs (CIP) to
  Standard Occupational Classification (SOC) Crosswalk."
- **Used in:**
  - `raw.cip_soc_crosswalk` — CIP <-> SOC mappings
  - `base.cip_soc_crosswalk` — normalized crosswalk
  - `consumable.program_career_paths` — critical join enabling program->career lookup
- **Attribution requirement:** Optional but recommended.

## Karpathy AI Exposure Scores

- **Source:** https://github.com/karpathy/jobs
- **Publisher:** Andrej Karpathy (personal repository)
- **License:** MIT License.
- **Citation:** "Karpathy, A. (2024). AI exposure scores for BLS
  occupations. https://github.com/karpathy/jobs"
- **Used in:**
  - `raw.karpathy_ai_exposure` — 342 occupation exposure scores
  - `base.karpathy_ai_exposure` — normalized and BLS-matched (419 rows)
  - `consumable.ai_exposure` — RES pentagon stat, Fight AI boss score
    (fields: `exposure_score`, `rationale`, `category`, `stat_res`,
    `boss_ai_score`, `karpathy_score`)
- **Attribution requirement:** Retain the MIT license notice on any
  redistribution of the raw data. MCP responses surfacing `exposure_score`
  or the derived `stat_res`/`boss_ai_score` SHOULD credit Karpathy.

## Anthropic Economic Index

- **Source:** https://huggingface.co/datasets/Anthropic/EconomicIndex
- **Publisher:** Anthropic
- **License:** CC-BY 4.0 International
- **Citation:** "Economic Index Dataset, Anthropic (2026)"
- **Used in:**
  - `raw.anthropic_economic_index` — 4,082 (task, SOC) rows
    (release_2025_03_27)
  - `base.anthropic_observed_exposure` — 588 SOC-level aggregates
  - `consumable.ai_exposure` (v1.1.0 additive fields):
    `observed_exposure_pct`, `automation_pct`, `anthropic_task_count`,
    `anthropic_source_release`
- **Release pinned:** `release_2025_03_27` (later HuggingFace releases
  `release_2026_01_15` and `release_2026_03_24` contain only raw conversation
  snapshots and lack `task_pct_v2.csv`).
- **Attribution requirement:** Credit Anthropic in any published analysis
  using this data. MCP responses that surface `observed_exposure_pct` should
  include the attribution string built from `anthropic_source_release`, e.g.:
  `Source: Anthropic Economic Index v2, release 2025-03-27, CC-BY 4.0`.
  The pinned release id is carried on every row; provenance is per-record.

## BEA Regional Price Parities (RPP)

- **Source:** https://apps.bea.gov/regional/ (Regional Economic Accounts,
  table SARPP)
- **Publisher:** U.S. Bureau of Economic Analysis (BEA)
- **License:** Public domain (U.S. Government statistical publication).
- **Citation:** "U.S. Bureau of Economic Analysis, Regional Price Parities
  by State, Table SARPP, 2024 release (February 2026)."
- **Used in:**
  - `raw.bea_rpp` — 51 state rows (50 states + DC), 2024 vintage
  - `base.bea_rpp` — normalized state-level RPP
  - `consumable.regional_price_parities` — cost-of-living adjustment
  - MCP tools `get_regional_price_parity`, `compare_purchasing_power`
- **Attribution requirement:** Optional but recommended. Since the BEA is a
  U.S. Government statistical agency, attribution is expected practice for
  published analyses.

---

## Change Log

| Date | Change | By |
|------|--------|----|
| 2026-04-16 | Created. Consolidated 7 sources (College Scorecard Field of Study, College Scorecard Institution, BLS OOH, O*NET, CIP-SOC Crosswalk, Karpathy, BEA RPP). Added **Anthropic Economic Index** with CC-BY 4.0 attribution requirement and release-pinning note. | @doc-generator |

---

## Policy: Adding a New Source

When a new external dataset is ingested:
1. Add a section to this file (copy any existing section as a template).
2. Include: source URL, publisher, license type + text, citation format,
   list of Iceberg tables / Gold products powered, and the exact attribution
   requirement.
3. Add a `license:` block to the Bronze data contract that mirrors the
   license type, attribution, URL, and `requires_citation` flag.
4. If the license requires per-record attribution (e.g., CC-BY 4.0), the
   `source_release` / `data_year` / equivalent provenance field MUST be
   flagged CDE in `governance/cde-tagging/` so that governance tooling
   surfaces it on every downstream consumer.
5. MCP responses that surface license-encumbered fields MUST include the
   attribution string, built from the CDE provenance field.
