# Spec: gold-futureproof-engine

**Status:** COMPLETE
**Zone:** Gold
**Primary Agent:** @primary-agent
**Created:** 2026-04-08
**Revised:** 2026-04-09 (consolidated CIP granularity fix from addendum)

## Problem Statement

Build the unified cross-source Gold product that powers FutureProof's core loop: **school + major → career outcomes → five-stat pentagon → boss fights → branching paths.** This is the final data product in the pipeline — it joins College Scorecard, BLS OOH, O*NET, and the CIP-SOC crosswalk into a single queryable surface that the Gemma agent and frontend consume directly.

Every other Gold product was single-source. This one is the payoff — it executes the full join chain and pre-computes everything the product needs at query time.

## Source Data (All Existing Gold + Silver)

| Source | Type | Grain | Key Fields |
|--------|------|-------|------------|
| consumable.career_outcomes | Gold | unitid × cipcode × credlev | ERN (earnings), ROI (debt-to-earnings), effort slider percentiles. **cipcode is 4-digit XX.XX format.** |
| consumable.occupation_profiles | Gold | soc_code | GRW score, market score, wage data, education requirements |
| consumable.onet_work_profiles | Gold | bls_soc_code | HMN score, Burnout score, activity/context summaries |
| consumable.career_transitions | Gold | bls_soc_code × related_bls_soc_code | Stage 3 branching graph |
| base.cip_soc_crosswalk | Silver | cipcode × soc_code | The bridge. **cipcode is 6-digit XX.XXXX format.** match_quality flags. |

## What This Spec Produces

| # | Gold Table | Grain | Purpose |
|---|-----------|-------|---------|
| 1 | **consumable.program_career_paths** | unitid × cipcode × soc_code | The core query table. One row per school+major+career combination. Contains all five stats, boss fight inputs, and confidence scoring. |
| 2 | **consumable.career_branches** | soc_code × related_soc_code | Pre-computed Stage 3 branches enriched with full stat profiles for both source and target occupations. Ready for the branch tree visualization. |

## Technical Design

### CRITICAL: CIP Granularity Mismatch Resolution

**The problem:** College Scorecard stores CIP codes as 4-digit (`XX.XX`, e.g., `52.02`). The CIP-SOC crosswalk stores CIP codes as 6-digit (`XX.XXXX`, e.g., `52.0201`). Under strict matching, **0% of Scorecard programs match the crosswalk.** The crosswalk Silver EDA confirmed this — `has_scorecard_match` is FALSE for all 5,903 rows.

**The fix:** Join on the 4-digit CIP prefix. Truncate the crosswalk's 6-digit CIP to match Scorecard's 4-digit format:

```sql
JOIN base.cip_soc_crosswalk xw
  ON co.cipcode = LEFT(xw.cipcode, 5)
```

Example: Scorecard `cipcode = "52.02"` matches crosswalk entries `52.0201`, `52.0202`, `52.0203`, etc.

**Coverage (from crosswalk EDA):**
- **91.0%** of Scorecard CIP codes find at least one crosswalk match via 4-digit prefix
- **97.1%** of Scorecard rows are covered
- The ~9% of CIPs without matches tend to be small/niche programs
- Programs with no crosswalk match get **zero rows** in `consumable.program_career_paths` (filtered out by INNER JOIN)

**Cardinality impact:** A single Scorecard CIP (e.g., `52.02`) may match multiple 6-digit crosswalk CIPs (`52.0201`, `52.0202`, `52.0203`), each of which maps to multiple SOC codes. This increases fan-out per Scorecard program. After the join, dedup on the grain `(unitid, cipcode, soc_code)` — the `compute_grain_id` promote pattern handles this naturally.

### Table 1: consumable.program_career_paths

**The core product table.** When a student picks Indiana State University + Business Administration, this table returns all the career paths that combination leads to, each with a complete five-stat pentagon and boss fight profile.

**Join chain:**
```
consumable.career_outcomes (unitid=ISU, cipcode=52.02)
  → base.cip_soc_crosswalk (JOIN ON career_outcomes.cipcode = LEFT(crosswalk.cipcode, 5))
    → cipcode 52.02 matches crosswalk 52.0201, 52.0202, 52.0203, etc.
    → each crosswalk row brings a soc_code: 11-1021, 13-1111, 13-2051, ...
      → consumable.occupation_profiles (soc_code → GRW, market, wage)
      → consumable.onet_work_profiles (bls_soc_code → HMN, burnout)
  → DEDUP on grain (unitid, cipcode, soc_code) — same SOC via multiple 6-digit CIPs kept once
```

