# Principal Data Architect Review

**Date:** 2026-04-07
**Reviewer:** @principal-data-architect
**Scope:** Bronze zone transition review (Bronze to Silver) -- BLS OOH spec
**Domain:** U.S. Labor Market -- Occupation-Level Employment Projections (BLS Employment Projections / OOH)
**Spec:** raw-ingest-bls-ooh

## Executive Summary

This is a strong Bronze zone implementation -- cleaner and more complete than the College Scorecard ingestion that preceded it, benefiting from lessons learned on the first spec. The ingestor correctly acquires 832 detailed occupations from a BLS XLSX export, handles the three hardest parsing problems (employment-in-thousands conversion, top-coded wage detection, flexible header matching across BLS format changes), and lands data with 100% SOC code format validity and zero duplicates. The EDA is thorough and evidence-based, the DQ rules are well-calibrated against real data, and the chaos monkey achieved 18/18 rule coverage. The biggest concern is a documentation error in the data contract that reverses the education, experience, and training code orderings -- anyone reading the contract would misinterpret these fields. The second concern is that the domain context says "2023-2033" projection cycle while the spec and ingestor say "2024-2034" -- a factual inconsistency that must be resolved before Silver.

**Overall: READY to proceed to Silver, with two documentation fixes required (non-blocking but must be addressed before Silver DQ rules reference these codes).**

## Architecture Assessment
### Grade: A-
### Rationale

The Bronze zone is the right place for this data and the implementation is architecturally sound.

**Decisions I agree with:**

1. **XLSX parsing via openpyxl in read_only mode.** Correct choice -- BLS EP data is distributed as XLSX, not CSV. The `read_only=True` flag prevents loading the entire workbook into memory. For a ~1MB file this does not matter much, but it is good practice and shows awareness of the library's memory model.

2. **Flexible header matching via `_HEADER_PATTERNS`.** This is the single best architectural decision in the ingestor. BLS changes column headers every projection cycle (e.g., "Employment, 2023" becomes "Employment, 2024"). The substring-based fuzzy matching with first-match-wins priority is resilient to these changes without requiring code updates. The staff engineer correctly praised this.

3. **Summary row filtering in `_read_xlsx` (fetch), not in `flatten`.** Filtering aggregate rows (XX-0000) at the earliest possible point prevents them from polluting any downstream logic. The ingestor removes them before they even reach the flatten stage. This is the right boundary.

4. **Education/experience/training code derivation from labels.** The `_derive_code()` method handles both BLS formats: the interactive export (labels only, no code columns) and the static EP tables (which include code columns). This dual-path approach means the ingestor works regardless of which BLS format the user downloads. Code column takes precedence when present, label lookup is the fallback.

5. **Wage parsing with capping detection.** The `_parse_wage()` method handles four distinct cases: numeric value, ">=" notation, "or more" notation, and N/A. The separation of wage value and capped flag into a tuple return is clean. The fact that the interactive export has zero capped wages does not invalidate the capping logic -- it protects against future format changes or different BLS data sources.

6. **Fallback download strategy.** The `_download_and_read()` method tries the BLS URL first, then falls back to a cached local file. BLS is notorious for blocking automated downloads with 403 errors, so this is pragmatic.

**What concerns me:**

1. **`except Exception` in `_download_and_read()` is too broad.** This swallows all errors including `KeyboardInterrupt`, `SystemExit`, and `MemoryError`. The staff engineer flagged this as LOW severity. I agree it is low severity but I would narrow it to `except (requests.RequestException, IOError, ValueError)` for hygiene. A `MemoryError` during download should not silently fall back to a cached file.

2. **No retry logic on the BLS download.** A single HTTP request with a 120-second timeout. BLS servers occasionally return transient 503 errors. A simple retry with backoff (2 attempts, 5-second delay) would reduce manual intervention. Not blocking for Bronze.

