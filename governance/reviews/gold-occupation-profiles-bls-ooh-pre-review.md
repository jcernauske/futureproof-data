# Governance Review: gold-occupation-profiles-bls-ooh

**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-07
**Verdict:** APPROVED

---

## Pre-Implementation Checklist Results

| # | Item | Status | Notes |
|---|------|--------|-------|
| 1 | Clear problem statement and success criteria | PASS | Problem statement (lines 9-14) is specific: build the occupation-level consumable data product that backs GRW stat and Market/Ceiling boss fights. 10 success criteria are measurable and testable. |
| 2 | Input data sources identified with paths | PASS | Source table `base.bls_ooh` (Silver zone), 832 rows, grain soc_code. Silver spec is COMPLETE with 36/36 DQ rules passing. |
| 3 | Output artifacts defined with paths and formats | PASS | Target: `consumable.occupation_profiles` Iceberg table. Module: `src/gold/bls_ooh_occupation_profiles.py`. All 12 governance artifact paths listed in Governance Artifacts section (lines 301-312). |
| 4 | Transformations described (what changes, why) | PASS | 15 transformation steps listed (lines 196-215) with clear ordering. Derivation formulas specified for all 4 derived field groups (GRW score, wage position, market score, confidence tier). Piecewise linear function has explicit breakpoints with rationale. |
| 5 | Zone assignment correct (Gold / Consumable) | PASS | Gold zone is correct -- this is a derived, consumer-facing data product with business logic (score derivations, percentile ranking, confidence tiering, FutureProof stat mappings). |
| 6 | Primary implementation agent identified | PASS | @primary-agent identified. Full 15-step agent workflow documented (lines 220-235). |
| 7 | DQ rule categories specified or acknowledged | PASS | 8 expected DQ rule areas documented (lines 248-286) with specific thresholds, distributions, and null counts. Rules deferred to @dq-rule-writer with EDA evidence. |
| 8 | CDE mapping impact assessed | PASS | @cde-tagger listed in workflow step 12. New derived fields (grw_score, market_score, wage_percentile_overall, wage_percentile_education_tier, wage_tier, confidence_tier, data_completeness) will need CDE/PII classification. |
| 9 | Lineage scope defined | PASS | @lineage-tracker listed in workflow step 11. Lineage artifact path specified (line 310). Source-to-target field mapping is explicit in the schema tables (Source/Derivation columns). |
| 10 | Breaking changes to existing schemas flagged | PASS | No breaking changes -- this is a greenfield table. No existing `consumable.occupation_profiles` table. |
| 11 | Testing approach defined | PASS | Golden dataset with 3 independently verifiable derivation chains specified (lines 289-298). DQ rule execution required. Chaos monkey 5-cycle hardening included (@adversarial-auditor is RUN, not SKIP -- correct for first occupation-level Gold product with novel score derivations). |

---

## Data Model Gate (Greenfield -- Gold Zone)

This is a greenfield spec (target table `consumable.occupation_profiles` does not exist). Per the pipeline workflow, the 3-stage data modeling progression is required BEFORE implementation.

| # | Gate Item | Status | Notes |
|---|-----------|--------|-------|
| 1 | Business terms identified by @data-steward | NOT YET (expected) | @data-steward is step 2 in the workflow. Gold-specific terms (GRW score, market score, wage tier, occupation confidence tier, FutureProof stat mapping) are identified in the spec and listed in the Governance Artifacts section (line 301). The existing glossary has BT-001 through BT-045 from Silver-era terms. |
| 2 | Conceptual model exists | NOT YET (expected) | @semantic-modeler is steps 3-5. No Gold occupation models exist in `governance/models/` yet. |
| 3 | Logical model exists | NOT YET (expected) | Same as above. |
| 4 | Physical model exists | NOT YET (expected) | Same as above. |

**Model Gate Verdict:** These artifacts are produced during the pipeline workflow (steps 2-5), which runs AFTER governance-reviewer-pre approval. The pre-review verifies that the spec defines these artifacts as required deliverables and that the workflow includes the correct agent sequence with HUMAN APPROVAL GATES at steps 3 and 4. Both conditions are met. The model gate will be enforced at post-implementation review.

---

## Spec Completeness Assessment

### Schema Completeness: PASS

The schema defines 25+ fields across 9 categories (Identity, Classification, Employment & Growth, Compensation, Education & Entry Requirements, Derived GRW Score, Derived Wage Position, Derived Market Opportunity, Derived Data Quality Context, FutureProof Stat Mapping, Metadata). Each field has type, source/derivation, required flag, and descriptive notes. Derivation formulas are explicit and unambiguous.

### Transformation Clarity: PASS

