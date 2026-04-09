# Principal Data Architect Review

**Date:** 2026-04-08
**Reviewer:** @principal-data-architect
**Scope:** Bronze zone transition review -- all 3 raw sources (College Scorecard, BLS OOH, O*NET)
**Domain:** Education / Career Guidance (Higher Education Outcomes)
**Supersedes:** Previous single-source review dated 2026-04-06 (College Scorecard only)

## Executive Summary

This is a strong Bronze zone implementation across three fundamentally different data sources -- a 500MB government CSV, a BLS XLSX with fuzzy headers, and a multi-file O*NET ZIP archive with 5 tables and 6 scale types. The ingestors are well-crafted, consistently patterned, and handle source-specific complexity without over-engineering. The domain context document is exceptional -- at 1,100+ lines it correctly identifies every material data characteristic, edge case, and cross-source integration requirement. DQ coverage is comprehensive (76 rules across 3 sources, 74/76 passing, 2 explained). The biggest strength is the governance-first approach: every rule is evidence-backed from EDA, every decision is documented with rationale. The biggest concern is that the concept normalization gate remains PROPOSED across all three concept maps, and the CIP-to-SOC crosswalk -- the single most critical Silver zone dependency -- has not been ingested as a raw reference table. This must be addressed before Silver zone work begins.

**Overall: Ready to proceed to Silver, with one BLOCKING condition (crosswalk ingestion) and several recommendations.**

## Architecture Assessment
### Grade: A-
### Rationale

The 4-zone architecture is well-suited for this use case. Three government data sources with different formats, taxonomies, and grains need to be unified into a career guidance product. Bronze as a faithful capture layer, Silver for normalization and cross-source bridging, Gold for pre-computed analytics, MCP for AI serving -- each zone has a clear purpose.

Specific decisions I endorse:

1. **O*NET inheritance-based ingestor pattern.** `OnetBaseIngestor` handles ZIP download/cache/TSV parsing; 5 thin subclasses define schemas and flatten methods. This is textbook Bronze zone design -- shared infrastructure, source-specific coercion. The code in `src/raw/onet_ingestor.py` is 500 lines for 5 tables. Clean.

2. **BLS fuzzy header matching.** The BLS XLSX changes column headers between projection cycles ("Employment 2024" vs "Employment, 2023"). The `_HEADER_PATTERNS` approach with ordered substring matching is pragmatic and well-documented. It will survive the next BLS projection cycle without code changes.

3. **Employment "in thousands" conversion at ingest.** Converting BLS employment figures from thousands to actuals at the Bronze layer means Silver and Gold never deal with unit ambiguity. The +/- 1000 rounding tolerance in DQ rule RAW-OOH-018 correctly accounts for the conversion artifact.

4. **O*NET SOC code preserved as XX-XXXX.XX.** Keeping the full 8-character format in Bronze and deriving the 6-character BLS SOC in Silver is the right approach. The `.00` suffix is semantically meaningful (base vs. detailed occupation).

5. **Wage top-code detection in BLS ingestor.** The `_parse_wage` method correctly handles ">=239,200", "$239,200 or more", and N/A patterns, returning a `(value, is_capped)` tuple. The `median_wage_capped` boolean in the schema is a first-class data quality signal, not an afterthought.

What concerns me:

1. **CIP-to-SOC crosswalk is not ingested.** The domain context document identifies this as a "CRITICAL DEPENDENCY" for Silver zone (lines 154, 211-218). The manifest.yaml does not include it as a source. The Silver specs reference it. But no ingestor exists, no DQ rules cover it, and no data exists for it. This is the single biggest risk to the pipeline. Without the crosswalk, the central FutureProof question ("If I study X at school Y, what career outcomes can I expect?") cannot be answered.

2. **manifest.yaml is stale.** It shows College Scorecard as "scaffolded" and BLS/O*NET as "draft" despite all three being COMPLETE. The Silver and Gold pipeline entries exist but don't reflect O*NET. This is a documentation debt, not a technical blocker.