3. **The `DOWNLOAD_URL` points to an HTML page, not an XLSX file.** The URL `https://www.bls.gov/emp/tables/occupational-projections-and-characteristics.htm` is an HTML page that links to the actual XLSX download. The comment on line 169 says "for now assume direct download" -- meaning the download path is actually broken for the production URL and will always fall through to the fallback path. This is fine for MVP (the fallback file exists and is the production dataset), but it means the "download" path is dead code in practice. Should be documented more explicitly.

## Data Quality & Trust Assessment
### Grade: A-
### Rationale

The DQ framework is excellent. 18 rules, all evidence-backed from the full 832-row dataset EDA, 16 of 17 executable rules passing (1 deferred for framework metadata), and all 18 rules verified through chaos monkey adversarial testing.

**What earns the A-:**

- **Evidence chain is complete.** Every DQ rule cites the specific EDA finding that informed its threshold. The thresholds were initially calibrated on a 10-row sample, then updated and re-validated against the full 832-row dataset. The EDA explicitly documents the recalibration. This is best practice.

- **RAW-OOH-013 handling demonstrates maturity.** The initial rule required strictly positive openings. The full dataset revealed 4 occupations with zero openings due to BLS rounding from thousands. Rather than ignoring the failure, the team investigated the root cause, documented it in the scorecard, amended the rule to `>= 0`, and re-ran validation. The rule description now explains why zero is valid. This is how DQ rules should evolve.

- **The chaos monkey achieved 100% rule coverage.** 14 of 18 rules fired in the initial 5-cycle random run. The remaining 4 were exercised through a targeted follow-up run on the full dataset. The gap analysis section identifies 4 reasonable enhancements (employment magnitude cap, change pct bounds, SOC reference validation, education distribution) without over-engineering.

- **Cross-field consistency rules are strong.** RAW-OOH-004 (wage cap consistency) and RAW-OOH-018 (employment change arithmetic) validate relationships between fields, not just individual field ranges. These are the most valuable DQ rules because they catch corruption that single-field rules miss.

**What loses the full A:**

- **No SOC code referential integrity check.** A fake SOC code with valid format (e.g., 97-4823) passes all current rules. The chaos monkey report correctly identifies this gap and defers it to Silver zone (cross-reference against SOC 2018 code list). This is reasonable but it means Bronze has no defense against fabricated-but-valid-format codes.

- **Statistical distribution rules are warn-only.** The mean wage range ($40K-$70K) and negative employment change rate (15-40%) rules are informational, not gates. This is correct for Bronze (you do not reject data based on statistical properties), but it means a fundamental shift in the data distribution (e.g., mass wage inflation or BLS methodology change) would only produce a warning, not a pipeline halt.

## Governance Assessment
### Grade: A-
### Rationale

The governance artifacts are comprehensive and well-proportioned for public, aggregate, non-PII labor market data:

- Source config (`domain/sources/bls_ooh.yaml`) -- clean, well-documented
- EDA report -- 332 lines of field-by-field profiling on the full 832-row dataset, including cross-field analysis and edge case documentation
- DQ rules -- 18 rules with evidence citations and human approval timestamps
- DQ scorecard -- shows full-dataset validation with investigation of the single failure
- Chaos monkey -- 5-cycle random + targeted follow-up = 100% rule exercise rate
- Data contract -- CDE/PII flags with business rationale for each CDE designation
- SOC code audit -- standalone document cataloging broad codes and catchall categories
- Staff review -- concise, specific, approved with documented issues

**One governance error that must be fixed (CHANGES REQUESTED):**

The data contract (`governance/data-contracts/raw-bls-ooh.yaml`) has **reversed code orderings** for three fields:

- Line 158: `education_code` described as "1=No formal credential through 8=Doctoral/professional degree" -- **WRONG.** The ingestor code (lines 54-63) clearly maps `"doctoral or professional degree": 1` and `"no formal educational credential": 8`. The correct ordering is 1=Doctoral through 8=No formal.