All 15 transformations are well-specified:
- GRW score: piecewise linear function with 8 segments, explicit breakpoints, interpolation formulas, and rationale for anchoring national average growth (~4%) at approximately 6.0.
- Market score: weighted composite (60% GRW + 40% openings percentile rank), with null propagation rules.
- Wage percentile: DuckDB PERCENT_RANK window functions, null-safe (exclude nulls from ranking), partitioned by education_code for within-tier ranking.
- Wage tier: 5-tier bucketing with explicit percentile thresholds.
- Confidence tier: 3-tier bucketing with clear criteria mapping from broad/catchall/wage flags.
- Data completeness: fraction of 4 core fields that are non-null, producing discrete values {0.0, 0.25, 0.5, 0.75, 1.0}.

### Dropped Fields: PASS

6 Silver fields explicitly dropped with justification (lines 188-193): employment_change, median_wage_capped, education_typical, work_experience, training_typical, ingested_at. All justifications are reasonable -- redundant fields or Silver-only metadata. Silver preserves them for lineage.

### Golden Dataset Plan: PASS

3 independently verifiable derivation chains with explicit interpolation math:
1. Software Developers (15-1252): employment_change_pct=15.8, expected grw_score ~8.37, "very_high" or "high" wage_tier, confidence_tier="high".
2. Registered Nurses (29-1141): employment_change_pct=4.9, expected grw_score ~6.46, large employment base for strong market_score.
3. Null-wage occupation (29-1215): wage fields null, confidence_tier="low", but GRW/market still computed.

Each chain traces Silver row through Gold derivation formula to expected output. The GRW score interpolation math is shown step-by-step, which is excellent for verification.

### Agent Workflow: PASS

15-step workflow with correct ordering:
- Governance pre-review (step 1) before any work.
- Data steward (step 2) and semantic modeler (steps 3-5) with HUMAN APPROVAL GATES before implementation.
- Data analyst EDA (step 6) before DQ rule writing (step 7) -- correct dependency.
- Implementation (step 8) after model approval.
- DQ execution (step 9) after implementation.
- Chaos monkey (step 10) with 5-cycle hardening -- appropriate for novel score derivations.
- Governance post-review (step 14) and staff review (step 15) as final gates.

### Conditionally Skippable Agents: PASS

| Agent | Decision | Governance Compliance |
|-------|----------|----------------------|
| @entity-resolver | SKIP | PASS -- single-source Gold product. Cross-source resolution happens in crosswalk spec. |
| @pii-scanner | SKIP | PASS -- aggregated occupation-level statistics. No individual data. Consistent with domain context PII assessment. |
| @temporal-modeler | SKIP | PASS -- single-snapshot projection cycle. Full table replace on refresh. |
| @adversarial-auditor | RUN | PASS -- correct decision. First occupation-level Gold product with novel score derivation formulas (GRW piecewise, market composite). These are the formulas that directly produce FutureProof stat values shown to students. Adversarial testing is warranted. |

---

## Alignment with Silver Source Contract

Cross-referenced the Gold spec schema against `governance/data-contracts/base-bls-ooh.yaml`:

| Gold Spec Field | Silver Contract Field | Type Match | Notes |
|----------------|----------------------|------------|-------|
| soc_code (string) | soc_code (varchar) | PASS | CDE in Silver (BT-027). Correctly carried as identity field. |
| occupation_title (string) | occupation_title (varchar) | PASS | |
| soc_major_group (string) | soc_major_group (varchar) | PASS | |
| soc_major_group_name (string) | soc_major_group_name (varchar) | PASS | |
| broad_occupation_flag (boolean) | broad_occupation_flag (boolean) | PASS | |
| catchall_flag (boolean) | catchall_flag (boolean) | PASS | |
| employment_current (long) | employment_current (bigint) | PASS | CDE in Silver (BT-031). |
| employment_projected (long) | employment_projected (bigint) | PASS | CDE in Silver (BT-032). |
| employment_change_pct (double) | employment_change_pct (double) | PASS | CDE in Silver (BT-034). Primary GRW input. |
| openings_annual_avg (long) | openings_annual_avg (bigint) | PASS | |
| growth_category (string) | growth_category (varchar) | PASS -- see issue #1 | Silver contract says required=false (nullable). Gold spec says required=yes. See Issues section. |
| median_annual_wage (double) | median_annual_wage (double) | PASS | CDE in Silver (BT-036). 23 nulls. |
| wage_available (boolean) | wage_available (boolean) | PASS | |
| education_code (int) | education_code (integer) | PASS | |
| education_level_name (string) | education_level_name (varchar) | PASS | |
| work_experience_code (int) | work_experience_code (integer) | PASS | |
| training_code (int) | training_code (integer) | PASS | |
| source_load_date (date) | source_load_date (date) | PASS | |

**Dropped fields verified:** employment_change, median_wage_capped, education_typical, work_experience, training_typical, ingested_at -- all present in Silver contract, all dropped with justification in Gold spec. No fields are dropped without documentation.