3. **BLS download fallback is fragile.** `BlsOohIngestor._download_and_read()` catches all exceptions and falls back to a local file at `data/raw/xlsx_cache/bls_ooh.xlsx`. In production, a download failure should be surfaced, not silently absorbed by a potentially stale cache file. The O*NET ingestor has the same pattern. Both should log at WARNING level (they do) but also surface an explicit "using cached data" flag in lineage metadata.

4. **No CONTROL column decoding in College Scorecard.** The raw `control` field stores integers (1/2/3) from the source CSV. The domain context maps these to "Public/Private nonprofit/Private for-profit" but no code in the Bronze layer documents or validates this mapping. Silver zone handles it (per the README models), but a DQ rule for valid CONTROL values (1, 2, or 3) is missing from the raw DQ rules.

## Data Quality & Trust Assessment
### Grade: A-
### Rationale

76 DQ rules across 3 sources. College Scorecard: 18 rules, 18/18 passing. BLS OOH: 18 rules, 16/17 executable passing (1 deferred, 1 calibration failure explained). O*NET: 40 rules, 40/40 passing. Total passing rate: 74/75 executable = 98.7%.

What earns the A-:

- **DQ rules are evidence-backed, not template-generated.** Every rule references specific EDA findings. The thresholds are derived from observed data distributions with documented headroom rationale. This is how DQ rules should be written.

- **The O*NET cross-table referential integrity rules (RAW-ONET-012, -020, -029, -037, -038) are excellent.** They verify that every SOC code in child tables exists in the occupation master table. This catches orphan records that would silently produce null joins in Silver.

- **The BLS RAW-OOH-013 failure is correctly diagnosed.** 4 niche occupations (Patternmakers wood, Pediatric surgeons, Prosthodontists, Timing device assemblers) have zero openings due to BLS rounding from thousands. The scorecard correctly identifies this as a rule calibration issue, not a data integrity problem. The rule should be amended to `>= 0`.

- **The "non-rules" are as important as the rules.** No completeness rule for md_earn_wne (100% null by design). No anomaly rule for 2yr < 1yr earnings (44.2% expected). No rejection rule for O*NET survey dates from 2004. These demonstrate genuine domain understanding.

What is missing:

- **No DQ rule for CONTROL values** in College Scorecard (should be 1, 2, or 3).
- **No chaos monkey results documented for BLS OOH or O*NET.** College Scorecard was hardened through 5 chaos monkey cycles. Were the other two sources tested similarly? If not, the DQ rules are unproven against corruption.
- **Freshness rules use 30-day windows** which will fail in any non-daily-refresh scenario. The College Scorecard is refreshed annually, BLS OOH biennially. These freshness rules will be perpetually failing after 30 days unless the pipeline runs monthly. Consider widening to 400 days (annual + buffer) for College Scorecard and 900 days (biennial + buffer) for BLS OOH, as the domain context itself recommends.

## Governance Assessment
### Grade: A
### Rationale

The governance model is right-sized for the data's criticality. This is public federal data with no PII and no regulatory restrictions beyond attribution. The governance artifacts are:

- **Domain context:** 1,100+ lines across 3 data sources, with concept maps, entity types, temporal patterns, regulatory context, PII assessment, collision resolution rules, cross-source integration documentation, and unanswered interview questions. This is one of the most thorough domain context documents I have reviewed for a Bronze zone. It correctly identifies its own confidence levels.

- **Business glossary:** 26 terms, well-defined, with source references and approval status. Covers all key domain concepts.

- **Data contracts:** 11 contracts across raw tables, with CDE tagging, PII flags, and column-level descriptions. The CDE rationale for College Scorecard `cipcode` correctly identifies it as the foundation for the CIP-to-SOC crosswalk.

- **Lineage:** OpenLineage-format JSON events with run IDs, row counts, agent attribution, and input/output facets. Proper provenance chain.

- **DQ rules:** 76 rules in structured JSON with rule IDs, dimensions, priorities, SQL, thresholds, evidence, and approval status. All human-approved.

- **DQ scorecards:** Structured reports with per-rule results, investigation notes for failures, and gate status assessment.

This is not over-governed. Every artifact earns its place. A regulator or auditor would find this credible.

## Domain Discovery Assessment
### Grade: A
### Rationale

