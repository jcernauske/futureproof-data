# Principal Data Architect Review

**Date:** 2026-04-06
**Reviewer:** @principal-data-architect
**Scope:** Silver zone transition review (Silver to Gold)
**Domain:** Higher Education Outcomes (U.S. Department of Education College Scorecard, Field of Study)
**Spec:** silver-base-college-scorecard
**Prior Review:** governance/reviews/bronze-architecture-review.md (B+, APPROVED)

## Executive Summary

The Silver zone is solid. The transformer is clean, correct, and produces a well-structured base table with 69,947 rows, zero grain duplicates, zero unknown CIP family names, and correct CIP normalization across all rows. The governance apparatus is disproportionately thorough for a single-source education dataset -- 35 DQ rules, 5-cycle chaos monkey hardening, adversarial audit, lineage, data contract -- but the thoroughness is earned, not theatrical. The adversarial audit's critical finding (RISK-001, missing CIP families) has been fixed. The biggest concern for the Gold transition is that `institution_control` is 100% NULL because the CONTROL field was never added to the Bronze parquet, and the Gold spec plans to use it for segmentation analysis. The second concern is documentation drift: the spec, logical model, and glossary contain stale definitions that contradict the physical model and code in at least 4 places. Neither concern blocks Gold zone progression, but both must be tracked.

**Overall: This is ready to proceed to Gold, with conditions noted below.**

## Architecture Assessment
### Grade: B+
### Rationale

The Silver zone implements the correct pattern: read from Bronze Iceberg, transform (normalize CIP codes, derive CIP family, map institution control, compute small cohort flag), write to Silver Iceberg via idempotent promote. The single denormalized `base.college_scorecard` table is the right choice for this data. The conceptual model identifies 8 entities (Institution, Academic Program, CIP Family, Credential Type, Program Offering, Earnings 1yr, Earnings 2yr, Debt Outcome, Completions Measure), all of which resolve to 1:1 or 1:0..1 relationships at the program-offering grain. Normalizing these into separate dimension tables would add complexity without adding value for a single-source MVP.

Specific decisions I agree with:

1. **Flat denormalized table over star schema.** At 69,947 rows with a single source, separate dimension tables (institution dim, program dim) are premature. The Gold spec correctly plans to consume this as a wide fact table. When BLS and O*NET sources arrive and the CIP-to-SOC crosswalk creates many-to-many relationships, dimension tables will be necessary -- but not yet.

2. **Grain preservation (1:1 from Bronze to Silver).** No aggregation, no filtering, no row drops. Every Bronze row becomes one Silver row. The `transform_row()` function returns None only for rows with null grain fields, which should not exist if the Bronze ingestor is correct. Verified: 0 rows skipped in production.

3. **CIP code normalization as a string operation.** Inserting a dot at position 2 (`"5202" -> "52.02"`) is correct and defensive. The code handles already-normalized codes (passthrough) and preserves leading zeros (CIP families 01, 03, 04, 05, 09). Verified: 0 bad CIP format codes in production data.

4. **Deterministic grain hash as surrogate key.** `record_id = cs-<SHA256 truncated>` from `[unitid, cipcode, credential_level]`. Stable across re-runs. Verified: 0 nulls, 0 duplicates.

What concerns me:

1. **institution_control is architecturally broken.** The physical model says NOT NULL. The Iceberg schema says `required=False`. The data is 100% NULL. The DQ rule (SLV-CS-027) passes due to SQL NULL semantics (`NULL NOT IN (...)` evaluates to NULL, not TRUE). The data contract says `required: true`. This is four artifacts disagreeing with each other and with reality. The Gold spec (`gold-career-outcomes-college-scorecard.md`, line 53) lists `institution_control` as a field in the output schema. If Gold consumes it as-is, every row will have NULL institution control, and the segmentation analysis mentioned in the Gold spec will be impossible. **This is not blocking for Gold zone progression** -- the Gold spec can proceed with institution_control as nullable and add a note that segmentation requires the Bronze re-ingestion -- but it must be called out.