- Line 176: `work_experience_code` described as "1=None, 2=Less than 5 years, 3=5 years or more" -- **WRONG.** The ingestor (lines 66-70) maps `"5 years or more": 1, "less than 5 years": 2, "none": 3`.

- Line 194: `training_code` described as "1=None through 6=Internship/residency" -- **WRONG.** The ingestor (lines 73-80) maps `"internship/residency": 1, ... "none": 6`.

These are documentation errors, not code bugs. The ingestor code, EDA report, domain context, and Silver spec all have the correct orderings. But the data contract is the artifact most likely to be read by downstream consumers and AI agents. If the Silver zone DQ rules are written against the data contract descriptions, they will encode the wrong semantics.

**Fix required before Silver zone DQ rule authoring begins.**

## Domain Discovery Assessment
### Grade: A
### Rationale

The BLS OOH section of `governance/domain-context.md` (starting at line 369) is thorough and accurate. As someone who has worked with BLS Employment Projections data professionally:

1. **Domain identification is correct.** U.S. Labor Market, occupation-level employment projections from the BLS EP program.

2. **Taxonomy identification is correct.** SOC 2018 with 832 detailed occupations. The note about SOC 2028 migration is forward-looking and correct.

3. **The employment-in-thousands conversion is correctly documented.** This is the single most common source of errors when working with BLS EP data. The domain context prominently explains it.

4. **The top-coded wage explanation is accurate.** $239,200 is the BLS wage cap. The interactive export's behavior (actual numeric values instead of ">=" notation) is correctly noted as a format difference, not a data quality difference.

5. **N/A wage occupations are correctly categorized.** Elected officials, self-employed-dominated occupations -- this matches BLS documentation.

6. **The SOC code audit is excellent.** Identifying the 7 rolled-up/broad codes (13-1020, 13-2020, 29-2010, 31-1120, 39-7010, 47-4090, 51-2090) and the 46 "all other" catchall categories is exactly the kind of domain knowledge that prevents downstream integration errors. The Silver spec correctly uses this audit to design the `broad_occupation_flag` and `catchall_flag` fields.

7. **Cross-source integration is correctly framed.** The SOC-as-bridge-to-CIP narrative is accurate. The CIP-to-SOC crosswalk is correctly identified as the critical dependency for the FutureProof pipeline.

**One factual inconsistency to resolve:**

The domain context (line 382) says "current cycle: 2023-2033" while the spec (line 78) says "2024-2034 projection cycle" and the data contract says "2024-2034 projection cycle." The Silver spec also says "2024-2034." The actual BLS EP interactive export header columns reference "Employment 2024" and "Employment 2034," confirming 2024-2034. The domain context has a stale initial reference that should be updated to match reality.

### Concept Normalization Gate (BLOCKING CHECKLIST)

- [x] `governance/domain-context.md` contains a "Canonical Concept Map" section -- **PRESENT** (line 181)
- [x] The concept map has status CONFIRMED or PROPOSED -- **PROPOSED (Unconfirmed)**, acceptable for this gate
- [x] If PROPOSED: the map is reasonable for the identified domain -- **YES.** 12 target concepts. Concept #10 (Occupation) maps directly to this BLS OOH data source. The concept map correctly identifies the CIP-to-SOC crosswalk as the bridge mechanism.
- [x] The number of target business concepts is appropriate -- **12 concepts.** On the low side of the 15-50 range but appropriate for a two-source MVP. The BLS OOH adds the occupation dimension that was "EXTENDED" status in the College Scorecard concept map. The list is growing organically.
- [x] Collision resolution rules exist -- **PRESENT.** Four scenarios documented including the critical "Multiple SOC codes for one CIP code" resolution (retain all with confidence scores).
- [x] The silver zone spec includes a concept normalization step -- **YES.** The Silver spec (`docs/specs/silver-base-bls-ooh.md`) explicitly includes growth_category derivation (lines 134-145), education_level_name lookup (lines 149-160), SOC major group derivation (lines 107-133), broad_occupation_flag (lines 161-173), and catchall_flag (lines 176-178). These are concept normalization steps. The spec also references ConceptNormalizer implications for the 7 broad codes.

