# Principal Data Architect Review

**Date:** 2026-04-09
**Reviewer:** @principal-data-architect
**Scope:** Bronze-to-Silver zone transition review
**Domain:** AI labor market impact (Karpathy AI Exposure Scores)
**Spec:** raw-ingest-karpathy-ai-exposure

## Executive Summary

The Bronze zone for Karpathy AI Exposure is clean, well-governed, and ready for Silver. The ingestor is simple and correct, the EDA is thorough and honest about what the data actually contains vs. what the spec estimated, and the DQ rules are real tests against real data with appropriate thresholds. The biggest structural challenge for Silver is not the 52 null SOC rows (manageable via title matching) -- it is the 46 broad SOC codes (XX-XXX0) that represent a grain explosion problem the spec has not adequately addressed. The Silver plan's duplicate SOC handling strategy (take highest employment) loses information and may produce incorrect scores for detailed occupations under a broad code. These are solvable problems, not blockers.

## Architecture Assessment
### Grade: B+
### Rationale

The 4-zone pattern is correctly applied here. Bronze ingests two files, joins on slug, and lands a clean 342-row table. The zone boundary is clean -- Bronze does fetch/parse/join, Silver does SOC normalization and cross-validation, Gold does score inversion and filtering. This is the right decomposition.

The Silver spec's grain change from slug (Bronze) to soc_code (Silver) is well-motivated but introduces two distinct cardinality problems:

1. **Contraction (many-to-one):** Multiple Karpathy slugs mapping to the same SOC code. The EDA found zero duplicate SOC codes in the raw data, so the spec's dedup rule (take highest employment) may be a solution in search of a problem. Good defensive design, but the real test is what happens after broad code expansion.

2. **Expansion (one-to-many):** 46 broad SOC codes (XX-XXX0) will each fan out to multiple detailed SOC codes if the "propagate to all detailed codes under the prefix" strategy from the domain context is followed. This means Silver's output could have significantly more rows than Bronze (potentially 342 - 52 null + expansion of 46 broad codes to ~200+ detailed codes = ~500+ rows). The spec says the grain is "one row per occupation (soc_code)" with "Expected rows: 342" but the actual row count after broad code expansion will be higher. The spec needs to acknowledge this.

The architecture is sound -- I would not change the zone decomposition. But the Silver spec needs to be precise about what happens to row count after broad code expansion.

## Data Quality & Trust Assessment
### Grade: A-
### Rationale

18 DQ rules, all passing, across 6 dimensions. The rules are real SQL against real Iceberg tables, not stubs. The chaos monkey ran 5 cycles with 11 corruptions per cycle across 10 dimensions, and the rules caught the right failures (uniqueness, volume, format, completeness). Detection rates of 11-28% across cycles are realistic for a Bronze DQ suite -- these rules are not designed to catch every possible corruption, they are designed to catch the corruptions that matter for this data.

Specific things done right:
- SOC coverage threshold was correctly adjusted from the spec's optimistic 95% down to 80% based on EDA evidence (actual: 84.8%). This is how DQ should work -- evidence-based thresholds, not wishful thinking.
- Cross-validation rule RAW-KAI-009 compares wages against BLS OOH and found perfect alignment. This is a genuinely useful validation that confirms data vintage consistency.
- The DQ rules JSON file has full evidence citations linking each rule back to the EDA report and domain context. This is auditable governance.

One gap: RAW-KAI-009 errored in all 5 chaos monkey cycles (likely because the corrupted table had SOC codes that did not exist in BLS OOH). This is not a rules failure -- the cross-validation join naturally fails when SOC codes are corrupted. But it means the cross-validation rule has never been tested under adversarial conditions. Low risk given the rule passes trivially on clean data.

Missing DQ rule: No rule validates that rationale length exceeds a minimum threshold (EDA found min 297 chars). A rationale that is just "N/A" or a few words would pass the current null-check but would be useless for the MCP display use case. This should be added at Silver.

## Governance Assessment
### Grade: A-
### Rationale

The governance artifacts are comprehensive and proportional to the data's criticality (Medium quality tier -- LLM-generated scores):

