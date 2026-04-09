# Audit Trail: @doc-generator — silver-base-bls-ooh

**Date:** 2026-04-07
**Agent:** @doc-generator
**Spec:** docs/specs/silver-base-bls-ooh.md
**Table:** base.bls_ooh

## Actions Taken

### 1. Data Dictionary — Added base.bls_ooh (25 columns)

**File:** `governance/data-dictionary.json`

Added a complete table entry for `base.bls_ooh` with all 25 columns. Each column includes:
- Plain-English definition suitable for business analysts
- CDE flag and rationale (where applicable)
- PII flag (all false — aggregated occupation-level data)
- Source column lineage
- Business term cross-reference
- DQ rule cross-references
- Lineage file reference

**CDE columns documented (5):** soc_code, employment_current, employment_projected, employment_change_pct, median_annual_wage — consistent with data contract and physical model.

**Columns with no business term (3):** education_typical, work_experience, training_typical — these are original BLS text labels. Their normalized/coded counterparts have terms. Noted in each entry.

### 2. Data Contract — Updated base-bls-ooh.yaml

**File:** `governance/data-contracts/base-bls-ooh.yaml`

Updates to the existing contract produced by @cde-tagger:
- Added `data_dictionary` reference
- Added `lineage_file` reference under lineage section
- Added `consumers` section documenting 3 planned downstream consumers:
  1. Gold career outcomes (via CIP-SOC crosswalk)
  2. O*NET Silver join (direct SOC join)
  3. MCP grounding documents
- Updated header to note @doc-generator involvement

No schema or quality threshold changes were needed — the existing contract from @cde-tagger is consistent with the physical model, DQ rules, and DQ scorecard.

## Consistency Verification

Cross-checked the following artifacts for consistency:

| Artifact | Status | Notes |
|----------|--------|-------|
| Physical model (25 columns) | Consistent | All column names, types, and nullability match |
| Data contract (25 columns) | Consistent | All columns, types, CDE flags match |
| Business glossary (BT-015 through BT-045) | Consistent | All referenced terms exist in glossary |
| DQ rules (36 rules) | Consistent | Rule IDs cross-referenced in dictionary |
| DQ scorecard (36/36 passing) | Consistent | 100% pass rate confirmed |
| Lineage file | Consistent | Referenced in all dictionary entries |

## Judgment Calls

1. **Catchall flag count:** The spec originally estimated ~46 catchall occupations, but the DQ rules (SLV-OOH-011) and scorecard confirm 70. The data dictionary uses the actual count of 70, consistent with DQ rule findings and EDA.

2. **Education code ordering:** The raw zone dictionary documents education_code with ascending order (1=No formal through 8=Doctoral), but the Silver spec and physical model use descending order (1=Doctoral through 8=No formal). The data dictionary follows the Silver/physical model ordering (1=Doctoral) since that is what the actual table contains. This is a known difference between raw and Silver encoding — noted but not a bug.

3. **Business terms for text label fields:** education_typical, work_experience, and training_typical have no business terms. This is consistent with the physical model (which also shows no BT for these) and is an open issue (non-blocking) carried from the logical model. The coded/normalized counterparts are the governed fields.
