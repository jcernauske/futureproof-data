# Doc Generator Audit Trail: raw-ingest-karpathy-ai-exposure

**Date:** 2026-04-09
**Agent:** @doc-generator
**Spec:** docs/specs/raw-ingest-karpathy-ai-exposure.md
**Table:** raw.karpathy_ai_exposure (Bronze zone, 342 rows, 13 fields)

## Actions Taken

### 1. Data Dictionary Update

Added `raw.karpathy_ai_exposure` table entry to `governance/data-dictionary.json` with all 13 fields:

| Field | Type | CDE | Business Term |
|-------|------|-----|---------------|
| slug | string | Yes | -- |
| occupation_title | string | Yes | -- |
| category | string | No | -- |
| soc_code | string | Yes | -- |
| exposure_score | int | Yes | BT-080 |
| rationale | string | Yes | BT-081 |
| median_pay_annual | double | No | -- |
| num_jobs_2024 | long | No | -- |
| entry_education | string | No | -- |
| source_url | string | No | -- |
| ingested_at | timestamp | No | -- |
| source_method | string | No | -- |
| load_date | date | No | -- |

- CDE flags sourced from `governance/data-contracts/raw-karpathy-ai-exposure.yaml` (CDE tagger output)
- DQ rule cross-references sourced from `governance/dq-rules/raw-ingest-karpathy-ai-exposure.json`
- Lineage references point to `governance/lineage/raw-ingest-karpathy-ai-exposure-20260409T142500Z.json`
- All definitions written in plain English following the "explain it to a business analyst" standard

### 2. Business Glossary Update

Added two new terms to `governance/business-glossary.json`:

- **BT-080 (AI Exposure Score):** Defines the 0-10 LLM-generated reshaping estimate, including methodology source (Gemini Flash), caveats (not empirical, self-referential bias), and the key distinction that high scores predict reshaping, not job elimination.
- **BT-081 (AI Exposure Rationale):** Defines the 2-3 sentence LLM-generated explanation, its role as a display field in the FutureProof frontend, and its provenance from the Karpathy scoring pipeline.

Both terms set to `approval_status: "proposed"` pending @data-steward review.

### 3. Data Contract

No new data contract generated for the Bronze table. The CDE tagger already produced the authoritative contract at `governance/data-contracts/raw-karpathy-ai-exposure.yaml` with full column-level CDE/PII tagging. Bronze tables do not receive Brightsmith-format machine-verifiable contracts (those are generated for Gold/consumable tables). The Gold consumable contract for `consumable.ai_exposure` will be generated when that table is built.

## Decisions and Judgment Calls

1. **CDE flags carried verbatim from CDE tagger.** The CDE tagger flagged 5 columns as CDE (slug, occupation_title, soc_code, exposure_score, rationale). I adopted these designations without modification -- the rationales are well-documented in the CDE tagger output and align with the spec's critical data flow.

2. **Cross-validation fields (median_pay_annual, num_jobs_2024, entry_education) not flagged as CDE.** These fields are carried for validation and dedup tiebreaking only. The authoritative sources for wage, employment, and education data are the BLS OOH tables. The definitions explicitly state "cross-validation only" to prevent confusion about which source is authoritative.

3. **SOC code nullable designation.** soc_code is marked nullable: true because ~52 of 342 rows lack SOC codes in the source data. This is expected and documented -- Silver zone resolves nulls via title matching. The definition explains this to business users.

4. **DQ rule cross-references are partial.** Only rules that directly validate a specific field are cross-referenced in that field's `dq_rules` array. Table-level rules (row count, cross-validation) are documented in the DQ rules file but not linked to individual columns.

5. **Business terms BT-080 and BT-081 mapped to exposure_score and rationale columns.** The spec explicitly defined these term IDs and their definitions. The glossary entries expand on the spec's definitions with additional context about methodology limitations and frontend usage.

## Artifacts Produced

| Artifact | Path |
|----------|------|
| Data dictionary entry | `governance/data-dictionary.json` (raw.karpathy_ai_exposure section) |
| Business glossary terms | `governance/business-glossary.json` (BT-080, BT-081) |
| Audit trail | `governance/audit-trail/2026-04-09-doc-generator-raw-ingest-karpathy-ai-exposure.md` |

## Not Produced (Out of Scope for Bronze)

- Data contract in Brightsmith format (Gold zone only)
- Grounding document (MCP zone only)
- Silver or Gold data dictionary entries (separate doc-generator runs for those specs)