2. **CIP code format is XX.XX, not XX.XXXX.** The College Scorecard field-of-study file uses 4-digit CIP series codes (2-digit family + 2-digit subfield), producing XX.XX after normalization. The full CIP 2020 taxonomy uses 6-digit codes (XX.XXXX). The NCES CIP-to-SOC crosswalk uses 6-digit codes. When the crosswalk is ingested (planned for Silver zone integration), there will be a join mismatch: Silver has "52.02" but the crosswalk has "52.0201", "52.0203", etc. The Gold spec does not yet address this. This is a known limitation that the domain context correctly identifies (line 210-215), but the Gold spec should acknowledge it.

3. **No partition strategy.** 69,947 rows is trivially small. But the Gold spec will produce a table of similar size with more columns (30+ fields including percentile bands). When BLS/O*NET data arrives, the Silver zone will need to handle occupation-task grain data (potentially millions of rows). The architecture should plan for partition-by-cip-family or partition-by-institution-control at that scale.

## Data Quality & Trust Assessment
### Grade: A-
### Rationale

35 DQ rules, evidence-backed from EDA, 34/35 passing in production. The single failure (SLV-CS-028, raw-to-Silver row count consistency) is an execution error (wrong table name in SQL), not a data quality failure -- the row count has been verified manually as an exact 69,947-to-69,947 match.

I verified the following against the actual Iceberg data:

| Metric | Expected | Actual | Status |
|--------|----------|--------|--------|
| Row count | 69,947 | 69,947 | PASS |
| Grain duplicates | 0 | 0 | PASS |
| Distinct institutions | 2,200-3,000 | 2,559 | PASS |
| Distinct CIP codes | 350-450 | 390 | PASS |
| Distinct CIP families | 40-50 | 45 | PASS |
| Credential levels | {3} | {3} | PASS |
| Bad CIP format | 0 | 0 | PASS |
| Unknown CIP family names | 0 | 0 | PASS |
| small_cohort_flag mismatches | 0 | 0 | PASS |
| Null record_id | 0 | 0 | PASS |
| Null institution_control | 69,947 | 69,947 | KNOWN GAP |
| earnings_1yr null rate | ~64% | 64.0% | PASS |
| earnings_2yr null rate | ~60% | 60.4% | PASS |
| debt null rate | ~63% | 63.1% | PASS |
| earnings_1yr range | $4,880-$161,723 | $4,880-$161,723 | PASS |
| 2yr < 1yr rate | ~44% | 44.2% | EXPECTED |
| All outcomes null | ~53% | 52.7% | EXPECTED |
| Stanford CS earnings_1yr | $130K-$145K | $136,126 | PASS |

The DQ rule set is comprehensive for structural validation. What it does not cover is semantic validation -- it checks that `cip_family_name` is non-null but not that the name is correct for the family code. The adversarial audit (RISK-009) flagged this gap. For a Silver base table, this is acceptable -- the CIP_FAMILIES lookup is a static dictionary with 45 entries that can be visually verified. For the Gold zone, where derived metrics like debt-to-earnings ratios and percentile bands introduce computation, semantic validation becomes more important, and a golden dataset will be essential.

What earns the A-:

- The chaos monkey methodology is legitimate: 5 cycles, escalating corruption rates, honest gap analysis. 71-74% detection rate is documented as a known limitation, not hidden.
- The privacy suppression handling is correct throughout the pipeline. NULL means FERPA-suppressed, not missing. The small_cohort_flag conservative default (NULL completions = True) is the right call.
- DQ rule evidence citations are specific and auditable.

What loses the full A:

- SLV-CS-028 has never executed successfully. The 1:1 row mapping between Bronze and Silver has never been validated by a DQ rule. It works in practice (manual verification confirms 69,947 = 69,947), but the automated check is broken.
- SLV-CS-027 passes on 100% NULL institution_control due to SQL NULL semantics. This is a subtle but real gap in coverage.
- No golden dataset exists for the Silver zone. The staff review performed spot-checks (Stanford CS, UT Austin Engineering, Harvard program count), which is good, but a formal golden dataset should be created when Gold zone is built.

## Governance Assessment
### Grade: A-
### Rationale

The governance model is well-proportioned. For a public, aggregate, non-PII education dataset with 69,947 rows, the governance apparatus is thorough without being excessive.

Artifacts present and substantive:
- Pre-review, post-review, staff review, adversarial audit, entity resolution, temporal assessment
- Silver EDA report (profiles all 18 target columns, identifies 5 critical findings)
- 35 DQ rules with human approval timestamps and evidence chains
- DQ scorecard showing 34/35 passing
- 5-cycle chaos monkey hardening with honest gap analysis
- Data contract (YAML, versioned, with quality thresholds and breaking change policy)
- OpenLineage event (column-level lineage for all 18 fields)
- Business glossary (17 terms, BT-001 through BT-017)
- Conceptual, logical, and physical models (all three tiers)
- Pipeline state tracking

