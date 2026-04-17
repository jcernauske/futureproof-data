# Spec: gold-occupation-profiles-bls-ooh

**Status:** COMPLETE
**Zone:** Gold
**Primary Agent:** @primary-agent
**Created:** 2026-04-07

## Problem Statement

Build the consumable occupation profile data product from the Silver `base.bls_ooh` table. This is the second Gold data product in FutureProof and the first occupation-level consumable — it answers: **"What does this career look like, and where is it headed?"**

The product shapes occupation data for direct consumption by the Gemma agent and the FutureProof frontend. It adds stat-ready scoring (GRW score on 1–10 scale, wage percentile rank within education tier), occupation-level confidence tiers, and pre-computed fields that map directly to the five-stat system and boss fight engine.

This Gold product is self-contained — it does not require the CIP→SOC crosswalk to be useful. Gemma can query it directly by SOC code or occupation title. The crosswalk connects it to College Scorecard later, but this table stands alone as an occupation reference.

## Success Criteria

- [ ] `consumable.occupation_profiles` Iceberg table exists with all schema fields populated
- [ ] Grain: soc_code (one row per occupation, 832 rows)
- [ ] GRW score computed on 1–10 scale from employment_change_pct
- [ ] Wage percentile rank computed within education tier and overall
- [ ] Occupation confidence tier assigned to every row
- [ ] FutureProof stat mappings documented (which fields back which stats/bosses)
- [ ] Idempotent promote pattern used
- [ ] Deterministic `record_id` via `compute_grain_id()`
- [ ] DQ rules written, executed, and passing (no P0 failures)
- [ ] Golden dataset with at least 3 independently verifiable values
- [ ] Data contract produced for `consumable.occupation_profiles`

## Source Data

- **Source Table:** `base.bls_ooh` (Silver zone)
- **Row Count:** 832 rows
- **Grain:** soc_code (one row per occupation)

## Technical Design

### Iceberg Table: consumable.occupation_profiles

- **Grain:** One row per occupation (soc_code)
- **Dedup grain fields:** [soc_code]
- **Promote pattern:** Use `brightsmith.infra.promote.promote()` for idempotent writes
- **Record ID:** `compute_grain_id(row, ['soc_code'], prefix='op')`

### Schema

#### Identity Fields (carried from Silver)
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| record_id | string | derived | yes | Deterministic grain hash (prefix: `op`) |
| soc_code | string | base.bls_ooh | yes | SOC occupation code (XX-XXXX). Primary join key. |
| occupation_title | string | base.bls_ooh | yes | Official BLS occupation name |
| soc_major_group | string | base.bls_ooh | yes | 2-digit SOC major group code |
| soc_major_group_name | string | base.bls_ooh | yes | Major group description |

#### Classification (carried from Silver)
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| broad_occupation_flag | boolean | base.bls_ooh | yes | True for 7 rolled-up/broad codes |
| catchall_flag | boolean | base.bls_ooh | yes | True for 70 "all other" categories |

#### Employment & Growth (carried + derived)
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| employment_current | long | base.bls_ooh | no | Current employment count |
| employment_projected | long | base.bls_ooh | no | Projected 2034 employment count |
| employment_change_pct | double | base.bls_ooh | no | Percent change 2024–2034 |
| openings_annual_avg | long | base.bls_ooh | no | Average annual job openings |
| growth_category | string | base.bls_ooh | yes | Bucketed growth (declining_fast through booming) |

#### Compensation (carried + derived)
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| median_annual_wage | double | base.bls_ooh | no | Median annual wage. Null for 23 occupations. |
| wage_available | boolean | base.bls_ooh | yes | True if wage data exists |

#### Education & Entry Requirements (carried)
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| education_code | int | base.bls_ooh | no | BLS education level code (1–8) |
| education_level_name | string | base.bls_ooh | no | Human-readable education level |
| work_experience_code | int | base.bls_ooh | no | BLS work experience code (1–3) |
| training_code | int | base.bls_ooh | no | BLS training code (1–6) |

#### Derived: GRW Score (FutureProof Stat)
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| grw_score | double | See derivation below | no | Growth stat on 1–10 scale. Backs the GRW pentagon stat. Null only if employment_change_pct is null (0 rows currently). |
| grw_score_rounded | int | ROUND(grw_score) | no | Integer 1–10 for display |

#### Derived: Wage Position
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| wage_percentile_overall | double | PERCENT_RANK() OVER (ORDER BY median_annual_wage) | no | 0.0–1.0 rank among all occupations with wage data. Null if wage unavailable. |
| wage_percentile_education_tier | double | PERCENT_RANK() OVER (PARTITION BY education_code ORDER BY median_annual_wage) | no | 0.0–1.0 rank within same education requirement tier. Shows how well this career pays relative to peers needing the same degree. Null if wage unavailable. |
| wage_tier | string | Bucketed wage_percentile_overall | no | See derivation below. Null if wage unavailable. |

