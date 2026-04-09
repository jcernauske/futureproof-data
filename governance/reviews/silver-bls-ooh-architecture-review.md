# Principal Data Architect Review

**Date:** 2026-04-07
**Reviewer:** @principal-data-architect
**Scope:** Silver zone transition review (Silver to Gold) -- BLS OOH spec
**Domain:** U.S. Labor Market -- Occupation-Level Employment Projections (BLS Employment Projections)
**Spec:** silver-base-bls-ooh
**Prior Review:** governance/reviews/bronze-bls-ooh-architecture-review.md (A-, APPROVED)

## Executive Summary

This is the strongest Silver zone implementation in the pipeline so far. The transformer is 277 lines of clean, single-purpose code that correctly derives 8 fields from Bronze source data, validates SOC codes with fail-fast semantics, and promotes idempotently. 73 tests cover every derivation boundary. 36 DQ rules pass at 100%, and the chaos monkey exercised 22 of them. The golden dataset has 6 independently verifiable values across 3 occupations, all matching. The governance apparatus is proportional and substantive -- not a single governance artifact reads as checkbox compliance. The biggest concern is a data contract documentation error (DQ priority sub-counts sum to 31 instead of the actual 36) that the staff engineer already flagged. The second concern is a stale projection cycle reference ("2023-2033") in the domain context that was flagged in my Bronze review and has not yet been corrected. Neither blocks Gold zone progression.

**Overall: This is ready to proceed to Gold. No blocking issues.**

## Architecture Assessment
### Grade: A
### Rationale

The Silver zone implements exactly the right pattern for this data: read 832 rows from Bronze Iceberg, validate SOC code format, derive classification and bucketing fields, promote idempotently to a single denormalized Silver base table. Every architectural decision is correct.

**Decisions I agree with:**

1. **Single denormalized table.** At 832 rows with a single source and all relationships resolving to 1:1 at the occupation grain, separate dimension tables (SOC major group dim, education requirement dim) would be premature abstraction. The logical model explicitly documents this decision and gives 4 reasons. The pattern matches `base.college_scorecard` which creates consistency across the Silver zone.

2. **Hardcoded broad occupation code list over pattern matching.** The spec explains why (`src/silver/bls_ooh_transformer.py` line 72-73, comment: "Do NOT pattern-match; see spec for rationale"). A frozenset of 7 codes is deterministic and auditable. The alternative -- regex on trailing zeros -- would produce false positives (35-2010 ends in 0 but is a legitimate detailed code). The spec documents this at lines 161-167 with specific examples. This is the kind of decision that shows domain understanding, not just coding ability.

3. **Catchall flag via substring match, not suffix match.** The EDA found 29-1029 "Dentists, all other specialists" has "all other" mid-title. Using `"all other" in occupation_title.lower()` (line 175) correctly catches all 70 cases including this edge case. Using `.endswith("all other")` would miss it.

4. **Growth category as a derived categorical field.** Precomputing the tier in Silver means the Gold zone and MCP tools do not need to implement bucketing logic. The half-open interval boundaries are clean and well-documented. The `derive_growth_category()` function is pure -- no side effects, no state. The 14 boundary tests in the test suite verify every threshold.

5. **Preserving null-wage occupations with a convenience flag.** Dropping 23 null-wage rows would lose physicians, surgeons, and performers -- occupations that students will ask about. The `wage_available` flag lets downstream consumers filter or caveat as appropriate without losing the occupation record.

6. **Grain hash on soc_code only with 'ooh' prefix.** The `compute_grain_id(row, ['soc_code'], prefix='ooh')` call is correct. The prefix prevents collisions with College Scorecard's `cs-` prefixed IDs if tables are ever merged. Deterministic and stable across re-runs.

**What I would note but not change:**

1. **No `projection_cycle` field.** I recommended this in my Bronze review. It is still not present. When BLS releases the next projection cycle (expected 2026), old and new data will be distinguishable only by `source_load_date`, which is a pipeline timestamp, not a business-meaningful vintage indicator. This is acceptable for MVP (single snapshot, full replace on refresh) but should be added when the pipeline handles multiple vintages.

