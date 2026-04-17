# Spec: gold-career-outcomes-college-scorecard

**Status:** COMPLETE
**Zone:** Gold
**Primary Agent:** @primary-agent
**Created:** 2026-04-06

## Problem Statement
Build the consumable career outcomes table from the Silver `base.college_scorecard` data. This is the core data product powering FutureProof's query pattern: **school + major → earnings percentiles, debt, debt-to-earnings, employment rate.** The effort slider in the product UI depends on 25th/50th/75th percentile earnings bands — these are derived from the cross-institution distribution of program medians within each CIP family, giving users a realistic range of outcomes for their field of study.

## Source Data Constraint: Percentile Bands

The College Scorecard field-of-study file provides **median earnings only** — no individual-level 25th/75th percentile columns exist at this grain. The percentile bands in this spec are computed as window-function aggregates: for each CIP family, the 25th and 75th percentiles of the program-level medians across all institutions. This answers the effort slider question well: "If I study Computer Science, the bottom-quartile program outcome is $X and the top-quartile is $Y."

These are **cross-institution percentile bands**, not within-cohort percentiles. The spec documents this clearly so the MCP layer and UI can present them with appropriate context.

## Success Criteria
- [ ] `consumable.career_outcomes` Iceberg table exists with all schema fields populated
- [ ] Grain: unitid x cipcode x credlev (same as Silver base)
- [ ] Earnings percentile bands (p25/p50/p75) computed per CIP family via window functions
- [ ] Debt-to-earnings ratio computed for all rows with both debt and earnings data
- [ ] Earnings growth rate computed for rows with both 1yr and 2yr earnings
- [ ] Programs with insufficient data excluded (small_cohort_flag = True AND no earnings data)
- [ ] Confidence tier assigned to every row
- [ ] Idempotent promote pattern used
- [ ] Deterministic `record_id` via `compute_grain_id()`
- [ ] DQ rules written, executed, and passing (no P0 failures)
- [ ] Golden dataset with at least 3 independently verifiable values
- [ ] Data contract produced for `consumable.career_outcomes`

## Source Data
- **Source Table:** `base.college_scorecard` (Silver zone)
- **Row Count:** 69,947 rows in Silver base
- **Output Row Count:** ~69,947 (all rows carried forward; exclusion flags applied, not row drops)
- **Grain:** unitid x cipcode x credlev

## Technical Design

### Iceberg Table: consumable.career_outcomes
- **Grain:** One row per institution (unitid) x program (cipcode) x credential level (credlev)
- **Dedup grain fields:** [unitid, cipcode, credlev]
- **Promote pattern:** Use `brightsmith.infra.promote.promote()` for idempotent writes
- **Record ID:** `compute_grain_id(row, ['unitid', 'cipcode', 'credlev'], prefix='co')`

### Schema