**Grain:** unitid × cipcode × soc_code (one row per school × program × career outcome)

**Schema:**

#### Identity
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| record_id | string | derived | yes | `compute_grain_id(row, ['unitid', 'cipcode', 'soc_code'], prefix='pcp')` |
| unitid | long | career_outcomes | yes | IPEDS institution ID |
| institution_name | string | career_outcomes | yes | School name |
| cipcode | string | career_outcomes | yes | CIP program code (XX.XX — 4-digit from Scorecard) |
| program_name | string | career_outcomes | yes | Program name (e.g., "Business Administration") |
| cip_family | string | career_outcomes | yes | 2-digit CIP family |
| cip_family_name | string | career_outcomes | yes | CIP family name |
| soc_code | string | crosswalk | yes | SOC occupation code (XX-XXXX) |
| occupation_title | string | occupation_profiles OR onet_work_profiles | yes | Career name |
| soc_major_group_name | string | occupation_profiles | no | SOC major group |

#### The Five Stats (1–10 scale, pentagon-ready)
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| stat_ern | int | derived | no | **Earning Power.** 1–10. Derived from career_outcomes earnings + occupation_profiles wage percentile. See derivation. |
| stat_roi | int | derived | no | **Return on Investment.** 1–10. Derived from career_outcomes debt-to-earnings ratio. See derivation. |
| stat_res | int | placeholder | no | **AI Resilience.** 1–10. PLACEHOLDER — requires Karpathy scores + task-level AI scoring (separate spec). Set to null for hackathon MVP. |
| stat_grw | int | occupation_profiles.grw_score_rounded | no | **Growth.** 1–10. Direct from BLS OOH Gold. |
| stat_hmn | int | onet_work_profiles.hmn_score_rounded | no | **Human Edge.** 1–10. Direct from O*NET Gold. |

#### Boss Fight Inputs
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| boss_ai_score | int | placeholder | no | AI boss. PLACEHOLDER — same dependency as stat_res. Null until Karpathy integration. |
| boss_loans_score | int | derived | no | Student Loans boss. Derived from debt-to-earnings. See derivation. |
| boss_market_score | int | occupation_profiles.market_score_rounded | no | Market boss. Direct from BLS OOH Gold. |
| boss_burnout_score | int | onet_work_profiles.burnout_score_rounded | no | Burnout boss. Direct from O*NET Gold. |
| boss_ceiling_score | int | derived | no | Ceiling boss. Derived from wage percentile within education tier. See derivation. |

#### Program-Level Context (from College Scorecard)
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| earnings_1yr_median | double | career_outcomes | no | Median earnings 1yr post-grad |
| earnings_1yr_p25 | double | career_outcomes | no | 25th percentile (effort slider: low focus) |
| earnings_1yr_p75 | double | career_outcomes | no | 75th percentile (effort slider: high focus) |
| debt_median | double | career_outcomes | no | Median debt |
| debt_to_earnings_annual | double | career_outcomes | no | Key affordability ratio |
| confidence_tier_program | string | career_outcomes | no | Scorecard confidence tier |

#### Occupation-Level Context (from BLS + O*NET)
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| median_annual_wage | double | occupation_profiles | no | Occupation-level median wage |
| growth_category | string | occupation_profiles | no | "declining_fast" through "booming" |
| employment_current | long | occupation_profiles | no | Current employment count |
| education_level_name | string | occupation_profiles | no | Typical education requirement |
| top_5_activities | string | onet_work_profiles | no | JSON: top work activities |
| top_human_activities | string | onet_work_profiles | no | JSON: top human-edge activities |
| burnout_drivers | string | onet_work_profiles | no | JSON: top burnout contributors |
| time_pressure | double | onet_work_profiles | no | Individual burnout element |
| work_hours | double | onet_work_profiles | no | Duration of typical work week |

#### Data Quality
| Field | Type | Derivation | Required | Notes |
|-------|------|-----------|----------|-------|
| match_quality | string | derived at Gold time | yes | See derivation below. **Do NOT use crosswalk Silver's has_scorecard_match flag** — it is FALSE for all rows due to the CIP granularity mismatch. Derive from actual join results instead. |
| stats_available_count | int | derived | yes | How many of the 5 stats are non-null (0–5) |
| bosses_available_count | int | derived | yes | How many of the 5 bosses are non-null (0–5) |
| overall_confidence | string | derived | yes | See derivation below |