- EDA report: Thorough, honest, actionable. Correctly identified the SOC coverage gap and broad code issue before DQ rules were written.
- Domain context: Extensive section covering methodology, vocabulary, limitations, cross-validation, integration strategy, and PII assessment. The limitations table is particularly well done -- it acknowledges self-referential bias, no demand elasticity, no regulatory barriers.
- Business glossary: BT-080 and BT-081 are well-defined with appropriate caveats.
- Data contract: Present (YAML format).
- Lineage: OpenLineage JSON with column-level lineage. Correct.
- Audit trail: Multiple audit records covering EDA, DQ rules, DQ execution, chaos monkey, PII scan, entity resolution, CDE tagging, and adversarial audit.

This is right-sized governance for an MVP hackathon pipeline with medium-quality data. Not over-governed, not under-governed.

## Domain Discovery Assessment
### Grade: A
### Rationale

The domain context for Karpathy AI Exposure is accurate and well-researched. Specific validations:

- The methodology description correctly captures that this is a single Gemini Flash run with no calibration or inter-rater reliability. The "saturday morning 2 hour vibe coded project" caveat is preserved.
- The SOC taxonomy section correctly identifies 244 detailed, 46 broad, and 52 null codes with appropriate resolution strategies.
- The limitations table (7 limitations) is comprehensive and domain-accurate: self-referential bias, no demand elasticity, no regulatory barriers, no social preferences -- these are the standard critiques of LLM-based occupation scoring in the labor economics literature.
- The FutureProof integration section correctly documents the stat_res inversion formula and the boss_ai_score passthrough.
- Cross-validation results are accurately reported (perfect wage alignment, r=0.387 exposure-pay correlation).

The domain interpretation would pass review by a labor economist familiar with AI exposure scoring.

### Concept Normalization Gate

This is a special case. The Karpathy dataset does not introduce a new classification taxonomy that requires concept normalization in the traditional sense. The SOC codes used here are the same SOC codes already handled by the existing BLS OOH and O*NET concept maps. The Karpathy-specific concepts (exposure_score, rationale, category) are not classification codes -- they are measures and attributes.

- [x] `governance/domain-context.md` contains Canonical Concept Map sections (3 sections: College Scorecard, BLS OOH, O*NET)
- [x] Concept maps have status PROPOSED
- [x] The maps are reasonable for the identified domain
- [x] Target concept count is appropriate (12 for College Scorecard, reasonable range)
- [x] SOC code normalization is already documented in the existing concept maps
- [N/A] Collision resolution for Karpathy-specific concepts -- no new taxonomy codes to normalize

**Concept normalization is NOT a blocker for this spec.** The Karpathy dataset joins on SOC code, which is already normalized by the existing BLS OOH Silver pipeline. The Silver transformation for Karpathy is SOC format validation and cross-referencing, not concept normalization. The spec correctly identifies this as a join/validation problem, not a concept mapping problem.

## AI-Readiness Assessment
### Grade: B+
### Rationale

The MCP tool design (`get_ai_exposure(soc_code)`) is appropriate for the use case. Returning both the score and the rationale text is correct -- the rationale provides the interpretive context that prevents users from conflating "AI exposure" with "AI will take my job."

The domain context section on AI-Ready Considerations is well-written and provides actionable guidance for the MCP engineer: always include methodology caveats, frame scores as "reshaping" not "replacement."

One architectural concern: the spec defines `get_ai_exposure(soc_code)` as a standalone tool, but the primary consumer will call `get_career_path_stats(unitid, cipcode)` which returns stat_res and boss_ai_score inline. Having two access paths to the same data (standalone tool vs. embedded in career path stats) creates a consistency risk if the data refreshes at different times. The Gold zone backfill pattern (re-promote program_career_paths with ai_exposure join) mitigates this, but the pipeline must ensure both tables are always promoted together. This should be documented as a deployment constraint.

## Code Quality Assessment
### Grade: A-
### Rationale

The ingestor (`src/raw/karpathy_ai_exposure_ingestor.py`) is 300 lines of clean, readable Python. Each method does one thing. The `_normalize_scores()` method handles the dict-vs-array format discrepancy correctly. Type coercion methods are defensive and handle edge cases (None, empty string, whitespace, commas, dollar signs).

The test suite (34 tests, all passing) uses well-designed sample data with boundary values (score 0, score 10, null SOC, unmatched slugs, comma-formatted numbers). These are real tests with specific value assertions, not `assert result is not None` theater.

Staff engineer correctly noted: `_coerce_soc` and `_coerce_string` are identical. Minor redundancy, not worth blocking.

The one code smell flagged by the staff engineer -- `test_full_soc_coverage_above_90_percent` asserting `> 0.80` -- is cosmetic but sloppy. Test names should not lie.

## Top Risks