---

## Alignment with Insight Report

Cross-referenced against `governance/insights/silver-bls-ooh-to-gold-insights.md`:

| Insight Report Criterion | Spec Coverage | Status |
|--------------------------|---------------|--------|
| Row count = 832 (1:1 with Silver) | Spec line 19: "832 rows" and DQ rules section "exactly 832" | PASS |
| Grain uniqueness: zero duplicates on soc_code | Spec success criteria and DQ rules: "zero duplicates" | PASS |
| grw_score range 1.0-10.0, null only when employment_change_pct null (0 rows) | DQ rules lines 257-258 | PASS |
| grw_score for SW Dev (15-1252): ~8.37 | Golden dataset #1 (line 291): "8.37" with interpolation math shown | PASS |
| grw_score for Reg Nurses (29-1141): ~6.46 | Golden dataset #2 (line 293): "6.46" with interpolation math shown | PASS |
| wage_percentile_overall null count = 23 | DQ rules line 270: "null count = 23" | PASS |
| confidence_tier "low" count = exactly 23 | DQ rules line 277: "exactly 23" | PASS |
| backs_stats = "ERN,GRW" for all 832 rows | DQ rules line 280: "ERN,GRW for all 832 rows" | PASS |
| backs_bosses = "Market,Ceiling" for all 832 rows | DQ rules line 281: "Market,Ceiling for all 832 rows" | PASS |
| market_score null count = 0 | Insight report line 35. Spec implies this (all rows have employment_change_pct and openings_annual_avg). DQ rules do not state this explicitly. | See issue #2 |
| Confidence tier overlap analysis (broad/catchall vs null-wage) | Insight report line 225-228 raises the overlap question. Spec confidence tier definition (lines 176-179) handles it (wage_available=False overrides). DQ rules do not verify expected tier counts. | See issue #3 |

---

## Derivation Logic Review

### GRW Score: PASS

The piecewise linear function is well-specified with 8 segments. Boundary conditions are clear:
- Floor at 1.0 (employment_change_pct <= -20.0)
- Cap at 10.0 (employment_change_pct >= 50.0)
- Linear interpolation between breakpoints
- Null propagation if input is null (0 expected currently)