#### Metadata
| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| promoted_at | timestamp | generated | yes | |

### ERN Stat Derivation (1–10)

Combines program-level earnings (Scorecard) with occupation-level wage position (BLS):

```
raw_ern = 0.6 * scorecard_percentile + 0.4 * occupation_wage_percentile
stat_ern = ROUND(1.0 + 9.0 * raw_ern)
```

Where:
- `scorecard_percentile` = `cip_family_earnings_rank` from career_outcomes (how this program's earnings compare within its CIP family, 0.0–1.0)
- `occupation_wage_percentile` = `wage_percentile_overall` from occupation_profiles (how this occupation's wage compares to all occupations, 0.0–1.0)

60% weight on actual program earnings (school-specific), 40% on occupation-level wage (career-level). Null if either input is null.

### ROI Stat Derivation (1–10)

Maps debt-to-earnings ratio inversely to a 1–10 scale:

| debt_to_earnings_annual | stat_roi | Rationale |
|------------------------|----------|-----------|
| ≤ 0.25 | 10 | Excellent — very low debt relative to earnings |
| 0.25 → 0.75 | 10 → 8 | Strong ROI |
| 0.75 → 1.5 | 8 → 5 | Average range |
| 1.5 → 2.5 | 5 → 3 | Concerning |
| 2.5 → 4.0 | 3 → 1 | Poor ROI |
| > 4.0 | 1 | Very poor — debt massively exceeds earnings |

Piecewise linear interpolation, same pattern as GRW. Null if debt_to_earnings_annual is null.

### Boss Loans Score Derivation (1–10)

Inverse of ROI — higher score means the Student Loans boss is stronger (worse for the student):

```
boss_loans_score = 11 - stat_roi
```

ROI of 10 → Loans boss is 1 (easy fight). ROI of 1 → Loans boss is 10 (devastating).

### Boss Ceiling Score Derivation (1–10)

Measures how constrained this occupation's earnings are within its education tier:

```
boss_ceiling_score = ROUND(10.0 - 9.0 * wage_percentile_education_tier)
```

Low earner within tier → boss is strong (ceiling is real, you're stuck below it). High earner → boss is weak (you've already pushed past it). This is the simplest defensible formula. Null if wage_percentile_education_tier is null.

### Match Quality Derivation (Gold-Time)

**Do NOT use the crosswalk Silver's `has_scorecard_match` flag** — it is FALSE for all 5,903 rows because the Silver spec used strict 6-digit matching. Instead, derive match_quality at Gold time based on whether the occupation-level joins actually produced data:

```
match_quality = CASE
  WHEN bls_join_succeeded AND onet_join_succeeded THEN 'full'
  WHEN bls_join_succeeded AND NOT onet_join_succeeded THEN 'partial_no_onet'
  WHEN NOT bls_join_succeeded AND onet_join_succeeded THEN 'partial_no_bls'
  WHEN NOT bls_join_succeeded AND NOT onet_join_succeeded THEN 'scorecard_only'
END
```

Where `bls_join_succeeded` = occupation_profiles row exists for this soc_code, `onet_join_succeeded` = onet_work_profiles row exists for this soc_code.

### Overall Confidence Derivation

| Tier | Criteria |
|------|----------|
| high | stats_available_count >= 4 AND match_quality = "full" |
| medium | stats_available_count >= 2 AND match_quality contains "partial" |
| low | stats_available_count < 2 OR match_quality = "scorecard_only" |

### Transformations (Table 1)

1. **Read career_outcomes** (College Scorecard Gold)
2. **Join to crosswalk using 4-digit CIP prefix:** `career_outcomes.cipcode = LEFT(crosswalk.cipcode, 5)`. This is the critical join — Scorecard uses XX.XX, crosswalk uses XX.XXXX. The LEFT(5) truncation produces the 4-digit prefix match. One Scorecard program may match multiple crosswalk entries, each bringing different SOC codes.
3. **LEFT JOIN to occupation_profiles** on `crosswalk.soc_code = occupation_profiles.soc_code` → adds BLS data (GRW, market, wage). LEFT JOIN so rows without BLS data are preserved with nulls.
4. **LEFT JOIN to onet_work_profiles** on `crosswalk.soc_code = onet_work_profiles.bls_soc_code` → adds O*NET data (HMN, burnout). LEFT JOIN for same reason.
5. **Dedup on grain** (unitid, cipcode, soc_code) — the 4-digit prefix join may produce duplicate (unitid, cipcode, soc_code) rows if the same SOC appears via multiple 6-digit crosswalk CIPs. Keep one row per grain combination. When deduplicating, prefer the row with the most non-null stat values.
6. **Compute stat_ern** from scorecard earnings rank + occupation wage percentile
7. **Compute stat_roi** from debt-to-earnings ratio (piecewise linear)
8. **Set stat_res** to null (placeholder — Karpathy integration pending)
9. **Carry stat_grw** from occupation_profiles.grw_score_rounded
10. **Carry stat_hmn** from onet_work_profiles.hmn_score_rounded
11. **Compute boss scores** (loans from ROI inverse, ceiling from wage percentile, carry market + burnout, placeholder AI)
12. **Derive match_quality** from join success flags (NOT from crosswalk Silver has_scorecard_match)
13. **Compute stats_available_count, bosses_available_count**
14. **Compute overall_confidence**
15. **Compute record_id** and promote

### Transformer

- **Module:** `src/gold/futureproof_engine.py`
- **Function:** `transform()`
- **Pattern:** Read 4 Gold tables + 1 Silver crosswalk, join with CIP prefix matching, derive, promote to `consumable.program_career_paths`

### Row Count Estimate

The 4-digit prefix join plus many-to-many crosswalk cardinality means significant fan-out. Estimated range: **150,000–500,000 rows.** DQ rule should accept this range and flag anything outside it. DuckDB handles this fine.

---

### Table 2: consumable.career_branches

Pre-computed Stage 3 branch data. For each occupation, what are the related careers (branches), and what are their full stat profiles?

This enriches `consumable.career_transitions` with the full stat pentagon for both source and target occupations, so the frontend can render branch trees without additional queries.

**Grain:** soc_code × related_soc_code

**Schema:**

| Field | Type | Source | Required | Notes |
|-------|------|--------|----------|-------|
| record_id | string | derived | yes | `compute_grain_id(row, ['soc_code', 'related_soc_code'], prefix='br')` |
| soc_code | string | career_transitions | yes | Source occupation |
| source_title | string | career_transitions | yes | Source occupation title |
| related_soc_code | string | career_transitions | yes | Branch target occupation |
| related_title | string | career_transitions | yes | Branch target title |
| best_index | int | career_transitions | yes | Similarity rank (1 = most similar) |
| relatedness_tier | string | career_transitions | yes | Primary-Short / Primary-Long / Supplemental |
| is_primary | boolean | career_transitions | yes | True for top 10 |
| source_grw | int | occupation_profiles (source) | no | Source GRW score |
| source_hmn | int | onet_work_profiles (source) | no | Source HMN score |
| source_burnout | int | onet_work_profiles (source) | no | Source Burnout score |
| source_wage | double | occupation_profiles (source) | no | Source median wage |
| related_grw | int | occupation_profiles (related) | no | Branch target GRW score |
| related_hmn | int | onet_work_profiles (related) | no | Branch target HMN score |
| related_burnout | int | onet_work_profiles (related) | no | Branch target Burnout score |
| related_wage | double | occupation_profiles (related) | no | Branch target median wage |
| related_growth_category | string | occupation_profiles (related) | no | Branch target growth category |
| related_education_level | string | occupation_profiles (related) | no | What education the branch requires |
| grw_delta | int | derived | no | related_grw - source_grw. Positive = branch grows faster. |
| hmn_delta | int | derived | no | related_hmn - source_hmn. Positive = more human edge. |
| burnout_delta | int | derived | no | related_burnout - source_burnout. Positive = more burnout risk. |
| wage_delta | double | derived | no | related_wage - source_wage. Positive = higher pay. |
| branch_has_full_data | boolean | derived | yes | True if related occupation has both BLS and O*NET data |
| promoted_at | timestamp | generated | yes | |

### Transformations (Table 2)

1. **Read career_transitions** (Gold)
2. **Join source occupation** stats from occupation_profiles + onet_work_profiles
3. **Join related occupation** stats from occupation_profiles + onet_work_profiles
4. **Compute deltas** (grw_delta, hmn_delta, burnout_delta, wage_delta)
5. **Compute branch_has_full_data** flag
6. **Compute record_id** and promote

**Build order:** Table 1 (program_career_paths) first, Table 2 (career_branches) second. Table 2 does NOT depend on Table 1 — they're independent. But building Table 1 first validates the cross-source join chain.

### Row Count

15,944 (same as career_transitions — 1:1 enrichment).

---

## The RES Stat Gap

The **AI Resilience (RES) stat** and **AI boss fight** are placeholders (null) in this spec. They require:

1. **Karpathy's AI Exposure Scores** — 0–10 scores for ~342 BLS occupations. Available on GitHub. Needs a small Bronze ingestor.
2. **Task-level AI scoring** — Gemma scores individual O*NET tasks for automation susceptibility. This is a Gold-zone enrichment using the Gemma agent, not a traditional data pipeline.

This is a **separate spec** that should be tackled after the unified engine is working. The product is functional without RES — it has ERN, ROI, GRW, HMN (4 of 5 stats) and Loans, Market, Burnout, Ceiling (4 of 5 bosses plus the composite Final Boss). RES and AI are additive, not foundational.

For the hackathon, if Karpathy scores can be quickly ingested (it's a small CSV), stat_res can be populated with a simple Bronze → Gold pipeline for the Karpathy data. Task-level Gemma scoring is a stretch goal.

---

## Success Criteria

- [ ] Both Gold tables exist with correct schemas
- [ ] program_career_paths uses 4-digit CIP prefix join (NOT strict 6-digit match)
- [ ] program_career_paths joins all 4 source tables via crosswalk correctly
- [ ] Five stats computed (ERN, ROI, GRW, HMN populated; RES placeholder null)
- [ ] Boss scores computed (Loans, Market, Burnout, Ceiling populated; AI placeholder null)
- [ ] Career branches enriched with source and target stats + deltas
- [ ] stats_available_count and bosses_available_count accurate
- [ ] match_quality derived from join results (NOT from crosswalk Silver has_scorecard_match flag)
- [ ] overall_confidence correctly derived
- [ ] Grain integrity on both tables (dedup after CIP prefix fan-out)
- [ ] DQ rules passing
- [ ] Golden dataset with verifiable join chains including CIP prefix matching

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @data-steward — Identify business terms
3. @semantic-modeler — Conceptual model → HUMAN APPROVAL GATE
4. @semantic-modeler — Logical model → HUMAN APPROVAL GATE
5. @semantic-modeler — Physical model
6. @data-analyst — EDA (validate join coverage via CIP prefix match, stat distributions, null rates)
7. @dq-rule-writer — Gold DQ rules
8. @primary-agent — Implement 2 transformers (program_career_paths first, career_branches second)
9. @dq-engineer — Execute rules, produce scorecard
10. @chaos-monkey — 5-cycle hardening
11. @lineage-tracker — OpenLineage capture
12. @doc-generator — Dictionary + contracts
13. @governance-reviewer — Post-implementation check
14. @staff-engineer — Final review

## Conditionally Skippable Agents

| Agent | Decision | Justification |
|-------|----------|---------------|
| @entity-resolver | SKIP | All joins are on deterministic keys (CIP prefix, SOC codes). No fuzzy matching. |
| @pii-scanner | SKIP | All source data is aggregated public statistics. |
| @temporal-modeler | SKIP | Single-snapshot pipeline. Full table replace. |
| @adversarial-auditor | RUN | This is the cross-source join — adversarial testing must verify CIP prefix join coverage, null propagation through the chain, dedup correctness, and stat derivation accuracy. |

## DQ Rules

Expected areas of focus:

**consumable.program_career_paths:**
- Row count: 150,000–500,000 range (wider range due to CIP prefix fan-out)
- Grain uniqueness: unitid × cipcode × soc_code = zero duplicates (dedup must work)
- CIP prefix join coverage: ≥90% of career_outcomes distinct CIP codes matched (expect ~91%)
- stat_ern, stat_roi range: 1–10 when non-null
- stat_grw, stat_hmn range: 1–10 when non-null
- stat_res: 100% null (placeholder)
- stats_available_count distribution: expect majority with 4 (all except RES)
- boss scores range: 1–10 when non-null
- boss_ai_score: 100% null (placeholder)
- match_quality distribution: expect majority "full" (based on crosswalk EDA: 76.6% estimated)
- overall_confidence distribution: expect majority "high" for "full" match quality rows
- Null propagation: verify that nulls from upstream (e.g., null wages) correctly propagate to null stats

**consumable.career_branches:**
- Row count: 15,944 (1:1 with career_transitions)
- Grain uniqueness: soc_code × related_soc_code = zero duplicates
- Delta fields: range check (stat deltas should be -9 to +9, wage deltas reasonable)
- branch_has_full_data: correlates with match_quality in the underlying data

## Golden Dataset

1. **Indiana State University + Business Administration → Financial Analyst** — trace the full join chain: Scorecard CIP `52.02` → crosswalk prefix match → `52.0201` (and others) → SOC `13-2051` → BLS growth/wage → O*NET HMN/burnout. Verify all 4 non-placeholder stats compute correctly. Verify CIP prefix matching produces the expected SOC codes.

2. **A program with poor ROI** — verify stat_roi is low, boss_loans_score is high (inverse relationship).

3. **A career branch pair** — verify source and target stats populated, deltas computed correctly, wage_delta sign is correct.

## Open Decisions for Human Approval

1. **ERN weighting (60/40 program vs. occupation)** — this weights school-specific earnings higher than general occupation wages. A Stanford CS grad's ERN is pulled up by Stanford's earnings data, even though Software Developer median wage is the same everywhere. This captures the school premium. Confirm or adjust.

2. **ROI piecewise breakpoints** — the thresholds above are based on Department of Education Gainful Employment guidance. Confirm they feel right for the pentagon display.

3. **Ceiling boss formula** — the simplified approach uses wage percentile within education tier. A more sophisticated approach would use BLS experience-level salary data to measure actual earnings trajectory flatness. The simple approach is defensible for hackathon. Confirm.

4. **RES stat as null placeholder** — confirm that shipping with 4/5 stats and 4/5 bosses is acceptable for the hackathon. The pentagon can render with a "coming soon" treatment on the RES vertex.

5. **CIP prefix matching breadth** — the 4-digit prefix join is coarser than the crosswalk was designed for. A Business Admin program (CIP 52.02) now maps to careers from Business Admin AND Management (52.0201), Business Commerce (52.0202), and other 52.02xx programs. This may produce some spurious career paths. For the hackathon, accept the broader match — it's better to show too many career paths than zero. Post-hackathon, consider enriching Scorecard data with 6-digit CIP codes from IPEDS or using Gemma to filter relevant paths.

## Governance Artifacts

- [ ] Business glossary: `governance/business-glossary.json`
- [ ] Conceptual model: `governance/models/gold-futureproof-engine-conceptual.md`
- [ ] Logical model: `governance/models/gold-futureproof-engine-logical.md`
- [ ] Physical model: `governance/models/gold-futureproof-engine-physical.md`
- [ ] EDA report: `governance/eda/gold-futureproof-engine-eda.md`
- [ ] DQ rules: `governance/dq-rules/gold-futureproof-engine.json`
- [ ] DQ scorecard: `governance/dq-scorecards/gold-futureproof-engine-scorecard.md`
- [ ] Chaos manifest: `governance/chaos-manifests/gold-futureproof-engine-chaos.md`
- [ ] Golden dataset: `governance/golden-datasets/gold-futureproof-engine-golden.json`
- [ ] Lineage: `governance/lineage/gold-futureproof-engine-{timestamp}.json`
- [ ] Data contracts: `governance/data-contracts/consumable-program-career-paths.yaml`, `governance/data-contracts/consumable-career-branches.yaml`
- [ ] Staff review: `governance/reviews/gold-futureproof-engine-staff-review.md`

## What This Unlocks

After this spec, the data pipeline is complete. The MCP layer (`/bs:serve`) exposes:

| Query Pattern | Source Table | Example |
|--------------|-------------|---------|
| "School + Major → Career Outcomes" | consumable.program_career_paths | "ISU Business Admin → Financial Analyst (ERN 6, ROI 5, GRW 5, HMN 4)" |
| "Career → Branch Options" | consumable.career_branches | "Financial Analyst → [Management path, Technical path, Lateral pivot, Specialist]" |
| "Occupation Deep Dive" | consumable.occupation_profiles + consumable.onet_work_profiles | "Financial Analyst: median $95K, growing at 9%, high time pressure" |
| "Compare Builds" | consumable.program_career_paths (2-3 queries) | "ISU Business vs. Michigan Advertising vs. Kelley Marketing" |

The Gemma agent calls these via MCP function tools. The frontend renders the pentagon, boss fights, and branch tree. The product works.

*Then: build the frontend.*
