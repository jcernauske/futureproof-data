# Audit Trail: Business Glossary — gold-futureproof-engine

**Date:** 2026-04-09
**Agent:** @data-steward
**Spec:** docs/specs/gold-futureproof-engine.md
**Mode:** Greenfield (Gold zone)

## Summary

Identified business terms from the Gold FutureProof Engine spec, which builds the unified cross-source product joining College Scorecard, BLS OOH, O*NET, and CIP-SOC crosswalk data into two consumable tables: `consumable.program_career_paths` and `consumable.career_branches`.

## New Terms Proposed (BT-077 through BT-093)

| Term ID | Term | Source | Category | Status |
|---------|------|--------|----------|--------|
| BT-077 | Pentagon Stats | project-specific | entity | PROPOSED |
| BT-078 | Earning Power (stat_ern) | project-specific | derived | PROPOSED |
| BT-079 | Return on Investment (stat_roi) | project-specific | derived | PROPOSED |
| BT-080 | AI Resilience (stat_res) | project-specific | derived | PROPOSED |
| BT-081 | Boss Fight Score | project-specific | entity | PROPOSED |
| BT-082 | Program Career Path | project-specific | entity | PROPOSED |
| BT-083 | Boss AI Score | project-specific | derived | PROPOSED |
| BT-084 | Boss Loans Score | project-specific | derived | PROPOSED |
| BT-085 | Boss Ceiling Score | project-specific | derived | PROPOSED |
| BT-086 | CIP Prefix Match | project-specific | derived | PROPOSED |
| BT-087 | Stats Available Count | project-specific | derived | PROPOSED |
| BT-088 | Bosses Available Count | project-specific | derived | PROPOSED |
| BT-089 | Overall Confidence (FutureProof Engine) | project-specific | classification | PROPOSED |
| BT-090 | Career Branch | project-specific | entity | PROPOSED |
| BT-091 | Stat Delta | project-specific | derived | PROPOSED |
| BT-092 | Branch Has Full Data | project-specific | derived | PROPOSED |
| BT-093 | Match Quality (Gold Engine) | project-specific | classification | PROPOSED |

All 17 terms are project-specific and require REQUIRE_HUMAN_APPROVAL gate (set to true in CLAUDE.md).

## Existing Terms Updated (used_in_models)

Added "gold-futureproof-engine" to used_in_models for the following existing terms:

BT-001 (UNITID), BT-003 (CIP Code), BT-004 (Program Name), BT-005 (CIP Family), BT-006 (CIP Family Name), BT-009 (Median Earnings 1-Year), BT-011 (Median Debt), BT-019 (Debt-to-Earnings Ratio), BT-022 (CIP Family Earnings Rank), BT-026 (Promotion Timestamp), BT-027 (SOC Code), BT-028 (Occupation Title), BT-030 (SOC Major Group Name), BT-031 (Employment Current), BT-036 (Median Annual Wage), BT-039 (Education Level Name), BT-041 (Growth Category), BT-047 (GRW Score), BT-048 (Wage Percentile Overall), BT-049 (Wage Percentile Education Tier), BT-051 (Market Score), BT-060 (Career Transition), BT-061 (Relatedness Tier), BT-066 (HMN Score), BT-068 (Burnout Score), BT-069 (Burnout Driver), BT-073 (CIP-SOC Crosswalk), BT-076 (Match Quality)

## Existing Terms NOT Needing Boss-Specific Glossary Entries

- boss_market_score: This is a direct carry of Market Score (BT-051) from BLS Gold. No new term needed; BT-051 already covers it.
- boss_burnout_score: This is a direct carry of Burnout Score (BT-068) from O*NET Gold. No new term needed; BT-068 already covers it.

## Ambiguities Found

- **Match Quality (BT-076 vs BT-093):** The Silver crosswalk defines Match Quality (BT-076) with 5 values including "no_scorecard". The Gold Engine defines its own Match Quality (BT-093) with 4 values, derived from actual join results rather than Silver-level flags. The spec explicitly warns against using the Silver crosswalk's has_scorecard_match flag. These are distinct concepts despite sharing a name. BT-093 is the Gold-time derivation; BT-076 is the Silver-time derivation.

## Validation

Glossary validator passed: `uv run python3 -m brightsmith.infra.glossary_validator validate` returned PASS.
