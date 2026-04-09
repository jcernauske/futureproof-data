# Audit Trail: @doc-generator — gold-career-outcomes-college-scorecard

**Agent:** @doc-generator
**Spec:** docs/specs/gold-career-outcomes-college-scorecard.md
**Date:** 2026-04-06
**Zone:** Gold (Consumable)

## Actions Taken

### 1. Golden Dataset Created
**Path:** `governance/golden-datasets/gold-career-outcomes-college-scorecard-golden.json`
- 12 verifiable values across 3 well-known programs
- MIT Computer Science (unitid 166683, CIP 11.07) — 5 values: earnings, DTE ratio, DTE tier, confidence tier, program value index
- UPenn Nursing (unitid 215062, CIP 51.38) — 4 values: earnings, DTE ratio, earnings growth, outcome completeness
- UF Business Administration (unitid 134130, CIP 52.02) — 3 values: DTE ratio, program value index, earnings growth rate (negative)
- Each value traced from Silver source row through Gold derivation formula to expected output
- Selected to cover: high-earnings CS, moderate-earnings healthcare, typical-business, and negative earnings growth (common edge case)

### 2. Data Dictionary Updated
**Path:** `governance/data-dictionary.json`
- Added `consumable.career_outcomes` table entry with all 30 columns
- Every column has a plain-English definition passing the "explain to a business analyst" test
- CDE flags cross-referenced from data contract (`governance/data-contracts/consumable-career-outcomes.yaml`)
- DQ rules cross-referenced from scorecard (42 rules, all passing)
- Lineage cross-referenced to `governance/lineage/gold-career-outcomes-college-scorecard-20260406T220000Z.json`

### 3. README Updated
**Path:** `README.md`
- Added Gold conceptual model Mermaid diagram (Career Outcome + Percentile Band + Financial Assessment + Data Confidence entities)
- Added Gold logical model Mermaid diagram (30-column denormalized Career Outcomes table)
- Added Gold physical model Mermaid diagram (CONSUMABLE_CAREER_OUTCOMES with DuckDB types)
- Updated Tables section to include `consumable.career_outcomes`
- Updated Business Glossary from 17 to 26 terms (added BT-018 through BT-026)
- Updated Key Design Decisions with 4 Gold-specific decisions
- Added Silver/Gold subsection headers to all three model levels for clarity

### 4. Grounding Document Created
**Path:** `data/ai_ready/grounding/career-outcomes-college-scorecard.md`
- Structured fact sheet for MCP zone consumption
- Key metrics: row count, confidence tier distribution, DTE tier distribution, earnings ranges
- Lineage reference and confidence notes for AI consumers
- Data quality score: 100% (42/42 DQ rules passing)

## Interpretation Decisions

1. **Golden dataset institution selection:** Chose MIT (CS), UPenn (Nursing), and UF (Business) because they are well-known institutions with high-confidence data, cover three different CIP families, and represent different outcome profiles (very high earnings, moderate earnings, typical state university). Stanford was also available but MIT was preferred for CS because both CIP 11.07 programs had identical percentile bands (same CIP family), and MIT's lower debt creates a more extreme DTE ratio that better tests the derivation math.

2. **Negative earnings growth as golden value:** Deliberately included UF Business Admin's negative earnings growth rate (-3.7%) as a golden value because the spec explicitly notes that negative values are expected in ~44% of programs. This tests that the pipeline correctly handles and preserves negative derived values.

3. **Data dictionary definition style:** Used first-person explanatory style ("This tells you...") for derived fields like confidence_tier and percentile bands, since these are FutureProof-specific concepts that business users may not intuitively understand. Kept more factual style for source-carried fields (earnings, debt) that map to well-known College Scorecard concepts.

4. **institution_control null note:** Added explicit note in data dictionary that this field is currently 100% null due to a Bronze re-ingestion blocker, since this could confuse consumers who expect it to be populated based on the NOT NULL constraint in the physical model.
