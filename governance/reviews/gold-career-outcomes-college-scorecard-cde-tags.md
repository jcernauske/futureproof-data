## CDE/PII Tagging Report: gold-career-outcomes-college-scorecard
**Date:** 2026-04-06
**Agent:** @cde-tagger
**Table:** consumable.career_outcomes
**Zone:** Gold (Consumable)
**Physical Model:** governance/models/gold-career-outcomes-college-scorecard-physical.md
**Data Contract:** governance/data-contracts/consumable-career-outcomes.yaml

### Domain Context Referenced

- **governance/domain-context.md** -- Higher Education Outcomes domain. Data is aggregated program-level statistics from the U.S. Department of Education College Scorecard (Field of Study file). All earnings and debt figures are cohort-level medians, not individual records.
- **Regulatory alignment:** Department of Education Gainful Employment rule methodology informs the debt-to-earnings ratio as a key affordability metric. FERPA governs privacy suppression at the source. No BCBS 239 or financial regulatory reporting applies directly, but CDE identification follows BCBS 239 principles (columns critical to downstream business processes and management decisions).
- **PII assessment:** governance/domain-context.md PII section confirms "This dataset contains NO PII. All values are institutional identifiers, program codes, and aggregate statistical measures." Privacy is protected at the source by Department of Education suppression rules (FERPA).
- **Business criticality:** This is the core consumable data product powering FutureProof's query pattern (school + major = earnings percentiles, debt, debt-to-earnings, employment rate). The effort slider UI depends on percentile bands. The MCP layer serves these columns directly to AI consumers.

### CDE Identification Methodology

CDEs were identified based on three criteria applied to this specific Gold consumable table:
1. **Direct consumer exposure** -- columns served directly to the MCP layer and product UI
2. **Downstream derivation dependency** -- columns whose errors propagate to multiple derived metrics
3. **Business decision criticality** -- columns that students and families use to make enrollment decisions

### Columns Flagged as CDE

| Column | Table | Rationale |
|--------|-------|-----------|
| unitid | consumable.career_outcomes | Natural key component identifying the institution. Required for all downstream joins, MCP layer queries, and institution-level aggregations. Incorrect values orphan rows from institutional context. |
| earnings_1yr_median | consumable.career_outcomes | Primary business metric powering the effort slider UI. Feeds 5 downstream derived columns (debt-to-earnings ratio, earnings rank, program value index, 1yr percentile bands). Errors propagate to all consumer-facing affordability metrics. |
| earnings_2yr_median | consumable.career_outcomes | Primary business metric for multi-horizon career guidance. Feeds earnings growth rate and 2yr percentile bands. Enables cross-cohort trajectory analysis. |
| debt_median | consumable.career_outcomes | Primary affordability metric. Feeds debt-to-earnings ratio (Gainful Employment alignment), debt-to-earnings tier, program value index, and debt percentile bands. Errors corrupt 4 downstream derived columns. |
| earnings_1yr_p25 | consumable.career_outcomes | Powers the lower bound of the effort slider UI for 1yr earnings. Directly consumed by MCP layer and product UI. |
| earnings_1yr_p75 | consumable.career_outcomes | Powers the upper bound of the effort slider UI for 1yr earnings. Directly consumed by MCP layer and product UI. |
| earnings_2yr_p25 | consumable.career_outcomes | Lower bound of 2yr earnings range within CIP family. Consumed by MCP layer for multi-horizon guidance. |
| earnings_2yr_p75 | consumable.career_outcomes | Upper bound of 2yr earnings range within CIP family. Consumed by MCP layer for multi-horizon guidance. |
| debt_p25 | consumable.career_outcomes | Lower bound of debt range within CIP family. Essential for affordability context in MCP layer. |
| debt_p75 | consumable.career_outcomes | Upper bound of debt range within CIP family. Essential for affordability context in MCP layer. |
| debt_to_earnings_annual | consumable.career_outcomes | Key affordability metric aligned with Gainful Employment rule methodology. Primary measure students and policymakers use to evaluate program debt burden. Directly consumed by MCP layer and product UI. |

**Total CDE columns: 11** (4 carried from Silver + 6 percentile bands + 1 financial ratio)

### Columns Flagged as PII

| Column | Table | Rationale |
|--------|-------|-----------|

**Total PII columns: 0**