#### Identity Fields (carried from Silver)
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| record_id | string | derived | yes | Deterministic grain hash (prefix: `co`) |
| unitid | long | base.college_scorecard | yes | IPEDS institution ID |
| institution_name | string | base.college_scorecard | yes | Official institution name |
| institution_control | string | base.college_scorecard | no | Public / Private nonprofit / Private for-profit |
| cipcode | string | base.college_scorecard | yes | Normalized CIP code (XX.XX) |
| program_name | string | base.college_scorecard | yes | Human-readable program description |
| cip_family | string | base.college_scorecard | yes | 2-digit CIP family code |
| cip_family_name | string | base.college_scorecard | yes | CIP family description |
| credential_level | int | base.college_scorecard | yes | Credential level (3=Bachelor's) |

#### Core Outcome Fields (carried from Silver)
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| earnings_1yr_median | double | base.college_scorecard | no | Median earnings, 1yr post-completion |
| earnings_2yr_median | double | base.college_scorecard | no | Median earnings, 2yr post-completion |
| debt_median | double | base.college_scorecard | no | Median debt at graduation |
| completions_count | long | base.college_scorecard | no | IPEDS completions (first major = completions_count_1) |
| small_cohort_flag | boolean | base.college_scorecard | yes | True if completions < 30 |

#### Derived: Percentile Bands (CIP-family window aggregates)
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| earnings_1yr_p25 | double | PERCENTILE_CONT(0.25) OVER (PARTITION BY cip_family) on earnings_1yr_median | no | 25th percentile of 1yr medians across institutions in same CIP family |
| earnings_1yr_p75 | double | PERCENTILE_CONT(0.75) OVER (PARTITION BY cip_family) on earnings_1yr_median | no | 75th percentile |
| earnings_2yr_p25 | double | PERCENTILE_CONT(0.25) OVER (PARTITION BY cip_family) on earnings_2yr_median | no | 25th percentile of 2yr medians |
| earnings_2yr_p75 | double | PERCENTILE_CONT(0.75) OVER (PARTITION BY cip_family) on earnings_2yr_median | no | 75th percentile |
| debt_p25 | double | PERCENTILE_CONT(0.25) OVER (PARTITION BY cip_family) on debt_median | no | 25th percentile of debt across CIP family |
| debt_p75 | double | PERCENTILE_CONT(0.75) OVER (PARTITION BY cip_family) on debt_median | no | 75th percentile |

#### Derived: Financial Ratios
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| debt_to_earnings_annual | double | debt_median / earnings_1yr_median | no | Key affordability metric. < 1.0 manageable, > 2.0 concerning. Null if either input null. |
| debt_to_earnings_tier | string | Bucketed debt_to_earnings_annual | no | "Low" (< 0.75), "Moderate" (0.75–1.5), "High" (1.5–2.5), "Very High" (> 2.5). Null if ratio null. |
| earnings_growth_rate | double | (earnings_2yr - earnings_1yr) / earnings_1yr | no | Early career trajectory. Null if either input null. Negative values valid (cohort differences, not individual regression). |

#### Derived: Relative Position
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| cip_family_earnings_rank | double | PERCENT_RANK() OVER (PARTITION BY cip_family ORDER BY earnings_1yr_median) | no | 0.0–1.0, where 1.0 = highest earner in CIP family. Null if earnings null. |
| program_value_index | double | earnings_1yr_median / debt_median | no | ROI proxy — higher = better value. Null if either input null. |

#### Derived: Data Quality Context
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| confidence_tier | string | See derivation rules below | yes | "high", "medium", "low", "insufficient" |
| has_earnings | boolean | earnings_1yr_median IS NOT NULL OR earnings_2yr_median IS NOT NULL | yes | Convenience flag for filtering |
| has_debt | boolean | debt_median IS NOT NULL | yes | Convenience flag for filtering |
| outcome_completeness | double | count of non-null outcome fields / 3 | yes | 0.0, 0.33, 0.67, or 1.0 (3 core outcome fields: 1yr, 2yr, debt) |

#### Metadata
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| source_load_date | date | base.college_scorecard | yes | Date of source data load |
| promoted_at | timestamp | generated | yes | Gold zone promotion timestamp |

### Confidence Tier Derivation

| Tier | Criteria |
|------|----------|
| high | small_cohort_flag = False AND has_earnings = True AND has_debt = True |
| medium | small_cohort_flag = False AND (has_earnings = True OR has_debt = True) |
| low | small_cohort_flag = True AND (has_earnings = True OR has_debt = True) |
| insufficient | has_earnings = False AND has_debt = False |

### Debt-to-Earnings Tier Thresholds

Based on Department of Education guidance (Gainful Employment rule) and industry convention:

| Tier | Range | Interpretation |
|------|-------|----------------|
| Low | debt_to_earnings_annual < 0.75 | Debt is very manageable relative to earnings |
| Moderate | 0.75 ≤ ratio < 1.5 | Typical range for most bachelor's programs |
| High | 1.5 ≤ ratio < 2.5 | May require extended repayment or income-driven plan |
| Very High | ratio ≥ 2.5 | Debt significantly exceeds first-year earnings |

### Transformations

1. **Read Silver base table** via DuckDB (same pattern as Silver transformer)
2. **Compute CIP-family percentile bands** via window functions over the non-null earnings/debt values within each CIP family
3. **Compute debt-to-earnings ratio** (null-safe: null if either input is null)
4. **Compute debt-to-earnings tier** from ratio
5. **Compute earnings growth rate** (null-safe)
6. **Compute CIP-family earnings rank** via PERCENT_RANK window function
7. **Compute program value index** (earnings / debt)
8. **Compute confidence tier** from small_cohort_flag + data availability
9. **Compute convenience flags** (has_earnings, has_debt, outcome_completeness)
10. **Compute record_id** via `compute_grain_id()`
11. **Promote** to `consumable.career_outcomes` via idempotent promote pattern

### Transformer
- **Module:** `src/gold/college_scorecard_career_outcomes.py`
- **Function:** `transform()`
- **Registration:** `domain/manifest.yaml` under `pipeline.zones.gold`
- **Pattern:** Read from `base.college_scorecard`, transform, promote to `consumable.career_outcomes`

### Percentile Band Implementation Notes

The percentile bands are computed using DuckDB window functions on the in-memory DataFrame after reading from Silver. Only rows with non-null values for the respective field contribute to the percentile calculation. This means:
- A CIP family with 5 non-null earnings values will have percentile bands based on 5 data points
- CIP families with < 3 non-null values should have their percentile bands set to null (insufficient sample)
- The p50 (median) of the CIP family distribution is NOT the same as any individual program's `earnings_1yr_median` — it's the median of medians across institutions

Minimum sample size for percentile bands: **3 non-null values per CIP family per field.** Below this threshold, set all three bands (p25/p50/p75) to null for that family-field combination.

### Dropped Fields (from Silver, with justification)
| Field | Reason |
|-------|--------|
| completions_count_2 | Second-major completions not relevant to career outcomes query pattern. Retained completions_count_1 as `completions_count`. |
| credential_description | Redundant with credential_level (always "Bachelor's Degree" in MVP) |
| ingested_at | Silver metadata — replaced by promoted_at in Gold |

## Agent Workflow (Greenfield)
1. @governance-reviewer — Pre-implementation review
2. @data-steward — Identify business terms from spec (Gold-specific terms)
3. @semantic-modeler — Propose conceptual model → HUMAN APPROVAL GATE
4. @semantic-modeler — Propose logical model → HUMAN APPROVAL GATE
5. @semantic-modeler — Generate physical model from approved logical
6. @data-analyst — EDA on Silver base data (profile for Gold thresholds, validate percentile band distributions)
7. @dq-rule-writer — Write Gold DQ rules from EDA + logical model
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
| @entity-resolver | SKIP | Single-source data, no cross-source entity matching needed yet (no BLS/O*NET integration in this spec) |
| @pii-scanner | SKIP | governance/domain-context.md PII section: "No personal data expected" — all data is aggregated program-level statistics, no individual student records |
| @temporal-modeler | SKIP | Single-snapshot data (most recent cohort), no temporal versioning required. Full table replace strategy per user-confirmed decisions. |
| @adversarial-auditor | SKIP | First Gold spec in pipeline; will audit holistically when cross-source integration specs land |

## DQ Rules
To be written by @dq-rule-writer based on @data-analyst EDA findings.

Expected areas of focus:
- Grain uniqueness (unitid x cipcode x credlev = zero duplicates)
- Row count consistency with Silver source (69,947 expected, allow +/- 15%)
- Debt-to-earnings ratio range (0.01–10.0; values outside this are likely data quality issues)
- Debt-to-earnings tier distribution (expect "Moderate" to be plurality)
- Earnings growth rate range (-0.5 to 2.0; more extreme values warrant investigation)
- Confidence tier distribution (expect "insufficient" ≈ 50-55%, based on Silver EDA suppression rates)
- Percentile band ordering (p25 ≤ p50 ≤ p75 for every CIP family — hard constraint)
- Percentile band null pattern (null if CIP family has < 3 non-null values for that field)
- cip_family_earnings_rank range (0.0–1.0, no nulls where earnings_1yr_median is non-null)
- has_earnings / has_debt flag accuracy (must match underlying field nullity exactly)
- outcome_completeness value set (exactly {0.0, 0.33, 0.67, 1.0})
- Derived field null propagation (debt_to_earnings_annual is null when either input is null)

## Golden Dataset

At least 3 independently verifiable values, selected from programs with high confidence data:
- A well-known CS program (high earnings, known debt range)
- A well-known nursing program (moderate earnings, known debt)
- A well-known business program (verify debt-to-earnings ratio math)

Each golden value must be traceable: source Silver row → Gold derivation → expected output.

## Governance Artifacts
- [ ] Business glossary: `governance/business-glossary.json` (Gold-specific terms: debt-to-earnings ratio, confidence tier, earnings percentile band, etc.)
- [ ] Conceptual model: `governance/models/gold-career-outcomes-college-scorecard-conceptual.md`
- [ ] Logical model: `governance/models/gold-career-outcomes-college-scorecard-logical.md`
- [ ] Physical model: `governance/models/gold-career-outcomes-college-scorecard-physical.md`
- [ ] EDA report: `governance/eda/gold-career-outcomes-eda.md`
- [ ] DQ rules: `governance/dq-rules/gold-career-outcomes-college-scorecard.json`
- [ ] DQ scorecard: `governance/dq-scorecards/gold-career-outcomes-college-scorecard-scorecard.md`
- [ ] Chaos manifest: `governance/chaos-manifests/gold-career-outcomes-college-scorecard-chaos.md`
- [ ] Golden dataset: `governance/golden-datasets/gold-career-outcomes-college-scorecard-golden.json`
- [ ] Lineage: `governance/lineage/gold-career-outcomes-college-scorecard-{timestamp}.json`
- [ ] Data contract: `governance/data-contracts/consumable-career-outcomes.yaml`
- [ ] Staff review: `governance/reviews/gold-career-outcomes-college-scorecard-staff-review.md`

## User-Confirmed Decisions
1. Earnings percentile bands (25th/50th/75th) are critical — they power the effort slider
2. Percentile bands are cross-institution distributions within CIP family (source data only has medians)
3. Include debt-to-earnings ratio as primary affordability metric
4. Gold table name: `consumable.career_outcomes`
5. All programs carried forward (flagged, not excluded) — filtering happens at query time

## Future Integration Notes
This Gold table is the first consumable data product. When BLS and O*NET data sources are integrated:
- **CIP-to-SOC crosswalk** will join career outcomes to occupation descriptions and AI exposure scores
- **Individual-level percentiles** may become available via SOC-level earnings distributions from BLS OES data
- The effort slider will be enhanced with occupation-specific projections (BLS growth rates) and AI automation risk (O*NET task analysis)
- A second Gold spec (`gold-career-projections`) will likely combine this table with BLS/O*NET data via the crosswalk