The domain context document (`governance/domain-context.md`) is accurate and comprehensive. Specific validations:

1. **Domain identification is correct.** Higher Education Outcomes / Program-Level Career Outcomes. The sub-domains for BLS OOH (U.S. Labor Market -- Occupation-Level Employment Projections) and O*NET (U.S. Occupational Information -- Task-Level Work Analysis) are precisely scoped.

2. **Grain definitions are correct.** College Scorecard: unitid x cipcode x credlev. BLS OOH: soc_code. O*NET: varies by table (onet_soc_code for occupations, onet_soc_code x task_id for tasks, onet_soc_code x element_id x scale_id for activities/context, onet_soc_code x related_onet_soc_code for relationships). All verified against actual data.

3. **The 1yr/2yr earnings interpretation is correct and critically important.** The document correctly identifies that these are different cohort measurement windows, NOT longitudinal tracking. This is the single most common misinterpretation of College Scorecard data and would poison every downstream analysis if misunderstood.

4. **The O*NET scale type system documentation is excellent.** 6 scale types (IM, LV, CX, CXP, CT, CTP) with ranges, row counts, and usage guidance. This is essential for Silver zone agents who need to correctly pivot or aggregate O*NET data.

5. **The Career Changers/Starters gap is correctly identified and mitigated.** The document recommends Related Occupations as the fallback with a clear explanation of the semantic difference (similarity vs. transitions).

6. **Cross-source SOC code bridging is well-documented.** The format comparison table (O*NET XX-XXXX.XX vs BLS XX-XXXX), the 76 split cases, the aggregation strategy for non-.00 suffixes -- this is the kind of integration documentation that prevents Silver zone disasters.

Minor issues:

- The domain context notes a potential BLS education code mapping discrepancy (code 3 = "High school diploma" observed in EDA vs. BLS documentation saying "Some college, no degree"). The full dataset validation in the DQ scorecard confirms all 8 codes are present and the `_EDUCATION_CODE_MAP` in the ingestor correctly maps code 3 to "Bachelor's degree". This appears to be a documentation artifact from the 10-row sample EDA where the sample happened to pair code 3 with a misleading label. Not a real issue.

## Concept Normalization Gate (BLOCKING ASSESSMENT)

- [x] `governance/domain-context.md` contains a "Canonical Concept Map" section -- YES, three separate concept maps (College Scorecard: 12 concepts, BLS OOH: 12 concepts, O*NET: 13 concepts)
- [x] The concept maps have status PROPOSED -- YES, all three are "PROPOSED (Unconfirmed)"
- [x] PROPOSED maps are reasonable for the identified domain -- YES, I validate these based on my knowledge of U.S. education/labor data
- [x] Number of target business concepts is appropriate -- YES, 37 total across 3 sources (12 + 12 + 13). Reasonable for a multi-source domain with cross-source integration requirements.
- [x] Collision resolution rules exist -- YES, documented for all three sources with clear rationale
- [ ] Silver zone specs include concept normalization steps -- PARTIALLY. The Silver specs for College Scorecard and BLS OOH exist and are marked COMPLETE. The O*NET Silver spec does not yet exist.

**Gate Assessment: PASS with conditions.** The concept maps are well-constructed and I agree with the proposed concepts. The 37-concept target is in the right range (not oversimplified, not over-normalized). The collision resolution rules are sensible. The Silver zone MUST use these concept maps for normalization.