#### Derived: Market Opportunity
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| market_score | double | See derivation below | no | Combined growth + openings signal on 1–10 scale. Backs the Market boss fight. |
| market_score_rounded | int | ROUND(market_score) | no | Integer 1–10 for display |

#### Derived: Data Quality Context
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| confidence_tier | string | See derivation below | yes | "high", "medium", "low" |
| data_completeness | double | count of non-null core fields / 4 | yes | 4 core fields: median_annual_wage, employment_current, employment_change_pct, openings_annual_avg. Values: 0.0, 0.25, 0.5, 0.75, 1.0. |

#### FutureProof Stat Mapping (documentation fields)
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| backs_stats | string | static | yes | Comma-separated list of FutureProof stats this occupation data feeds. Always "ERN,GRW" for this data product. |
| backs_bosses | string | static | yes | Comma-separated list of boss fights this data feeds. Always "Market,Ceiling" for this data product. |

#### Metadata
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| source_load_date | date | base.bls_ooh | yes | Date of original BLS data load |
| promoted_at | timestamp | generated | yes | Gold zone promotion timestamp |

### GRW Score Derivation (1–10 Scale)

Maps employment_change_pct to a 1–10 score using a piecewise linear scale anchored to BLS growth benchmarks:

| employment_change_pct | grw_score | Rationale |
|-----------------------|-----------|-----------|
| ≤ -20.0 | 1.0 | Severe decline |
| -20.0 to -10.0 | 1.0 → 2.5 | Fast decline — linear interpolation |
| -10.0 to -1.0 | 2.5 → 4.0 | Moderate decline |
| -1.0 to 1.0 | 4.0 → 5.0 | Stable (average is ~4% nationally, but 0% is "not growing") |
| 1.0 to 5.0 | 5.0 → 6.5 | Below-average to average growth |
| 5.0 to 10.0 | 6.5 → 7.5 | Above-average growth |
| 10.0 to 20.0 | 7.5 → 9.0 | Strong growth |
| ≥ 20.0 | 9.0 → 10.0 | Exceptional growth (capped at 10.0) |

For values ≥ 20.0: linear interpolation from 9.0 at 20.0 to 10.0 at 50.0, capped at 10.0.

Implementation: piecewise linear function. Input: employment_change_pct. Output: grw_score (double, 1.0–10.0). Null if input is null.

This places the national average growth (~4%) at approximately 6.0, which feels right — "average" should be slightly above the midpoint since growth is the positive outcome.

### Market Score Derivation (1–10 Scale)

Combines growth signal and opportunity volume into a single market health indicator:

```
market_score = 0.6 * grw_score + 0.4 * openings_score
```

Where `openings_score` is the PERCENT_RANK of `openings_annual_avg` mapped to 1–10:

```
openings_score = 1.0 + 9.0 * PERCENT_RANK() OVER (ORDER BY openings_annual_avg)
```

Rationale: Growth direction matters more (60% weight) but opportunity volume matters too — a field can be growing at 15% but only have 200 jobs nationwide, which is poor market opportunity. The openings signal corrects for this.

Null if grw_score is null or openings_annual_avg is null.

### Wage Tier Derivation

| Tier | Range | Interpretation |
|------|-------|----------------|
| low | wage_percentile_overall < 0.25 | Bottom quartile earners |
| below_average | 0.25 ≤ percentile < 0.50 | Below median |
| above_average | 0.50 ≤ percentile < 0.75 | Above median |
| high | 0.75 ≤ percentile < 0.90 | Strong earners |
| very_high | percentile ≥ 0.90 | Top 10% of occupations |

Null if wage_percentile_overall is null.

### Confidence Tier Derivation

| Tier | Criteria |
|------|----------|
| high | broad_occupation_flag = False AND catchall_flag = False AND wage_available = True |
| medium | (broad_occupation_flag = True OR catchall_flag = True) AND wage_available = True |
| low | wage_available = False (regardless of other flags) |

Rationale: Broad and catchall occupations have real data but represent heterogeneous groups — guidance will be less specific. Null-wage occupations have the weakest data for FutureProof's purposes (can't compute ERN stat).

### Dropped Fields (from Silver, with justification)