Per governance/domain-context.md: "This dataset contains NO PII. All values are institutional identifiers, program codes, and aggregate statistical measures." All earnings and debt figures are cohort-level medians (not individual financial records). Institution names are public IPEDS data, not personal names. Privacy is protected at the source by FERPA suppression.

### Columns Evaluated -- Not Flagged

| Column | Table | Reason Not Critical/Sensitive |
|--------|-------|-------------------------------|
| record_id | consumable.career_outcomes | Technical surrogate key. Derived deterministically from natural key. Not consumed by business users or product UI. |
| institution_name | consumable.career_outcomes | Display label only. unitid is the authoritative identifier. Errors are cosmetic, not analytical. |
| institution_control | consumable.career_outcomes | Segmentation dimension, not a core outcome metric. Used for filtering/grouping but not for primary decision-making calculations. |
| cipcode | consumable.career_outcomes | Natural key component but serves as a join key to external taxonomies, not as an outcome metric. Classification errors are important but addressed by DQ rules on format validation, not CDE flagging. |
| program_name | consumable.career_outcomes | Display label only. cipcode is the authoritative identifier. Errors are cosmetic. |
| cip_family | consumable.career_outcomes | Partition key for percentile band computation. Important for derivation correctness but its integrity is enforced by DQ rules (must match cipcode prefix). Not directly consumed as an outcome metric. |
| cip_family_name | consumable.career_outcomes | Display label for CIP family. Cosmetic only. |
| credential_level | consumable.career_outcomes | Natural key component. MVP has only one value (3 = Bachelor's). Integrity enforced by DQ range check. Not an outcome metric. |
| completions_count | consumable.career_outcomes | Program size indicator. Drives small_cohort_flag but not directly consumed as an outcome metric by the product UI. |
| small_cohort_flag | consumable.career_outcomes | Data quality flag. Feeds confidence tier derivation but is an intermediate indicator, not a consumer-facing metric. |
| debt_to_earnings_tier | consumable.career_outcomes | Derived categorical label from debt_to_earnings_annual. The ratio itself (flagged as CDE) is the authoritative metric; the tier is a convenience bucketing. |
| earnings_growth_rate | consumable.career_outcomes | Supplementary metric. Cross-cohort differential (not true longitudinal growth). Informative but not central to the effort slider or primary affordability assessment. |
| cip_family_earnings_rank | consumable.career_outcomes | Relative positioning metric. Useful for context but not the primary decision-driving metric (percentile bands serve that role). |
| program_value_index | consumable.career_outcomes | ROI proxy (mathematical inverse of debt-to-earnings). Supplementary to the primary debt-to-earnings ratio which is already flagged as CDE. |
| confidence_tier | consumable.career_outcomes | Data quality classification. Important for interpretation but not an outcome metric itself. |
| has_earnings | consumable.career_outcomes | Convenience boolean flag. Derived from earnings nullity. Not an outcome metric. |
| has_debt | consumable.career_outcomes | Convenience boolean flag. Derived from debt nullity. Not an outcome metric. |
| outcome_completeness | consumable.career_outcomes | Data quality proportion. Informative but not an outcome metric. |
| source_load_date | consumable.career_outcomes | Pipeline metadata. Not an analytical or business metric. |
| promoted_at | consumable.career_outcomes | Pipeline metadata. Not an analytical or business metric. |

### No Backward Propagation Note

CDE flags on this Gold consumable table are independent of Silver base table flags. The Silver contract (base-college-scorecard.yaml) has its own CDE flags (unitid, earnings_1yr_median, earnings_2yr_median, debt_median). The Gold table adds 7 new CDEs (6 percentile bands + debt_to_earnings_annual) that do not propagate backward to Silver. Lineage, not CDE flags, traces data origin across layers.

### Alignment with Physical Model

The physical model at governance/models/gold-career-outcomes-college-scorecard-physical.md identifies 11 CDE columns in its Column Summary section: "4 CDE columns carried from Silver (unitid, earnings_1yr_median, earnings_2yr_median, debt_median)" + "6 CDE columns new in Gold (earnings_1yr_p25, earnings_1yr_p75, earnings_2yr_p25, earnings_2yr_p75, debt_p25, debt_p75)" + "1 CDE column new in Gold (debt_to_earnings_annual)". This tagging report confirms all 11 with rationale.