**Concept Normalization Gate: PASS.**

## AI-Readiness Assessment
### Grade: B+
### Rationale

The Bronze zone is not directly AI-serving, but it lays the groundwork correctly:

1. **SOC codes are clean and joinable.** 832 codes, 100% valid format, zero duplicates. This is the prerequisite for the CIP-to-SOC crosswalk that enables the core FutureProof question.

2. **The 23 null-wage occupations are preserved, not dropped.** This is the right decision. Many of these are high-profile occupations (physicians, surgeons) that users will ask about. The Silver spec adds a `wage_available` flag, and the Gold zone will need a strategy for these (likely: surface the occupation with a note that wage data is not available from BLS for this occupation).

3. **The 7 broad codes and 46 catchall categories are identified.** This is critical for AI-readiness. An MCP server that maps a student to "Managers, all other" (SOC 11-9199) needs to know that this is a low-signal result. The Bronze zone identified these; the Silver zone flags them; the Gold/MCP zones can use the flags for confidence scoring.

4. **The education/experience/training codes enable education-requirement matching.** The core FutureProof integration: "Does studying X give me the credential level needed for career Y?" requires matching College Scorecard's `credlev` against BLS OOH's `education_code`. Both are now in the pipeline.

**What is missing (expected at Silver/Gold):**

- The CIP-to-SOC crosswalk table does not exist yet. Without it, College Scorecard programs cannot be linked to BLS occupations. This is the single most important dependency for AI-readiness.
- No derived metrics yet (debt-to-salary ratio, growth categorization). These are correctly deferred to Silver/Gold.

## Code Quality Assessment
### Grade: A
### Rationale

**Ingestor (`src/raw/bls_ooh_ingestor.py`, 473 lines):**

- Clean class structure extending `BaseIngestor` with three required methods (`fetch`, `flatten`, `get_schema`)
- Well-organized constants: `_EDUCATION_CODE_MAP`, `_WORK_EXPERIENCE_CODE_MAP`, `_TRAINING_CODE_MAP`, `_HEADER_PATTERNS` are all class-level, documented, and testable
- The `_map_columns()` method (lines 230-248) is a clean implementation of fuzzy header matching. The `used_fields` set prevents double-mapping. First-match-wins priority is deterministic.
- `_parse_wage()` returns a tuple `(value, is_capped)` which is cleaner than setting a side-effect flag
- `_derive_code()` with its code-column-first-then-label-fallback pattern handles both BLS export formats gracefully
- All static methods are correctly marked `@staticmethod`
- The `import openpyxl` inside `_read_xlsx()` and `import tempfile` inside `_download_and_read()` are lazy imports -- slightly unusual but harmless for a rarely-instantiated class

**Tests (`tests/raw/test_bls_ooh_ingestor.py`, 454 lines, 40 tests):**

- **40 tests, all passing in 0.62 seconds.** Fast, deterministic, no network dependencies.
- **Well-organized test classes:** TestSchema (5), TestConstants (3), TestFetch (5), TestFlatten (9), TestCoerceEdgeCases (11), TestFullDataset (7)
- **Specific value assertions:** Software developers at SOC 15-1252 with employment_current = 1795500. Surgeons at 29-1248 with capped wage = 239200.0. Legislators at 11-1031 with null wage.
- **Edge case coverage:** None input, empty string, negative employment change, all 8 education levels, code derivation from labels, code column precedence over labels
- **Full dataset tests** (7 tests against the real 832-row BLS XLSX) verify row count range, SOC format, uniqueness, no summary codes, all education codes present, declining occupations exist, and wage null rate. These are excellent integration-level smoke tests.
- **The `__new__` trick** to skip `BaseIngestor.__init__` is documented and pragmatic (same pattern as the College Scorecard tests)