The adversarial audit is the standout governance artifact. It found real defects (RISK-001 through RISK-015), categorized them honestly, and the critical one (RISK-001, missing CIP families) was fixed. The audit's meta-assessment ("approximately 85% of the way to being trustworthy for a regulated environment") is fair and self-aware.

What loses the full A:

- **Documentation drift.** The spec, logical model, and glossary contain stale definitions that contradict the physical model and code. Specifically: (a) small_cohort_flag derivation rule (spec/logical say NOT NULL AND < 30; physical/code say NULL OR < 30), (b) CIP code format (spec/glossary say XX.XXXX; reality is XX.XX), (c) grain hash field names (spec says credlev; code uses credential_level), (d) institution_control derivation (physical model says integer map; code handles both text and integer). The staff review documented all 5 issues as LOW severity and non-blocking, which is correct, but the pattern of upstream documentation not being updated when downstream decisions change is a systemic weakness.

- **BT-018 (Institution Control Type) still not defined.** This was identified as an open issue in the logical model, physical model, and data contract. It remains open.

## Domain Discovery Assessment
### Grade: A
### Rationale

I re-read `governance/domain-context.md` in full (364 lines). My Bronze review graded it A, and the Silver zone has not introduced any domain interpretation errors. The domain context continues to be the most accurate and useful artifact in the governance suite.

Specific validations:

1. The Canonical Concept Map (12 concepts, status PROPOSED) remains appropriate. The Silver zone correctly implements concepts 1-8 (Academic Program, Program Family, Institution, Credential Level, Graduate Earnings 1yr/2yr, Program Debt, Program Size). Concepts 9-12 (Debt-to-Earnings Ratio, Occupation, Institution Type, Earnings Availability) are correctly deferred to Gold/MCP zones.

2. The CIP-to-SOC crosswalk guidance (lines 207-215) is accurate. The many-to-many relationship, the format normalization requirement, and the left-join strategy are all correct. The Gold spec does not yet implement the crosswalk (it is deferred to a future `gold-career-projections` spec), which is the right call for an MVP.

3. The collision resolution rules (lines 250-258) are being followed: ipedscount1 is the primary completions measure, both earnings windows are retained, CIP-per-institution has no collision because the grain handles it.

### Concept Normalization Gate (BLOCKING CHECKLIST)

- [x] `governance/domain-context.md` contains a "Canonical Concept Map" section -- PRESENT at line 181
- [x] The concept map has status CONFIRMED or PROPOSED -- PROPOSED (Unconfirmed), acceptable for Silver-to-Gold transition
- [x] If PROPOSED: the map is reasonable for the identified domain -- YES. 12 concepts, well-scoped for single-source MVP
- [x] The number of target business concepts is appropriate -- 12 concepts is on the low end of the 15-50 range but appropriate for a single-source MVP; the list will grow with BLS/O*NET integration
- [x] Collision resolution rules exist -- PRESENT with 4 scenarios documented
- [x] The silver zone spec includes a concept normalization step -- YES. CIP code normalization (4-digit to XX.XX) is implemented in `normalize_cipcode()`. CIP family derivation uses a static lookup against CIP 2020 taxonomy. Institution control uses CONTROL_MAP. The ConceptNormalizer framework tool is not used (the normalization is done via simple dictionary lookups), but the functional requirement is met.

**Concept Normalization Gate: PASS**

Note: The formal ConceptNormalizer tool from the Brightsmith framework is not used. The normalization is done through `CIP_FAMILIES` and `CONTROL_MAP` dictionaries, which is functionally equivalent for a single-taxonomy dataset. When the CIP-to-SOC crosswalk introduces a second taxonomy and many-to-many mappings, the ConceptNormalizer should be adopted.

## AI-Readiness Assessment
### Grade: B+
### Rationale

The Silver base table is well-positioned for Gold zone consumption. The schema is clean, the grain is stable, and the column names are business-meaningful. An LLM consuming this table via an MCP server could answer questions like "What are the median earnings for Business graduates at Stanford?" directly from the base table.

What works well:

1. **Business-meaningful column names.** `earnings_1yr_median` instead of `earn_mdn_hi_1yr`. `institution_name` instead of `instnm`. `program_name` instead of `cipdesc`. An LLM can interpret these without a data dictionary.

2. **small_cohort_flag as a pre-computed trust indicator.** An MCP tool can filter to `small_cohort_flag = False` for reliable data or include flagged programs with appropriate caveats.

3. **cip_family and cip_family_name for grouping.** The LLM can aggregate by CIP family ("What are the best outcomes in Engineering?") without needing to parse CIP codes.

What needs improvement for Gold/MCP:

1. **52.7% of rows have ALL outcome fields null.** The Gold spec addresses this with `confidence_tier` ("insufficient" for programs with no outcomes) and `has_earnings` / `has_debt` convenience flags. This is the right approach -- carry all rows forward, flag them, and let the query layer filter.

2. **institution_control is 100% NULL.** The Gold spec lists `institution_control` in the output schema. Segmentation by institution type (public vs. private vs. for-profit) is a high-value analysis dimension that the domain context identifies. Until the Bronze re-ingestion adds the CONTROL field, this dimension is unavailable. The Gold spec should explicitly note this limitation.

3. **CIP code format (XX.XX vs XX.XXXX) will cause crosswalk join failures.** The Gold spec's "Future Integration Notes" (lines 236-239) acknowledge this but the current spec does not need to solve it. The first Gold spec (`gold-career-outcomes-college-scorecard`) operates on a single source.

4. **The Gold spec's percentile band design is sound.** Computing cross-institution percentile bands (p25/p50/p75) of program-level medians within each CIP family is a creative use of the available data. The "minimum 3 non-null values per CIP family" threshold for computing bands is reasonable. The spec correctly documents that these are cross-institution percentile bands, not within-cohort percentiles.

## Code Quality Assessment
### Grade: A-
### Rationale

**Transformer (`src/silver/college_scorecard_transformer.py`, 246 lines):**

Clean, single-responsibility design. Three public functions (`get_silver_schema`, `transform_row`, `transform`) plus one helper (`normalize_cipcode`). The `transform_row` function is the core: maps raw dict to Silver dict, returns None for invalid rows. The `transform` function orchestrates read-transform-promote. No god functions.

Specific observations:

- `normalize_cipcode()` handles both 4-digit and already-normalized inputs. Correct defensive programming.
- `CIP_FAMILIES` has all 45 entries (verified via production data: 0 "Unknown" fallback values). The RISK-001 fix from the adversarial audit is confirmed.
- `CONTROL_MAP` handles numeric strings ("1", "2", "3"), text labels ("Public", "Private nonprofit", "Private for-profit"), and the variant "Private not-for-profit". The variant is undocumented in governance artifacts but is a reasonable defensive choice.
- `small_cohort_flag` derivation (`completions_1 is None or completions_1 < 30`) matches the physical model and DQ rule SLV-CS-026. The conservative NULL handling is correct.
- `ingested_at` is generated per-row via `datetime.now()`, meaning rows in a single batch get slightly different timestamps. The staff review noted this as a non-blocking nit. I agree.

**Tests (`tests/silver/test_college_scorecard_transformer.py`, 240 lines, 37 tests):**

The tests are substantive. Boundary value testing for small_cohort_flag (29=True, 30=False). Record ID determinism and uniqueness. NULL handling for all nullable fields. Column renames with specific value assertions. Dropped field verification. CIP normalization edge cases.

Weaknesses (non-blocking):
- No integration test that reads from an actual Iceberg table. All tests are unit-level against `transform_row()`. DQ rules provide integration-level validation.
- No test asserting `len(CIP_FAMILIES) == 45`. If someone removes a family from the dict, no unit test catches it (DQ rule SLV-CS-032 catches it in production).

## Top Risks

1. **institution_control is 100% NULL and the Gold spec depends on it.** The CONTROL field was never added to the Bronze parquet. The Gold spec lists institution_control in its output schema and the domain context identifies institution type segmentation as HIGH VALUE for analysis. **Impact:** Gold zone cannot perform institution-type segmentation. The debt-to-earnings analysis that the domain context recommends ("Do for-profit institutions have worse debt-to-earnings ratios?") is impossible. **Mitigation:** Either re-ingest Bronze with the CONTROL field before Gold implementation, or mark institution_control as explicitly nullable in the Gold spec and defer the segmentation analysis to a follow-up spec.