2. **`ingested_at` varies per row within a batch.** Each call to `datetime.now(tz=datetime.timezone.utc)` in the loop (line 210) produces a slightly different timestamp. For 832 rows this is sub-second drift. Functionally irrelevant, but a batch-level timestamp (generated once before the loop) would be cleaner semantically. The staff engineer noted this as a nit, and I agree.

## Data Quality & Trust Assessment
### Grade: A
### Rationale

36 DQ rules, 36 passing, 100% rate. This is the first Silver zone spec to achieve a perfect scorecard on first execution. The rules cover 6 DQ dimensions: uniqueness (2), validity (10), completeness (8), consistency (6), referential integrity (2), coverage (1), plus volume (1) -- though the categories are not labeled in the scorecard.

**What earns the A:**

1. **SLV-OOH-021 is the standout rule.** It validates that every row's `growth_category` matches the exact CASE WHEN bucketing logic from the spec. This is not a generic "value in list" check -- it is a full derivation replay in SQL. With 19 boundary rows (2.3% of data) sitting exactly on threshold values, this rule catches any off-by-one or boundary inclusion error. This is the most valuable DQ rule in the set.

2. **SLV-OOH-032 validates cross-field arithmetic.** `employment_projected - employment_current = employment_change` within +/- 1,000 tolerance accounts for BLS rounding from thousands. The tolerance is neither too tight (would false-alarm on rounding) nor too loose (would miss real corruption). Evidence-backed from EDA.

3. **SLV-OOH-011 correctly uses 70, not 46.** The spec originally said 46 catchall categories. The Silver EDA found 70. The DQ rule writer correctly used the EDA-corrected count. The rationale explicitly documents the correction: "Spec states 46 but EDA counted 70." The spec was also updated (line 43: "corrected from initial estimate of 46 after Silver EDA"). This is the governance process working as designed.

4. **The DQ rule writer tightened the employment_change_pct range bounds.** The spec suggested -100 to +200 (very loose). The DQ rule uses -50 to +60 (tight but with 40% headroom over observed -36.1 to +49.9). This is the right call -- a sanity bound should catch real anomalies, not just validate that the data exists.

5. **The golden dataset is well-constructed.** 6 values across 3 occupations (Software Developers, Registered Nurses, Word Processors/Typists). All 6 have full traceability chains (Bronze source, derivation logic, expected output). The staff review independently verified all 6 against the warehouse. The occupations were chosen to cover different growth categories (growing_fast, growing, declining_fast), different wage profiles, and different domains.

**What prevents an A+:**

1. **Chaos monkey exercised only 22 of 36 rules (61.1%).** 14 rules never fired across 5 cycles. The chaos report's explanations are reasonable ("may check a field/condition not targeted by corruption strategies") but several of the unfired rules are important: SLV-OOH-004 (valid 22 SOC major groups), SLV-OOH-008 (soc_code not null), SLV-OOH-020 (growth_category null iff pct null). These are structural invariants that the chaos monkey's cell-level corruption may not violate (e.g., corrupting a soc_code cell to null might get caught by SLV-OOH-001 or SLV-OOH-002 before SLV-OOH-008). The 61.1% rate is lower than the Bronze zone's 100% (18/18 after targeted follow-up). A targeted follow-up for the Silver zone was not performed.

2. **No SOC code referential integrity check against the SOC 2018 taxonomy.** This was flagged in my Bronze review as a gap. A fake SOC code like "97-4823" with valid XX-XXXX format would pass all current rules. The chaos monkey flagged this too. For Silver, I accept that the Bronze data is the source of truth and it has zero invalid SOC codes -- but when the CIP-SOC crosswalk is introduced, SOC referential integrity becomes critical.

## Governance Assessment
### Grade: A-
### Rationale

The governance apparatus is comprehensive, well-proportioned, and substantive:

- **Models:** Conceptual, logical, physical -- all APPROVED. The physical model at `governance/models/silver-base-bls-ooh-physical.md` is excellent: 434 lines including PyIceberg schema definition, DDL reference, source-to-target mapping, nullability semantics, derivation rules, and DQ rule alignment. This is the most complete physical model artifact in the pipeline.

- **Business glossary:** 20 terms (BT-015 through BT-045 with gaps for shared terms). Includes Silver-specific terms: BT-029/030 (SOC major group code/name), BT-040 (broad occupation flag), BT-041 (growth category), BT-042 (wage available), BT-043 (catchall flag), BT-044/045 (work experience/training codes).

- **DQ rules:** 36 rules with human approval timestamps and evidence chains. Every rule cites the EDA finding that informed its threshold. All approved within a single session.

- **DQ scorecard:** 36/36 from real execution against the persistent warehouse, not ephemeral data.

- **Chaos monkey:** 5-cycle adversarial hardening. Honest about the 61.1% rule activation rate.

- **Lineage:** Full OpenLineage event with column-level derivation descriptions. The runtime metrics confirm 832 rows read, 832 transformed, 832 promoted, 0 skipped.

- **Data contract:** 25 columns documented with types, constraints, CDE flags, PII flags, and descriptions. Quality thresholds specified. Breaking change policy defined.

- **Golden dataset:** 6 values with traceability chains. Stored as structured JSON.

- **Staff review:** Thorough. Independently verified warehouse data, golden dataset, test quality, spec compliance, and idempotent re-run behavior.

**What loses the full A:**