1. **Broad SOC code expansion strategy is underspecified.** The domain context says "propagate Karpathy exposure score from broad code (XX-XXX0) to all detailed codes (XX-XXXX) under the same prefix." This means a single Karpathy score (e.g., Software Developers broad code) would be assigned identically to multiple detailed occupations (Web Developers, Software QA, etc.). This is a reasonable approximation but (a) the spec does not document the expected row count after expansion, (b) the Silver DQ rules do not validate post-expansion grain uniqueness, and (c) the `soc_resolved_method` field does not have a value for "broad_code_expansion." **Impact:** Incorrect downstream join cardinality. **Mitigation:** Add `soc_resolved_method = 'broad_expansion'` as a fourth category, update expected row count, add DQ rule for post-expansion grain uniqueness.

2. **No rationale minimum length DQ rule.** The rationale field is a display field shown to users in the MCP/frontend Fight AI boss results. A degenerate rationale (empty-ish string that passes the null check) would produce a bad user experience. **Impact:** Low probability but high visibility if it occurs. **Mitigation:** Add a Silver DQ rule: `rationale length >= 100 chars`.

3. **RAW-KAI-009 cross-validation errored in all chaos monkey cycles.** The wage cross-validation rule depends on a join to `bronze.bls_ooh`, which may fail if that table is unavailable, renamed, or if corrupted SOC codes break the join. This rule has never been proven to fail correctly under adversarial conditions. **Impact:** Silent cross-validation failures in production. **Mitigation:** Add error handling so RAW-KAI-009 reports a distinct "ERROR" status rather than silently passing. Low priority for hackathon.

## What I'd Cut

Nothing. This is a small, clean pipeline. The governance artifacts are proportional. There is no over-engineering. If anything, the spec is ambitious in scope (Bronze through Gold through MCP backfill through re-promotion in a single spec document) but that is a documentation choice, not an architecture issue. Each zone should be implemented and validated independently.

## What's Missing for Production

1. **Broad code expansion strategy must be codified in the Silver spec** before implementation begins. The current Silver spec (Zone 2 in the main spec doc) only mentions "SOC code normalization" and "null SOC resolution" -- it does not describe how to handle the 46 broad codes. The domain context says "propagate to all detailed codes under prefix" but this is not reflected in the Silver schema, DQ rules, or expected row counts.

2. **Silver DQ rule for rationale minimum length** (>= 100 chars). Currently only checking non-null.

3. **Silver DQ rule for post-broad-expansion grain uniqueness on soc_code.**

4. **Deployment constraint documentation:** consumable.ai_exposure and consumable.program_career_paths must be promoted atomically (or in sequence with no consumer reads between them) to avoid inconsistent stat_res values.

## What I'd Do Differently

If starting over, I would separate the broad SOC code expansion into its own explicit pipeline step with its own DQ gate, rather than bundling it into the Silver transformation alongside null SOC resolution and format normalization. These are three distinct operations with different risk profiles:

- SOC format normalization: zero risk, mechanical
- Null SOC title matching: medium risk, fuzzy matching
- Broad-to-detailed SOC expansion: high risk, cardinality change, score propagation

Mixing them in a single Silver transformation makes it harder to isolate failures and validate the output. But for a hackathon MVP with 342 rows, this is an acceptable trade-off.

## Overall Verdict
### Grade: B+

### Decision: APPROVED

The Bronze zone is clean and well-governed. The data is trustworthy at the Bronze level -- 342 rows, 18 DQ rules passing, 5 chaos monkey cycles survived, staff engineer approved, cross-validation against BLS OOH confirms data vintage alignment. The Silver transformation plan is sound in concept but needs the broad SOC code expansion strategy formalized before implementation.

I am approving this transition with two advisory notes (not blockers):

**Advisory 1 (RECOMMENDED):** Before writing Silver code, update the Silver zone section of the spec to explicitly document: (a) the broad-to-detailed SOC code expansion strategy, (b) the expected output row count after expansion (~500+ rows, not 342), (c) the `soc_resolved_method` values including 'broad_expansion', and (d) a DQ rule for post-expansion grain uniqueness on soc_code.

**Advisory 2 (RECOMMENDED):** Add a Silver DQ rule for rationale minimum length (>= 100 chars).

Neither advisory blocks the transition. The Silver zone implementer should address them during spec refinement before writing code.

---

**Signed:** @principal-data-architect
**Date:** 2026-04-09
**Verdict:** APPROVED (with advisories)