| Field | Reason |
|-------|--------|
| employment_change | Redundant with employment_change_pct for Gold consumers. Absolute change is less useful than percentage for stat scoring. Available in Silver if needed. |
| median_wage_capped | All False in current data. The wage_available flag is more useful. Preserved in Silver for lineage. |
| education_typical | Redundant with education_level_name (derived from code). Kept the normalized name, dropped the raw label. |
| work_experience | Redundant with work_experience_code. Code is sufficient for Gold consumers. |
| training_typical | Redundant with training_code. Code is sufficient for Gold consumers. |
| ingested_at | Silver metadata — replaced by promoted_at in Gold. |

### Transformations

1. **Read Silver base table** `base.bls_ooh` via DuckDB
2. **Compute grw_score** — piecewise linear function from employment_change_pct
3. **Compute grw_score_rounded** — ROUND(grw_score)
4. **Compute wage_percentile_overall** — PERCENT_RANK window on median_annual_wage (null-safe: exclude nulls from ranking)
5. **Compute wage_percentile_education_tier** — PERCENT_RANK window partitioned by education_code (null-safe)
6. **Compute wage_tier** — bucket wage_percentile_overall
7. **Compute openings_score** — PERCENT_RANK on openings_annual_avg mapped to 1–10
8. **Compute market_score** — 0.6 * grw_score + 0.4 * openings_score
9. **Compute market_score_rounded** — ROUND(market_score)
10. **Compute confidence_tier** — from broad/catchall flags + wage_available
11. **Compute data_completeness** — non-null core fields / 4
12. **Set backs_stats** — "ERN,GRW" for all rows
13. **Set backs_bosses** — "Market,Ceiling" for all rows
14. **Compute record_id** — `compute_grain_id(row, ['soc_code'], prefix='op')`
15. **Promote** to `consumable.occupation_profiles` via idempotent promote pattern

### Transformer

- **Module:** `src/gold/bls_ooh_occupation_profiles.py`
- **Function:** `transform()`
- **Registration:** `domain/manifest.yaml` under `pipeline.zones.gold`
- **Pattern:** Read from `base.bls_ooh`, transform, promote to `consumable.occupation_profiles`

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @data-steward — Identify business terms from spec (Gold-specific terms)
3. @semantic-modeler — Propose conceptual model → HUMAN APPROVAL GATE
4. @semantic-modeler — Propose logical model → HUMAN APPROVAL GATE
5. @semantic-modeler — Generate physical model from approved logical
6. @data-analyst — EDA on Silver base data (validate score distributions, percentile bands)
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
| @entity-resolver | SKIP | Single-source Gold product. Cross-source resolution happens in crosswalk spec. |
| @pii-scanner | SKIP | Aggregated occupation-level statistics. No individual data. |
| @temporal-modeler | SKIP | Single-snapshot projection cycle. Full table replace on refresh. |
| @adversarial-auditor | RUN | First occupation-level Gold product. Score derivations (GRW, market) need adversarial testing — these are the formulas that directly produce FutureProof stat values. |

## DQ Rules

To be written by @dq-rule-writer based on @data-analyst EDA findings.

Expected areas of focus:

**Grain & Row Count**
- Grain uniqueness: soc_code = zero duplicates (832 expected)
- Row count: exactly 832 (no rows added or dropped from Silver)

**Score Ranges**
- grw_score: 1.0–10.0 for all non-null rows
- grw_score_rounded: 1–10 integer for all non-null rows
- market_score: 1.0–10.0 for all non-null rows
- market_score_rounded: 1–10 integer for all non-null rows
- grw_score_rounded = ROUND(grw_score) for all rows (exact match)
- market_score_rounded = ROUND(market_score) for all rows

**Score Distribution**
- grw_score mean should be approximately 5.5–6.5 (given national average growth ≈ 4%)
- grw_score should have representation across at least 8 of 10 integer buckets (1–10)
- market_score distribution should not cluster excessively (std dev > 1.0)

**Percentile Ranks**
- wage_percentile_overall: 0.0–1.0 when non-null, null count = 23
- wage_percentile_education_tier: 0.0–1.0 when non-null, null count = 23
- wage_tier: one of 5 valid values when non-null, null count = 23

**Confidence Tier**
- confidence_tier: every row has a value ("high", "medium", "low")
- "high" should be the majority (occupations with wage data that are neither broad nor catchall)
- "low" count: exactly 23 (the null-wage occupations)

**FutureProof Mapping**
- backs_stats: "ERN,GRW" for all 832 rows
- backs_bosses: "Market,Ceiling" for all 832 rows

**Derived Field Consistency**
- data_completeness: value set is exactly {0.25, 0.5, 0.75, 1.0} (no rows should have 0.0 — all have employment fields)
- wage_tier null ↔ wage_available = False (exact correspondence)

## Golden Dataset

At least 3 independently verifiable derivation chains:

1. **Software Developers (15-1252)** — employment_change_pct = 15.8 → grw_score should be ≈ 8.4 (interpolated in 10.0–20.0 band: 7.5 + (15.8-10.0)/(20.0-10.0) * 1.5 = 7.5 + 0.87 = 8.37). Wage $133,080 → should be in "very_high" or "high" wage_tier. confidence_tier = "high" (not broad, not catchall, has wage).

2. **Registered Nurses (29-1141)** — employment_change_pct = 4.9 → grw_score should be ≈ 6.47 (interpolated in 1.0–5.0 band: 5.0 + (4.9-1.0)/(5.0-1.0) * 1.5 = 5.0 + 1.46 = 6.46). Large employment base (3.4M) → high openings_score → strong market_score.

3. **A null-wage occupation** (e.g., Family Medicine Physicians 29-1215) — wage fields all null, wage_tier null, wage_percentile null, confidence_tier = "low". But grw_score and market_score should still be computed (employment data exists).

Each value traceable: Silver row → Gold derivation formula → expected output.

## Governance Artifacts

- [ ] Business glossary: `governance/business-glossary.json` (Gold-specific terms: GRW score, market score, wage tier, occupation confidence tier, FutureProof stat mapping)
- [ ] Conceptual model: `governance/models/gold-occupation-profiles-bls-ooh-conceptual.md`
- [ ] Logical model: `governance/models/gold-occupation-profiles-bls-ooh-logical.md`
- [ ] Physical model: `governance/models/gold-occupation-profiles-bls-ooh-physical.md`
- [ ] EDA report: `governance/eda/gold-occupation-profiles-eda.md`
- [ ] DQ rules: `governance/dq-rules/gold-occupation-profiles-bls-ooh.json`
- [ ] DQ scorecard: `governance/dq-scorecards/gold-occupation-profiles-bls-ooh-scorecard.md`
- [ ] Chaos manifest: `governance/chaos-manifests/gold-occupation-profiles-bls-ooh-chaos.md`
- [ ] Golden dataset: `governance/golden-datasets/gold-occupation-profiles-bls-ooh-golden.json`
- [ ] Lineage: `governance/lineage/gold-occupation-profiles-bls-ooh-{timestamp}.json`
- [ ] Data contract: `governance/data-contracts/consumable-occupation-profiles.yaml`
- [ ] Staff review: `governance/reviews/gold-occupation-profiles-bls-ooh-staff-review.md`

## Open Decisions for Human Approval

1. **GRW score piecewise breakpoints** — the proposed scale places national average growth (~4%) at ≈6.0. This means "average" is slightly above the midpoint. Confirm this feels right for the pentagon display, or adjust.

2. **Market score weighting** — 60% growth + 40% openings. This downweights opportunity volume slightly. A field growing at 15% with 200 total jobs scores lower than a field growing at 8% with 100K jobs. Confirm this tradeoff or adjust.

3. **Wage tier thresholds** — quartile-based with a 90th percentile "very_high" breakout. This is standard but could be adjusted if the pentagon display needs different granularity.

4. **Confidence tier definition** — this spec defines confidence at the occupation level. The cross-source Gold product will need its own confidence tier that accounts for crosswalk quality. This occupation-level tier is a component, not the final answer.

## FutureProof Integration Notes

### What This Table Feeds

| FutureProof Element | Field(s) Used |
|---------------------|---------------|
| **GRW stat (pentagon)** | grw_score_rounded (1–10) |
| **ERN stat (pentagon)** | median_annual_wage (raw value for computation); wage_percentile_overall (for relative positioning) |
| **Market boss fight** | market_score + growth_category |
| **Ceiling boss fight** | median_annual_wage + wage_percentile_education_tier (how close to ceiling within your education tier) |
| **Gemma career descriptions** | occupation_title, employment_current, growth_category, education_level_name, median_annual_wage |
| **Gemma "what to do in school"** | education_code, training_code (what the career requires → what to study) |
| **Compare screen** | grw_score_rounded, market_score_rounded, wage_tier across builds |

### What This Table Does NOT Feed (needs crosswalk + O*NET)

- **RES stat** — needs O*NET task data + Karpathy AI exposure scores
- **HMN stat** — needs O*NET work activity dimensions
- **AI boss fight** — needs O*NET + Karpathy
- **Burnout boss fight** — needs O*NET work context
- **Stage 3 branching** — needs O*NET career pathway data
- **School-specific tailoring** — needs CIP→SOC crosswalk to College Scorecard

This Gold product gives you GRW, partial ERN, Market, and Ceiling. The other half of the stats and bosses come from the O*NET Gold product. Together they complete the pentagon.