1. **Data contract DQ priority sub-counts are wrong.** The data contract says p0=15, p1=10, p2=6 (sums to 31). Actual is P0=16, P1=20, P2=0 (sums to 36). The total was corrected to 36 but the breakdown was not. The staff engineer flagged this as LOW severity (Issue #1 in the staff review). I agree it is low severity but it demonstrates that the data contract was not verified against the DQ rules JSON after the total was corrected.

2. **Domain context projection cycle still says "2023-2033."** My Bronze review flagged this as a condition for Silver zone progression: "Update domain context BLS section projection cycle from '2023-2033' to '2024-2034.'" The domain context at line 382 still reads: "current cycle: 2023-2033." The spec, data contract, and actual data all say "2024-2034." This is a documentation error inherited from the initial domain context authoring. The Bronze review conditions were labeled "non-blocking but required before Silver DQ rules are authored" -- and the Silver DQ rules were authored without this fix. Not blocking, but the pattern of documentation fixes being deferred rather than applied is concerning. This is now twice-flagged.

3. **Three `education_typical`, `work_experience`, `training_typical` fields have no business glossary terms.** The physical model notes this as Open Issue #1. The coded/normalized versions have terms but the original BLS text labels do not. Minor for downstream consumers who will use the coded versions, but a gap in the glossary.

## Domain Discovery Assessment
### Grade: A
### Rationale

The BLS OOH section of `governance/domain-context.md` (starting at line 369) is thorough and domain-accurate. I validated the following:

1. **SOC taxonomy identification is correct.** SOC 2018 with 832 detailed occupations. The document correctly notes the anticipated SOC 2028 revision as a future change event.

2. **Education/experience/training code orderings are correct in the domain context.** Unlike the Bronze data contract (which had reversed orderings, flagged in my Bronze review), the domain context correctly states 1=Doctoral through 8=No formal for education, 1=5+ years through 3=None for experience, and 1=Internship/residency through 6=None for training.

3. **The entity type identification is precise.** Two primary entities (Occupation keyed by soc_code, SOC Major Group as derived from 2-digit prefix). The entity lifecycle events correctly identify SOC taxonomy revision, occupation addition/removal, and projection cycle changes.

4. **The temporal pattern documentation is accurate.** Biennial snapshot, base year vs. projected year distinction, and the important note that wage data is not projected but is the latest available point estimate.

5. **The cross-source integration narrative is correct.** SOC codes as the bridge to O*NET (direct join) and College Scorecard (via CIP-to-SOC crosswalk). This is the foundational domain knowledge that makes the FutureProof pipeline coherent.

**One stale reference:** The projection cycle reference at line 382 ("current cycle: 2023-2033") contradicts the actual data (2024-2034). This is a documentation error, not a domain understanding error -- the same document's vocabulary section at line 398 also says "2023-2033" for "Projection Cycle." Both need updating.

### Concept Normalization Gate (BLOCKING CHECKLIST)

- [x] `governance/domain-context.md` contains a "Canonical Concept Map" section -- PRESENT at line 181
- [x] The concept map has status CONFIRMED or PROPOSED -- PROPOSED (Unconfirmed), acceptable for Silver-to-Gold transition
- [x] If PROPOSED: the map is reasonable for the identified domain -- YES. 12 concepts, well-scoped for a two-source MVP. Concept #10 (Occupation) maps directly to this BLS OOH data source.
- [x] The number of target business concepts is appropriate -- 12 concepts on the low end of the 15-50 range but growing organically as sources are added. Appropriate.
- [x] Collision resolution rules exist -- PRESENT with 4 scenarios documented including "Multiple SOC codes for one CIP code" resolution
- [x] The silver zone spec includes a concept normalization step -- YES. Growth category derivation (6-tier bucketing), education_level_name lookup (8-value), SOC major group derivation (22-group), broad occupation flag (7-code hardcoded list), catchall flag (substring match). These are concept normalization steps. The ConceptNormalizer framework tool is not used (normalization done via lookup dictionaries and frozensets), which is functionally equivalent for a single-taxonomy dataset.

**Concept Normalization Gate: PASS**

## AI-Readiness Assessment
### Grade: A-
### Rationale

The Silver base table is well-positioned for Gold zone consumption and ultimately for MCP serving. The schema design directly enables the FutureProof use case.

**What works well:**

1. **Column names are business-meaningful.** `median_annual_wage` not `med_ann_wage`. `employment_change_pct` not `emp_chg_pct`. `growth_category` not `grw_cat`. An LLM can interpret these without a dictionary.

2. **The classification flags (`broad_occupation_flag`, `catchall_flag`) are pre-computed trust indicators.** The Gold spec (`gold-occupation-profiles-bls-ooh.md`) correctly plans to use these for confidence tier assignment. An MCP tool can include caveats like "Note: this is a broad occupation category that aggregates multiple detailed roles" when the flag is True.

3. **`growth_category` provides natural language buckets.** An LLM answering "Is software development a growing field?" can use `growth_category = 'growing_fast'` directly in its response without doing arithmetic on `employment_change_pct = 15.8`.

4. **The `education_code` enables education-requirement matching.** The Gold spec plans to compare College Scorecard's credential level against BLS OOH's education requirement. A student studying at a community college (associate's degree) asking about careers that require a bachelor's can be warned about the credential gap. This is only possible because both education taxonomies are now in the pipeline.

5. **`soc_major_group` and `soc_major_group_name` enable occupation-family grouping.** An LLM can aggregate: "The Healthcare Practitioners group has 73 occupations, with a median wage range from $X to $Y." This fallback grouping is valuable when detailed crosswalk matches fail.

**What needs improvement for Gold/MCP:**

1. **23 null-wage occupations include high-profile careers.** Physicians, surgeons, and performers are exactly the occupations students will ask about. The Silver table correctly preserves them with `wage_available = False`, but the Gold zone must have a strategy. The Gold spec (`gold-occupation-profiles-bls-ooh.md`) addresses this with confidence tiers, which is correct.

2. **No wage trajectory data.** The BLS OOH provides only a single median wage point. The "Ceiling boss fight" concept in the FutureProof spec requires wage progression data (entry-level vs. experienced). This table provides the entry-level anchor but the progression data would need a separate source (BLS experience-level OES data). The spec correctly documents this as a limitation at line 239.

3. **The CIP-to-SOC crosswalk does not exist yet.** Without it, this table is a standalone occupation reference. The Gold spec for occupation profiles (`gold-occupation-profiles-bls-ooh.md`) is designed to be self-contained (queryable by SOC code directly), which is the right approach -- it does not depend on the crosswalk. The crosswalk is a future spec that will enable the full school+major-to-career pipeline.

## Code Quality Assessment
### Grade: A
### Rationale

**Transformer (`src/silver/bls_ooh_transformer.py`, 277 lines):**

Clean, well-structured code. Four public functions (`get_silver_schema`, `derive_growth_category`, `transform_row`, `transform`) plus module-level constants. No god functions. No unnecessary abstractions.

Specific observations:

- `derive_growth_category()` is a pure function with explicit half-open interval logic. The chain of `if` statements (lines 133-145) reads linearly from the most negative bucket to the most positive. No ELIF confusion, no overlapping conditions.

- `transform_row()` follows a clear pattern: validate input, derive fields, assemble record dict, compute grain hash. The function raises `ValueError` for invalid SOC codes and unknown major groups -- fail-fast, no silent corruption. The staff engineer noted one inconsistency: null `occupation_title` is silently coerced to empty string (lines 163-165) rather than raising `ValueError`. Since DQ rule SLV-OOH-009 catches empty titles post-hoc and current data has zero null titles, this is non-blocking.

- `transform()` orchestrates read-transform-promote in 50 lines with clear logging at each stage. The return dict provides metrics (rows_read, rows_transformed, promoted, skipped_dedup, snapshot_id) useful for lineage and monitoring.

- Lookup tables (`SOC_MAJOR_GROUP_LOOKUP`, `EDUCATION_LEVEL_LOOKUP`, `BROAD_OCCUPATION_CODES`) are defined at module scope as constants. `BROAD_OCCUPATION_CODES` uses `frozenset`, which is correct for a fixed membership test (O(1) lookup, immutable). All 22 SOC major groups and all 8 education levels are present.

- The schema definition (`get_silver_schema()`, lines 90-118) matches the physical model exactly -- 25 fields, correct types, correct nullability.

**Tests (`tests/silver/test_bls_ooh_transformer.py`, 463 lines, 73 tests):**

The tests are real. Specific highlights:

- **Growth category boundary tests (14 tests):** Every threshold is tested with exact boundary values. `-10.0 -> declining` (not declining_fast). `-1.0 -> stable` (not declining). `1.0 -> growing` (not stable). `10.0 -> growing_fast` (not growing). `20.0 -> booming` (not growing_fast). Plus interior values and null. This is textbook boundary value testing.

- **Broad occupation flag (4 tests):** Parametrized test for all 7 codes, exact count assertion (`len(BROAD_OCCUPATION_CODES) == 7`), negative test for regular code, and false-positive test for code ending in 0 that is not broad (35-2010). Thorough.

- **Education level name (9 tests):** Parametrized across all 8 codes with expected name assertions, plus null education_code handling.

- **Validation (5 tests):** Missing, null, empty, invalid format, and alpha SOC codes all tested with specific ValueError message assertions.

- **Schema tests (3 tests):** Field count (25), required fields (set equality with `issubset`), nullable fields (set equality with `==`). The nullable test uses `==` not `issubset`, meaning any extra or missing nullable field would fail.

- **Test fixture data is synthetic, not production.** Software Developers fixture uses $130,160 wage vs $133,080 actual. This is intentional and acceptable -- unit tests validate transformation logic, the golden dataset validates end-to-end correctness.

**Minor weakness:** The schema required fields test uses `issubset` (line 448) while the nullable fields test uses `==` (line 462). The `issubset` check would pass even if additional required fields were added without updating the test. For consistency, the required fields test should also use `==`. Non-blocking.

## Top Risks

1. **Domain context projection cycle is stale ("2023-2033" vs "2024-2034").** This was flagged in my Bronze review and has not been fixed. If the Gold zone agents reference the domain context as authoritative, they will apply the wrong vintage label. **Impact:** Misleading data vintage labels in Gold zone products and MCP grounding documents. **Mitigation:** Update `governance/domain-context.md` lines 382, 398, and 447 from "2023-2033" to "2024-2034". Five-minute fix.

2. **Data contract DQ priority sub-counts are incorrect.** The contract says p0=15, p1=10, p2=6 (total=31 when summed). Actual is P0=16, P1=20, P2=0 (total=36). **Impact:** Any agent or consumer reading the data contract for DQ coverage understanding will get wrong numbers. Low severity since the DQ rules JSON and scorecard are the authoritative sources. **Mitigation:** Fix the three numbers in `governance/data-contracts/base-bls-ooh.yaml` lines 428-430 to p0_rules: 16, p1_rules: 20, p2_rules: 0.

3. **No SOC referential integrity against the SOC 2018 taxonomy.** A fabricated SOC code with valid XX-XXXX format would pass all current validation. This is acceptable for the current single-source Silver table (Bronze data has 100% valid codes), but when the CIP-SOC crosswalk is introduced, invalid SOC codes would create orphan joins. **Impact:** Currently zero (no invalid codes exist). Future risk when crosswalk is added. **Mitigation:** Import a SOC 2018 reference list as a dimension table in the crosswalk spec and validate referential integrity at that point.

## What I'd Cut

Nothing. This is a lean implementation. 25 fields, 8 derived, 277 lines of code, zero dead code. The physical model is the most detailed artifact at 434 lines, but every section serves a purpose (the source-to-target mapping and derivation rules tables are essential for Gold zone developers). The only candidate for cutting would be `median_wage_capped` (currently all-False), but the spec correctly argues for preserving it as a defensive measure against future data source changes.

## What's Missing for Production

1. **Fix the domain context projection cycle.** This is now a twice-flagged documentation error. It must be corrected before Gold zone agents begin referencing the domain context.

2. **Fix the data contract DQ sub-counts.** Quick fix: p0=16, p1=20, p2=0.

3. **SOC 2018 reference table.** Needed when the CIP-SOC crosswalk spec is authored. Not needed for the immediate Gold zone spec.

4. **Business glossary terms for education_typical, work_experience, and training_typical.** Minor gap -- the coded/normalized versions have terms, but the raw label fields do not.

5. **Targeted chaos monkey follow-up.** The Bronze zone achieved 100% rule activation via a targeted follow-up run. The Silver zone stopped at 61.1%. The 14 unfired rules should be specifically targeted to verify they can fire under the right corruption conditions.

## What I'd Do Differently

1. **Fix the Bronze review conditions before starting Silver.** My Bronze review listed two conditions: (a) fix data contract code descriptions, (b) fix domain context projection cycle. The data contract code descriptions were fixed (I verified the Silver DQ rules have correct code orderings). The domain context was not fixed. Deferring review conditions creates a pattern where documentation drift accumulates across zone transitions.

2. **Add a `projection_cycle` string field** (e.g., "2024-2034"). This was recommended in my Bronze review and is still absent. A single point-in-time snapshot is fine for MVP, but the next BLS release will require distinguishing old data from new. Adding the field now (with a constant value for all 832 rows) costs nothing and enables future temporal modeling without a schema change.

3. **Use batch-level `ingested_at` timestamp.** Generate `datetime.now(tz=datetime.timezone.utc)` once before the transform loop and assign the same value to all 832 rows. Sub-second drift is functionally irrelevant but per-row timestamps imply granularity that does not exist.

## Architectural Proposals for Gold Zone

### 1. Data Product Serving Pattern

**Evidence:** The Gold spec (`gold-occupation-profiles-bls-ooh.md`) defines a single-source data product at the same grain as Silver (soc_code, 832 rows). It adds GRW score (1-10 scale), wage percentile rank within education tier, and confidence tier. The table is designed to be self-contained and queryable by SOC code without the crosswalk.

**Recommendation: Single wide table (as specified).** The Gold spec's design is correct. 832 rows at the occupation grain with derived scoring fields is the right shape for MCP serving. The occupation profiles table is a reference dataset, not a fact table -- wide and complete is appropriate.

**Alternative:** A tall format with one row per occupation per metric would enable generic "get_stat(soc_code, stat_name)" MCP tools. This adds join complexity for no benefit at 832 rows.

### 2. Derived Metric Strategy

**Evidence:** The Gold spec defines GRW score (normalized 1-10), wage percentile rank (within education tier and overall), and occupation confidence tier. All are deterministic derivations from Silver fields.

**Recommendation: Precompute all derived metrics in Gold.** The percentile rank is a window function that cannot be computed efficiently at query time in MCP tools. The GRW score normalization is trivial but should be precomputed for consistency. The confidence tier logic (based on broad_occupation_flag, catchall_flag, wage_available, and employment size) is multi-factor and should not be reimplemented in every MCP tool.

## Overall Verdict
### Grade: A-

This is production-quality work. The transformer is correct, the DQ coverage is comprehensive, the governance artifacts are substantive, and the domain understanding is deep. 73 tests with meaningful assertions for a 277-line transformer is excellent coverage density. The golden dataset verifies end-to-end correctness across three representative occupations. The staff review independently confirmed all metrics match. Idempotent promote verified (re-run: 0 promoted, 832 skipped).

The A- (not a full A) reflects two things: (1) the domain context projection cycle error that was flagged in my Bronze review and has not been corrected -- this is a process gap, not a code quality issue, but it means a known documentation error has persisted across two zone transitions, and (2) the data contract DQ sub-count error, which is a minor documentation issue but demonstrates that the data contract was not cross-validated against the DQ rules JSON after the total was corrected.

Would I ship this? As a Silver base table, without hesitation. Would I invest in it? Yes -- the architecture is sound, the SOC code handling is domain-correct, and the classification flags (broad occupation, catchall) show the kind of domain knowledge that prevents downstream integration failures. Would I stake my reputation on it? On the data quality and transformation correctness, yes. On the governance artifact accuracy, yes with the two documentation fixes noted above.

**Verdict: APPROVED for Gold zone transition.**

The Gold spec (`gold-occupation-profiles-bls-ooh.md`) is well-designed. The GRW score normalization to a 1-10 scale is appropriate for the FutureProof stat system. The wage percentile rank within education tier provides meaningful context (comparing a bachelor's-required occupation against other bachelor's-required occupations, not against the full population). The confidence tier system correctly uses the broad_occupation_flag and catchall_flag as signal quality indicators.

---

## Conditions for Gold Zone Progression

1. **NON-BLOCKING (recommended, twice-flagged):** Fix domain context projection cycle from "2023-2033" to "2024-2034" at lines 382, 398, and 447 of `governance/domain-context.md`.
2. **NON-BLOCKING (recommended):** Fix data contract DQ sub-counts at `governance/data-contracts/base-bls-ooh.yaml` lines 428-430: change p0_rules to 16, p1_rules to 20, p2_rules to 0.
3. **NON-BLOCKING (minor):** Add business glossary terms for education_typical, work_experience, and training_typical if these fields are consumed by the Gold zone.

---

## Comparison with College Scorecard Silver Review

The BLS OOH Silver implementation addresses several weaknesses I identified in the College Scorecard Silver review:

| Dimension | College Scorecard Silver | BLS OOH Silver |
|-----------|------------------------|----------------|
| DQ scorecard | 34/35 (SLV-CS-028 never executed) | 36/36 (100%) |
| Documentation drift | 4+ artifacts disagreeing | 2 known issues (both minor) |
| Golden dataset | No formal golden dataset | 6-value golden dataset with traceability |
| Known data gaps | institution_control 100% NULL | No equivalent gap |
| Overall grade | B+ | A- |

The improvement is clear evidence that the team is learning across spec iterations. The governance process is maturing.
