# Audit Trail: @doc-generator for raw-ingest-bls-ooh

**Date:** 2026-04-07
**Agent:** @doc-generator
**Spec:** docs/specs/raw-ingest-bls-ooh.md
**Action:** Added data dictionary entries for raw.bls_ooh (19 fields)

## What Was Done

Added a new table entry `raw.bls_ooh` to `governance/data-dictionary.json` with all 19 fields documented:

### Data Fields (15)
| Field | Type | CDE | Source Column |
|-------|------|-----|---------------|
| soc_code | string | Yes | Matrix Code (SOC) |
| occupation_title | string | Yes | Matrix Title (Occupation) |
| employment_current | long | No | Employment, 2023 (in thousands) |
| employment_projected | long | No | Employment, 2033 (in thousands) |
| employment_change | long | No | Change, Numeric (in thousands) |
| employment_change_pct | double | Yes | Change, Percent |
| openings_annual_avg | long | No | Occupational Openings (annual avg) |
| median_annual_wage | double | Yes | Median Annual Wage |
| median_wage_capped | boolean | No | Derived from Median Annual Wage |
| education_typical | string | No | Typical Education Needed |
| education_code | int | Yes | Education Code |
| work_experience | string | No | Work Experience in a Related Occupation |
| work_experience_code | int | No | Work Experience Code |
| training_typical | string | No | Typical On-the-Job Training |
| training_code | int | No | Training Code |

### Metadata Fields (4)
| Field | Type | CDE | Source |
|-------|------|-----|--------|
| ingested_at | timestamp | No | Pipeline-generated |
| source_url | string | No | Pipeline-generated |
| source_method | string | No | Pipeline-generated |
| load_date | string | No | Pipeline-generated |

## CDE Fields (5)
- **soc_code** — Grain field and primary cross-source join key for CIP-to-SOC crosswalk and O*NET integration
- **occupation_title** — Required for display in all downstream career guidance products
- **employment_change_pct** — Primary growth/decline metric for career outlook analysis
- **median_annual_wage** — Primary salary metric for career guidance
- **education_code** — Required for matching occupations with education pathways

## DQ Rule Cross-References
All 18 approved DQ rules from `governance/dq-rules/raw-ingest-bls-ooh.json` were cross-referenced in field entries. Rules RAW-OOH-001 through RAW-OOH-018 are linked to their respective fields.

## Lineage Cross-Reference
All fields reference the lineage file at `governance/lineage/raw-ingest-bls-ooh-20260407T120000Z.json`.

## Interpretation Decisions

1. **occupation_title marked as CDE.** The CDE tagger flagged soc_code and occupation_title as CDEs. While occupation_title is a display label (not a join key), it is critical for end-user comprehension of all downstream products.

2. **record_count set to null.** The EDA is based on a 10-row sample. The full dataset (~832 rows) has not yet been ingested. Set record_count to null with an explanatory note rather than recording the sample count as authoritative.

3. **Nullable fields.** Employment figures, education/experience/training fields, and employment_change_pct are marked nullable per the spec schema (required=no). In practice, the EDA shows 0% null rate in sample for most fields, but median_annual_wage has expected nulls (~2-4% for N/A occupations).

4. **PII assessment.** No fields contain personally identifiable information. All data is at occupation-aggregate level (no individual workers identified).

## Sources Used
- Spec: `docs/specs/raw-ingest-bls-ooh.md`
- EDA report: `governance/eda/raw-bls-ooh-eda.md`
- DQ rules: `governance/dq-rules/raw-ingest-bls-ooh.json`
- Lineage: `governance/lineage/raw-ingest-bls-ooh-20260407T120000Z.json`
- Domain context: `governance/domain-context.md` (BLS OOH section)