**Minor observations:**

- The staff engineer noted the missing test for negative `employment_change` in the sample data tests. The `TestCoerceEdgeCases::test_negative_employment_change` test (line 302) covers this with synthetic data, and the `TestFullDataset::test_full_has_negative_employment_change` covers it with real data. So the gap is theoretical only.
- No test for the `ValueError` raised when no header row is found in the XLSX. Low risk since the only way to trigger this is a completely malformed file.

## Top Risks

1. **Data contract code descriptions are reversed (DOCUMENTATION BUG).** The `raw-bls-ooh.yaml` data contract reverses the orderings for `education_code`, `work_experience_code`, and `training_code`. If Silver zone agents reference the data contract for DQ rule semantics, they will write rules with inverted meanings. **Impact:** Incorrect Silver DQ rules or downstream interpretation errors. **Mitigation:** Fix the data contract descriptions to match the ingestor code before Silver zone DQ rule authoring begins. This is a 5-minute fix.

2. **Projection cycle inconsistency (2023-2033 vs 2024-2034).** The domain context says "2023-2033" while the spec, data contract, and actual XLSX headers say "2024-2034." If the Silver zone reads the domain context as authoritative, it may label the data with the wrong vintage. **Impact:** Misleading data vintage labels in Gold zone products. **Mitigation:** Update the domain context BLS section to say "2024-2034" consistently. Also a quick fix.

3. **The download URL points to an HTML page, not the XLSX file.** The production download path will always fail and fall back to the cached file. This is acceptable for MVP but means the pipeline cannot automatically refresh when BLS publishes a new projection cycle. **Impact:** Manual intervention required for data refresh. **Mitigation:** Either update the URL to point to the actual XLSX download link (if stable), or document the manual download step in the runbook. Not blocking for Bronze-to-Silver.

## What I'd Cut

- **`COLUMN_MAP` class attribute (lines 84-99).** It is never referenced in the code -- all column mapping goes through `_HEADER_PATTERNS`. This is dead code. It may have been an early implementation that was replaced by the more flexible pattern-matching approach. Remove it to avoid confusion.

- **`_coerce_int()` static method (lines 396-407).** It is defined but never called anywhere in the class. `_coerce_employment()` and `_derive_code()` handle all integer coercion. Dead code.

## What's Missing for Production

1. **Data contract code description fixes.** The reversed education/experience/training code descriptions must be corrected.
2. **Domain context projection cycle correction.** Update "2023-2033" to "2024-2034."
3. **CIP-to-SOC crosswalk ingestion.** This is the critical Silver zone dependency. Without it, the BLS OOH data cannot be linked to College Scorecard programs.
4. **SOC 2018 reference table.** For referential integrity checking in Silver. The chaos monkey identified the lack of SOC reference validation as a gap.
5. **Monitoring for BLS EP updates.** The biennial projection cycle means the data will be updated around 2025-2026. The pipeline needs a mechanism to detect and incorporate the new cycle.

## What I'd Do Differently

If starting over:

1. **Separate the download URL from the XLSX parsing.** The `_download_and_read()` method tries to download from an HTML page URL, which will never work. I would either (a) make the URL configurable in the source YAML so it can be updated when BLS changes the download link, or (b) explicitly document the manual download workflow and remove the pretense of automated downloading.

2. **Use an enum or named constants for the education/experience/training code maps.** The current dict-based approach works but the "magic numbers" (1-8, 1-3, 1-6) appear in multiple places (ingestor, EDA, domain context, data contract, Silver spec) with no single source of truth. A `BLSEducationLevel` enum defined once and imported everywhere would prevent the data contract reversal bug.