**BLOCKING CONDITION:** The CIP-to-SOC crosswalk must be ingested as a reference table before Silver zone cross-source integration can proceed. This is not a concept normalization issue per se, but it is the physical realization of the most important concept mapping (Concept #10 "Occupation" in the College Scorecard concept map). Without the crosswalk data, the concept map is aspirational.

## AI-Readiness Assessment
### Grade: B+
### Rationale

The Bronze zone has the right data for AI career guidance. The three sources together enable the core FutureProof question chain:

1. "What outcomes do graduates of [program] at [school] experience?" -- College Scorecard
2. "What occupations can [program] graduates enter?" -- CIP-to-SOC crosswalk (not yet ingested)
3. "What does [occupation] pay and is it growing?" -- BLS OOH
4. "What tasks does [occupation] involve and how exposed are they to AI?" -- O*NET

The governance metadata (domain context, glossary, contracts) is rich enough to ground an LLM. The AI-Ready Considerations sections in the domain context document provide specific guidance for MCP server design.

What holds it back from an A:

- The crosswalk gap means the chain is broken at step 2.
- No O*NET Silver spec exists yet, so the task-level and activity-level data is not yet query-ready.
- The domain context correctly identifies that 52.7% of College Scorecard rows have ALL outcome fields null (privacy suppression). The MCP server must handle "no data available for this program" gracefully -- this is not documented as a design requirement yet.

## Code Quality Assessment
### Grade: A-
### Rationale

All 3 ingestors follow the same `BaseIngestor` pattern: `fetch()` acquires data, `flatten()` coerces types, `get_schema()` defines Iceberg schema. Consistent, readable, well-documented.

Specific observations:

1. **163 tests, all passing.** Test coverage is thorough: schema validation, constant verification, fetch behavior, flatten coercion, edge cases, golden dataset assertions (real O*NET values verified), full-dataset integration tests (BLS OOH). The O*NET golden dataset tests (verifying CEO task 8823 has "financial or budget activities" text, Getting Information IM = 4.56, CXP categories sum to 100%) are the strongest evidence that the ingestors are correctly mapping source data.

2. **One lint violation:** unused `pytest` import in `tests/raw/test_college_scorecard_ingestor.py`. Trivial.

3. **The O*NET `_parse_tsv` method handles BOM correctly.** Small detail, but BOM handling in government data files has bitten many pipelines.

4. **Type coercion is defensive throughout.** Every `_coerce_*` method handles None, empty string, whitespace, and invalid values. Returns None rather than raising. This is correct for Bronze zone -- fail silently, let DQ rules catch problems.

5. **The `__new__` test pattern is a pragmatic workaround.** Tests use `IngestorClass.__new__(IngestorClass)` to skip `BaseIngestor.__init__` which requires framework config objects. This is brittle but works for unit testing. Consider providing a `create_for_test()` classmethod in the framework.

6. **No retry logic on HTTP downloads.** All three ingestors make single HTTP requests with no retry. Government APIs are unreliable. A simple 3-retry-with-backoff wrapper would improve production reliability.

## Top Risks

1. **CIP-to-SOC crosswalk not ingested.** Impact: Silver zone cross-source integration is impossible. The entire value proposition of FutureProof (program-to-career mapping) depends on this reference table. Mitigation: Add a raw-ingest spec for the NCES CIP-to-SOC crosswalk before Silver work begins. This is a small table (~15K rows) and a simple ingestor.

2. **O*NET Silver spec does not exist.** Impact: O*NET data sits in Bronze with no path to Silver. 5 tables with ~390K total rows and complex scale semantics need careful Silver zone modeling. Mitigation: Write the O*NET Silver spec before proceeding. The domain context document provides extensive guidance for the transformation design.

3. **DQ freshness rules will fail within 30 days.** Impact: Every subsequent DQ run will show P1 failures on freshness rules, creating alert fatigue and eroding trust in the DQ framework. Mitigation: Align freshness rule windows with actual source update cadences (annual for College Scorecard, biennial for BLS OOH, quarterly for O*NET).

## What I Would Cut

- **Nothing.** This is not over-engineered. Every ingestor, every test, every governance artifact earns its place. The O*NET ingestor pattern (shared base + thin subclasses) is particularly efficient. If anything, the governance artifacts are more thorough than strictly necessary for a hackathon, but I would rather have too much documentation than too little.

## What Is Missing for Production

1. **CIP-to-SOC crosswalk ingestion** (blocking)
2. **HTTP retry logic** on all three ingestors
3. **Chaos monkey hardening** for BLS OOH and O*NET DQ rules (College Scorecard was done; other two appear untested)
4. **CONTROL column DQ rule** for College Scorecard (valid values 1/2/3)
5. **Freshness rule calibration** to match actual source update cadences
6. **Integration test** that verifies all three raw tables can be queried together from the catalog
7. **manifest.yaml update** to reflect actual source statuses

## What I Would Do Differently

If starting over with the same requirements, I would:

1. **Ingest the CIP-to-SOC crosswalk in the first Bronze sprint**, not defer it. It is small, simple, and unlocks the entire Silver zone. Deferring it creates a dependency bottleneck.

2. **Use a shared HTTP client with retry/backoff** from the start, rather than raw `requests.get()` in each ingestor.

3. **Define the O*NET Silver zone model before ingesting O*NET.** The Work Context 6x row count surprise (297K vs 49K estimated) would have been caught at design time if the scale type system had been fully understood before the spec was written. The EDA caught it, but earlier discovery would have saved spec revision churn.

Otherwise, the architecture is sound and the execution quality is high. This team clearly understands the data.

## Interactive Architectural Proposals (Bronze to Silver Transition)

### 1. Dimensional Model Design

**Evidence:** College Scorecard has a clear star-schema grain (unitid x cipcode x credlev) with measure columns. BLS OOH is a simple dimension table (soc_code grain). O*NET has 5 tables at different grains: occupation (1K rows), tasks (19K rows), activities (73K rows), context (298K rows), relationships (18K rows).

**Recommendation (default):** Denormalized flat tables per source in Silver, with cross-source joining deferred to Gold zone. Reasons: (a) the sources have fundamentally different grains, (b) pre-joining in Silver would create massive fan-out (69K x ~5 SOC codes per CIP x ~20 tasks per SOC), (c) Silver should focus on cleaning and normalizing, not reshaping.

**Alternative:** Star schema with shared dimension tables (institution dim, program dim, occupation dim) and fact tables. More normalized, more complex, harder to evolve.

### 2. Normalization Aggressiveness

**Evidence:** 37 canonical concepts proposed across 3 sources. CIP taxonomy has 390 codes in 34 families. SOC taxonomy has ~832 detailed codes in 23 major groups. O*NET has 41 work activities and 57 work context elements.

**Recommendation (default):** Normalize classification codes (CIP format XX.XXXX, SOC as-is, O*NET-SOC preserved full + truncated for bridging). Normalize string enumerations to codes (BLS education/experience/training -- already done in Bronze). Do NOT attempt semantic normalization of work activities or task descriptions -- leave that for Gold/MCP zone AI processing.

### 3. Entity Resolution Strategy

**Evidence:** All three sources use federal standard identifiers (UNITID, SOC, O*NET-SOC, CIP). No name-based matching is needed. The only resolution complexity is the O*NET-to-BLS SOC 1:N mapping (76 BLS SOCs split across 149 O*NET detailed codes).

**Recommendation (default):** Skip entity resolution. Use ID-based joins exclusively. For the 76 O*NET split cases, aggregate O*NET ratings to BLS SOC level using simple averages. Document aggregation in lineage.

## Overall Verdict
### Grade: A-

This Bronze zone implementation is ready for Silver progression. The code is clean, the tests are thorough, the governance is proportional and honest, and the domain understanding is deep. The A- rather than A reflects two gaps: the missing CIP-to-SOC crosswalk (which should have been ingested alongside the three primary sources) and the absence of an O*NET Silver spec.

Would I ship this? Yes, with the crosswalk blocker resolved.
Would I invest in it? Yes. The governance-first approach and multi-source integration design show architectural maturity.
Would I stake my reputation on it? On the Bronze zone, yes. The data is faithfully captured, correctly typed, and well-governed. The Silver zone will determine whether the integration promise is delivered.

### Blocking Conditions for Silver Progression

1. **MUST** ingest the NCES CIP-to-SOC crosswalk as a raw reference table before Silver zone cross-source integration specs are written.
2. **MUST** amend BLS OOH rule RAW-OOH-013 threshold from `> 0` to `>= 0` to clear the P0 gate.

### Recommended (Non-Blocking) Improvements

1. Calibrate freshness rules to actual source update cadences
2. Add CONTROL column DQ rule for College Scorecard
3. Run chaos monkey on BLS OOH and O*NET DQ rule sets
4. Update manifest.yaml to reflect actual statuses
5. Add HTTP retry logic to all ingestors
6. Fix unused `pytest` import lint violation
