# Doc Generator Audit Trail: gold-futureproof-engine

**Date:** 2026-04-09
**Agent:** @doc-generator
**Spec:** docs/specs/gold-futureproof-engine.md

## Actions Taken

### Data Contracts

1. **Generated contracts from live Iceberg tables** using `brightsmith.infra.contract generate`:
   - `governance/data-contracts/program-career-paths.yaml` -- 40 columns, schema matches live table
   - `governance/data-contracts/career-branches.yaml` -- 24 columns, schema matches live table

2. **Enriched generated contracts with CDE tagger metadata** from `consumable-program-career-paths.yaml` and `consumable-career-branches.yaml`:
   - Merged business terms, CDE flags, CDE rationales, descriptions, and constraints
   - Added lineage source references
   - Set quality thresholds (min_row_count: 150,000 for program_career_paths; 15,000 for career_branches)

3. **Verified both contracts against live tables**:
   - `program-career-paths v1.0.0`: VALID (40/40 columns, 0 grain duplicates, 626,406 rows, all required columns non-null)
   - `career-branches v1.0.0`: VALID (24/24 columns, 0 grain duplicates, 15,944 rows, all required columns non-null)

### README.md Updates

1. **Updated Data Sources** -- changed BLS OOH and O*NET from "(planned)" to active; added CIP-SOC Crosswalk
2. **Added FutureProof Engine data models** -- conceptual, logical, and physical Mermaid diagrams for consumable.program_career_paths and consumable.career_branches
3. **Added BLS OOH physical model** -- Mermaid diagram for consumable.occupation_profiles
4. **Added CIP-SOC Crosswalk physical model** -- Mermaid diagram for base.cip_soc_crosswalk
5. **Added 8 new tables** to the Tables section: raw.bls_ooh, base.bls_ooh, consumable.occupation_profiles, raw.cip_soc_crosswalk, base.cip_soc_crosswalk, consumable.program_career_paths, consumable.career_branches
6. **Updated glossary term count** from 72 to 93
7. **Added 21 new business glossary terms** in README: BT-073 through BT-093 (CIP-SOC Crosswalk terms and FutureProof Engine terms)
8. **Added 7 new Key Design Decisions** (#21-#27) covering CIP prefix matching, ERN weighting, ROI breakpoints, RES placeholder, Gold-time match_quality derivation, dedup strategy, and Ceiling boss formula

### Decisions and Judgment Calls

1. **Two contract formats coexist.** The CDE tagger produced contracts in a non-Brightsmith format (`consumable-*.yaml`). The contract generator produces contracts in the standard `apiVersion: brightsmith/v1` format. I kept both -- the CDE tagger's contracts serve as the authoritative governance documentation with rich CDE/PII metadata, while the generated contracts serve as the machine-verifiable schema contracts that the `contract verify` tool validates. The enrichment script merges CDE metadata into the generated format.

2. **Freshness check skipped.** Both contracts report `freshness: SKIP` because the tables use `promoted_at` rather than `ingested_at`. This is expected for Gold zone tables that use the promote pattern.

3. **Row count for program_career_paths (626,406)** exceeds the spec's estimated range of 150,000-500,000. The contract min_row_count is set to 150,000 (lower bound of the spec estimate). The actual count is valid -- the CIP prefix fan-out produced more combinations than estimated, and the DQ rules for this table accept the actual count.
