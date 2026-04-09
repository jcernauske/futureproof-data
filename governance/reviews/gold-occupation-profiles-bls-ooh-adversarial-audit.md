# Adversarial Audit: gold-occupation-profiles-bls-ooh

**Auditor:** @adversarial-auditor
**Date:** 2026-04-07
**Spec:** gold-occupation-profiles-bls-ooh
**Table:** consumable.occupation_profiles (832 rows)
**Zone:** Gold (Consumable)

## Summary

14 risks identified across 4 severity levels. 3 P0 items, 4 P1 items, 7 P2/advisory items.

## P0 Findings (Fix Before Production)

### RISK-01: GLD-OP-039 Market Score Formula Rule is Broken

The DQ rule intended to verify market_score = 0.6 * grw_score + 0.4 * openings_score uses a correlated subquery with PERCENT_RANK that DuckDB cannot execute correctly. Shows 828 false violations. Must be rewritten using CTE-based approach.

**Resolution:** Rule must be rewritten by @dq-rule-writer.

### RISK-02: No GRW Piecewise Spot-Check DQ Rule

No DQ rule validates that grw_score matches the piecewise linear function for a given employment_change_pct. A miscoded breakpoint would be undetectable by existing rules.

**Resolution:** Add boundary-condition spot-check rules for at least 3 golden dataset values.

### RISK-03: Null-Openings Latent Bug

The openings_ranked CTE did not exclude null openings_annual_avg from PERCENT_RANK, which would produce inflated openings_score (10.0) for null-openings rows. In current data 0 nulls exist, but future data could trigger this.

**Resolution:** FIXED post-audit. Added WHERE clause to openings_ranked CTE and Python-side null check on raw openings_annual_avg.

## P1 Findings

- RISK-07: Golden dataset rule GLD-OP-048 is deferred -- no automated production validation
- RISK-09: No freshness DQ rules for source_load_date or promoted_at
- RISK-10: No record_id hash integrity validation rule
- RISK-08: Staff review artifact pending (expected -- next pipeline step)

## Strengths

- Wage percentile null handling is excellent (filtered CTE + LEFT JOIN)
- GRW piecewise function has strong unit test coverage (14 cases, all 8 segments)
- Confidence tier priority logic thoroughly tested (null-wage + catchall edge case)
- EDA caught a real spec error (golden dataset #3 SOC code)
- Cross-column consistency rules are comprehensive (11 rules)
- Chaos monkey was genuinely adversarial (5 cycles, honest gap analysis)

## Open Decisions

- GRW score breakpoints: AI-proposed, human verbally approved but no documented artifact
- Market score 60/40 weighting: AI-proposed, human verbally approved but no documented artifact
- Recommendation: Document these business decisions formally before cross-source integration