2. **CIP code format mismatch with CIP-to-SOC crosswalk.** Silver produces XX.XX (e.g., "52.02"). The NCES crosswalk uses XX.XXXX (e.g., "52.0201"). When the crosswalk is ingested for future BLS/O*NET integration, the join will fail without a left-prefix or range-based matching strategy. **Impact:** Blocks future cross-source integration. Does not block current Gold spec. **Mitigation:** The Gold spec correctly defers this to `gold-career-projections`. When the crosswalk is ingested, implement a CIP series-to-detailed-code mapping (one XX.XX maps to multiple XX.XXXX codes).

3. **Documentation drift across 4+ artifacts.** The spec, logical model, glossary, and physical model disagree on small_cohort_flag derivation, CIP code format, grain hash field names, and institution_control derivation. The physical model and code are the source of truth. The staff review documented all issues as LOW severity. **Impact:** A Gold zone developer reading the spec or logical model will get stale information. **Mitigation:** The staff review recommends "fix before Gold zone." This should be tracked as a pre-Gold cleanup task.

## What I'd Cut

- **credential_description in the Gold table.** It is always "Bachelor's Degree" in the MVP. The Gold spec already drops it ("Redundant with credential_level"). Good decision.
- **completions_count_2 in the Gold table.** The Gold spec drops it ("Second-major completions not relevant to career outcomes query pattern. Retained completions_count_1 as completions_count."). Good decision. r=0.984 correlation with completions_count_1 makes it redundant for consumer-facing products.
- **The `earnings_growth_rate` field in the Gold spec.** The domain context explicitly warns that 1yr and 2yr earnings are different cohorts, not longitudinal tracking. Computing (2yr - 1yr) / 1yr and calling it "earnings growth rate" is semantically misleading, even though the Gold spec acknowledges the caveat. A user seeing "earnings_growth_rate = -0.15" will interpret it as "earnings declined" when the real meaning is "the 2yr cohort happened to have lower medians than the 1yr cohort." I would rename it to `cohort_earnings_differential` or drop it entirely and let the MCP layer explain the difference.

## What's Missing for Production