3. **Add a "data vintage" field to the schema.** The projection cycle (2024-2034) is documented in comments and governance artifacts but not in the data itself. A `projection_cycle` string field (e.g., "2024-2034") would make the vintage explicit and queryable. When the next projection cycle is released, old and new data can be distinguished without relying on `load_date`.

## Concept Normalization Gate

**Status: PASS**

All gate criteria are met:
- Canonical Concept Map exists and is PROPOSED
- 12 business concepts are appropriate for a two-source MVP
- Collision resolution rules are documented
- The Silver spec includes concept normalization steps (growth categories, education levels, SOC major groups, broad/catchall flags)
- The CIP-to-SOC crosswalk is correctly identified as a separate Silver spec with ConceptNormalizer implications

## Silver Readiness Assessment

The Bronze output is well-suited for the planned Silver transformations:

1. **SOC normalization:** SOC codes are already clean (100% valid XX-XXXX, zero duplicates). Silver does not need to fix anything -- it derives additional fields (major group code/name) and flags (broad, catchall).

2. **Growth categorization:** `employment_change_pct` is populated for all 832 rows with the expected distribution (27.9% negative). The Silver spec's growth category thresholds (declining_fast through booming) are reasonable and grounded in BLS convention.

3. **Flag derivation:** The 7 broad codes and 46 catchall categories are identified in the SOC code audit and will be flagged in Silver. The audit is specific enough to hardcode the broad code list rather than relying on fragile pattern matching.

4. **Cross-source integration:** SOC codes are in the correct format (XX-XXXX) for CIP-to-SOC crosswalk matching. The broad occupation codes that need special crosswalk handling are identified. The wage and education data that will feed Gold zone stats (ERN, GRW) are clean and well-understood.

## Overall Verdict
### Grade: A-

This is the best Bronze zone implementation I have seen in this pipeline. The ingestor code is clean and well-tested (40 tests, 0.62 seconds). The EDA is comprehensive and was recalibrated against the full dataset. The DQ rules are evidence-backed, chaos-tested, and correctly amended when the full dataset revealed the zero-openings edge case. The SOC code audit provides exactly the domain knowledge that Silver needs.

The A- (not a full A) reflects: (1) the data contract code description reversals, which are documentation errors that could propagate to Silver, and (2) the projection cycle inconsistency between the domain context and other artifacts. Both are quick fixes. The dead code (`COLUMN_MAP`, `_coerce_int()`) and the non-functional download URL are minor blemishes that do not affect data correctness.

Would I ship this? As a Bronze zone, it does exactly what it should. Would I invest in it? Yes -- this is a solid foundation for the Silver transformations and the CIP-to-SOC bridge that makes FutureProof work. Would I stake my reputation on the data quality? On the 832 rows of BLS EP data in the Bronze zone, yes -- the EDA, DQ rules, and chaos testing give me high confidence in the data.

**Verdict: APPROVED for Silver zone transition.**

Conditions (non-blocking but required before Silver DQ rules are authored):
1. Fix data contract code descriptions for education_code, work_experience_code, and training_code
2. Update domain context BLS section projection cycle from "2023-2033" to "2024-2034"

---

## Recommendations for Silver Zone

1. **Import the broad code list from the SOC audit, do not pattern-match.** The Silver spec already calls for this (line 167). The 7 hardcoded codes are more reliable than a regex on the trailing digit.
2. **Preserve `median_wage_capped` through Silver even though it is all-False.** The Silver spec correctly plans this. It protects against future data source changes.
3. **The CIP-to-SOC crosswalk is the critical path.** It should be its own spec, ingested as a reference dimension. The Silver BLS OOH spec prepares the SOC side; the crosswalk spec bridges to the CIP side.
4. **Consider adding a `projection_cycle` field** (e.g., "2024-2034") to make the data vintage explicit and queryable without depending on metadata timestamps.
5. **Fix the data contract before Silver DQ rule authoring begins.** The reversed code descriptions will confuse any agent or human reading the contract.