The anchoring of national average growth (~4%) at approximately 6.0 is a design choice flagged for human approval (Open Decision #1). This is appropriate -- it is a tunable parameter that affects the visual presentation on the pentagon.

### Market Score: PASS

The composite formula (0.6 * grw_score + 0.4 * openings_score) is clear. The openings_score derivation using PERCENT_RANK mapped to 1-10 is well-defined. Null propagation rules are explicit.

The 60/40 weighting is flagged for human approval (Open Decision #2). This is appropriate.

### Wage Tier: PASS

5-tier bucketing with explicit thresholds. The 90th percentile "very_high" breakout is flagged for human approval (Open Decision #3). Null propagation is correct (null if wage_percentile_overall is null).

### Confidence Tier: PASS with ADVISORY

3-tier logic is clear and the override precedence is correct (wage_available=False takes priority). The spec notes this is an occupation-level tier, not the final cross-source confidence tier (Open Decision #4). This scoping is appropriate.

### Data Completeness: PASS with ADVISORY

The formula counts non-null values among 4 core fields divided by 4. The DQ rules section (line 284) states "no rows should have 0.0 -- all have employment fields." This is consistent with the Silver data (0 nulls for employment_current, employment_change_pct, openings_annual_avg; 23 nulls for median_annual_wage). However, see issue #4 regarding the expected value set.

---

## Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | ADVISORY | Gold spec marks `growth_category` as `required: yes` (line 69), but the Silver source contract marks it as `required: false` (nullable). The Silver staff review (issue #3) flagged this same inconsistency at the Silver layer -- the Silver spec says required=yes but the code and physical model correctly treat it as nullable. In practice, growth_category is null only when employment_change_pct is null (currently 0 rows), so this has no runtime impact. The Gold spec should match the Silver contract and mark growth_category as `required: no` for consistency. | No -- 0 rows affected in current data. @semantic-modeler should use `required: no` in the physical model to match Silver. |
| 2 | ADVISORY | The insight report states "market_score null count = 0" as a verification criterion, but the Gold spec's DQ rules section does not include an explicit rule for market_score null count. The spec's derivation section says "Null if grw_score is null or openings_annual_avg is null" and since both inputs currently have 0 nulls, market_score should have 0 nulls. @dq-rule-writer should include an explicit rule: market_score null count = 0. | No -- @dq-rule-writer will have access to insight report and EDA findings. |
| 3 | ADVISORY | Confidence tier expected counts are not specified in the DQ rules section. The insight report (lines 224-228) raises the question of overlap between null-wage occupations and broad/catchall flags. The spec's confidence tier definition correctly handles this (wage_available=False overrides), but the DQ rules section only specifies '"low" count: exactly 23' and '"high" should be the majority.' @dq-rule-writer should include expected counts for all 3 tiers, accounting for any overlaps between the 23 null-wage and the 77 broad/catchall occupations. | No -- @dq-rule-writer will resolve counts during EDA. |
| 4 | ADVISORY | Data completeness expected value set (line 284) states {0.25, 0.5, 0.75, 1.0} with "no rows should have 0.0." This is correct for current data (all rows have at least 1 of 4 core fields non-null), but the formula itself can produce 0.0. If future BLS data has an occupation with all 4 core fields null, data_completeness would be 0.0. The DQ rule should validate current expectation (minimum 0.25) without hardcoding the value set as a permanent constraint. | No -- minor. @dq-rule-writer can phrase the rule as "data_completeness >= 0.25 for current cycle." |
| 5 | ADVISORY | The GRW score piecewise function's highest segment (>= 20.0) linearly interpolates from 9.0 at 20.0 to 10.0 at 50.0, capped at 10.0. The maximum employment_change_pct in current Silver data is 49.9 (per insight report). This means one occupation will score very close to 10.0 (approximately 9.99). This is fine but worth noting: the cap at 50.0 was chosen to just barely encompass the current data maximum. If future BLS data has growth above 50%, the cap still applies correctly. | No -- informational. The cap behavior is well-defined. |
| 6 | ADVISORY | The `grw_score_rounded` and `market_score_rounded` fields use `ROUND()` which in most implementations uses banker's rounding (round half to even). The spec does not specify the rounding mode. For a 1-10 integer display value, this is unlikely to cause issues (the difference between rounding 7.5 to 7 vs 8 is cosmetically minor), but @primary-agent should document which rounding mode is used. | No -- cosmetic. Implementation should document rounding mode in code comments. |

---

## FutureProof Integration Notes Review

The integration mapping table (lines 328-337) correctly documents which FutureProof elements each field backs. The "What This Table Does NOT Feed" section (lines 339-347) correctly scopes the product's boundaries -- the remaining stats (RES, HMN) and boss fights (AI, Burnout) require O*NET data that has not been ingested yet.

This is good product documentation. It makes clear that this Gold product delivers GRW + partial ERN + Market + Ceiling, and that the other half of the pentagon comes from the O*NET Gold product.

---

## Open Decisions Assessment

4 open decisions are flagged for human approval:
1. GRW score breakpoints -- appropriate design parameter for human tuning
2. Market score weighting (60/40) -- appropriate tradeoff for human judgment
3. Wage tier thresholds -- standard approach, flagged for customization
4. Confidence tier scoping -- correctly notes this is occupation-level only

All 4 are legitimate design decisions, not governance gaps. They do not block pre-implementation review because they are addressed by the @semantic-modeler step with HUMAN APPROVAL GATES (steps 3-4 in the workflow).

---

## Decision Rationale

**APPROVED.** This spec is implementation-ready. The rationale:

1. **Completeness:** All 11 pre-implementation checklist items pass. The spec defines clear inputs, outputs, transformations, success criteria, and a testing approach.

2. **Schema rigor:** 25+ fields are fully specified across 9 categories with types, derivations, nullability, and business context. Every derived field has an explicit formula with boundary conditions and null propagation rules.

3. **Derivation quality:** The GRW score piecewise function is the most complex derivation in the project to date, and it is specified to a level where golden dataset values can be independently verified by hand calculation. The interpolation math in the golden dataset section demonstrates this -- grw_score for 15.8% growth is worked out step-by-step as 7.5 + (15.8-10.0)/(20.0-10.0) * 1.5 = 8.37.

4. **Governance alignment:** The spec references the correct source table, uses the idempotent promote pattern, defines grain fields for dedup, and plans all 12 required governance artifacts. The workflow includes HUMAN APPROVAL GATES at the correct steps.

5. **Insight report alignment:** The spec directly implements the insight report's Tier 1 Product #1, with verification criteria that match the insight report's expectations for row counts, score ranges, null counts, and golden dataset values.

6. **Adversarial auditor correctly included:** Unlike the College Scorecard Gold spec which skipped @adversarial-auditor, this spec runs it -- appropriate because GRW and market score are novel derivation formulas that directly produce FutureProof stat values shown to students. The 5-cycle hardening is warranted.

7. **Source contract consistency:** All 18 carried fields match the Silver contract types and semantics. All 6 dropped fields are justified. No fields are carried without documentation.

The 6 ADVISORY issues are all non-blocking: growth_category required flag mismatch (0 rows affected), 3 DQ rule coverage gaps that @dq-rule-writer will address with EDA evidence, 1 informational note about the GRW cap boundary, and 1 cosmetic note about rounding mode.

**This spec may proceed to Step 2 (@data-steward).**