1. **Bronze re-ingestion with CONTROL field.** This is the most impactful missing piece. It is explicitly called out in the EDA (Critical Finding #2), physical model (Open Issue #2), and adversarial audit (RISK-002).
2. **Golden dataset.** The staff review performed spot-checks but a formal golden dataset of 50-100 manually verified records does not exist. The adversarial audit (R-010) and the Gold spec both call for this.
3. **Fix SLV-CS-028.** The raw-to-Silver row count consistency rule has never executed successfully. The table name needs to reference the correct catalog/namespace.
4. **BT-018 (Institution Control Type) business term.** Still pending.
5. **Documentation cleanup.** Spec, logical model, and glossary need to be updated to match the physical model and code.

## What I'd Do Differently

1. **Fix the Bronze re-ingestion before starting Gold.** The CONTROL field was identified as a gap in the EDA before Silver implementation. It should have been fixed before Silver completed, not deferred to Gold. Now it is a known gap that every downstream artifact must account for.
2. **Adopt percentage-based DQ thresholds.** The Bronze review flagged this (Risk #2). The Silver DQ rules improved (null rate thresholds are percentages) but the volume rules still use absolute counts. When the next annual refresh arrives, the volume thresholds may need recalibration.
3. **Use the ConceptNormalizer for CIP family mapping.** The static `CIP_FAMILIES` dict works, but the Brightsmith framework's ConceptNormalizer would provide standardized governance integration (concept versioning, audit trail, collision detection). For a 45-entry lookup, the overhead is not justified in MVP, but for the CIP-to-SOC crosswalk (many-to-many, hundreds of mappings, varying confidence levels), the ConceptNormalizer will be essential.
4. **Rename `earnings_growth_rate` in the Gold spec.** As noted above, this name is misleading given the cohort-window semantics.

## Architectural Proposals for Gold Zone

### 1. Data Product Serving Pattern

**Evidence:** The Gold spec defines a wide table (`consumable.career_outcomes`) with ~30 fields including identity, outcome, percentile bands, financial ratios, relative position, and confidence tiers. The grain remains unitid x cipcode x credlev (same as Silver). The EDA shows 52.7% of rows have all outcome fields null.

**Recommendation: Wide pivoted table (as specified).** The Gold spec's design is correct. A single wide table at the program-offering grain is the right serving pattern for the MCP layer. The confidence tier and has_earnings/has_debt flags provide adequate filtering. A tall time-series format is inappropriate because this is a point-in-time snapshot, not a time series.

**Alternative:** Split into a fact table (outcomes, ratios) and a dimension table (institution, program metadata). This would reduce redundancy but add join complexity for the MCP layer. Not worth it for 69,947 rows.

### 2. Derived Metric Strategy

**Evidence:** The Gold spec defines 10 derived fields: 6 percentile bands (CIP-family window aggregates), debt-to-earnings ratio + tier, earnings growth rate, CIP-family earnings rank, and program value index.

**Recommendation: Precompute all derived metrics in Gold.** The percentile bands are window functions that cannot be efficiently computed per-query in MCP tools. The debt-to-earnings ratio is trivial to compute but precomputing it with a tier bucketing ("Low", "Moderate", "High", "Very High") adds immediate value for the MCP layer. The MCP tools should be thin query wrappers, not computation engines.

**Alternative:** Compute percentile bands in Gold, compute ratios at query time in MCP. This would allow the MCP layer to use different ratio formulas (e.g., monthly payment / monthly earnings instead of total debt / annual earnings). However, for MVP, precomputed is simpler and faster.

### 3. institution_control Handling

**Evidence:** institution_control is 100% NULL. The Gold spec includes it. The domain context identifies it as HIGH VALUE for segmentation.

**Recommendation: Include institution_control as nullable in Gold, with an explicit "DEFERRED" note.** Do not block Gold on the Bronze re-ingestion. Implement the Gold transformer to carry forward NULL gracefully. When the CONTROL field is added to Bronze and Silver is re-run, the Gold transformer should automatically pick up the values without code changes.

**Alternative:** Block Gold until Bronze re-ingestion is complete. This adds the segmentation dimension from day one but delays Gold delivery. For MVP, the nullable approach is better.

## Overall Verdict
### Grade: B+

This Silver zone implementation is production-quality work. The transformer is correct, the DQ coverage is comprehensive, the governance artifacts are substantive, and the adversarial audit's critical finding has been fixed. The data in the Iceberg table matches all expected characteristics: 69,947 rows, zero grain violations, correct CIP normalization, correct small_cohort_flag derivation, earnings and debt values in expected ranges, and a Stanford CS earnings figure ($136,126) that is independently plausible.

The B+ (not A) reflects three things: (1) institution_control is architecturally broken (100% NULL, 4 artifacts disagree, DQ rule masks the gap), (2) documentation drift across 4+ artifacts creates a maintenance burden and a risk of Gold zone developers working from stale information, and (3) the SLV-CS-028 DQ rule has never executed, meaning the Bronze-to-Silver row count consistency has never been automatically verified.

Would I ship this? As a Silver base table, yes -- it does exactly what a base table should do. Would I invest in it? Yes -- the architecture is sound, the domain understanding is deep, and the governance model is proportional. Would I stake my reputation on it? On the data quality and transformation correctness, yes. On the governance artifact consistency, not yet -- the documentation drift needs to be cleaned up before Gold.

**Verdict: APPROVED for Gold zone transition.**

The Gold spec (`gold-career-outcomes-college-scorecard.md`) is well-designed. The percentile band approach is creative and appropriate. The confidence tier system provides the right abstraction for data quality context. The debt-to-earnings ratio is the single most actionable metric for the FutureProof use case. I recommend proceeding with Gold implementation, with the three risks above tracked.

---

## Conditions for Gold Zone Progression

1. **NON-BLOCKING (track as known gap):** institution_control is 100% NULL. Gold spec must explicitly mark it as nullable and note the Bronze re-ingestion dependency.
2. **NON-BLOCKING (recommended):** Clean up documentation drift before Gold implementation begins. Specific files: spec line 78 (small_cohort_flag), glossary BT-003 (CIP format), spec line 36 (grain hash field names).
3. **NON-BLOCKING (recommended):** Fix SLV-CS-028 table name and re-run DQ scorecard.
4. **NON-BLOCKING (recommended):** Consider renaming `earnings_growth_rate` to `cohort_earnings_differential` in the Gold spec to avoid misleading interpretation.
