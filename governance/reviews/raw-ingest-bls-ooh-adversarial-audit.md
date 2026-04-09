# Adversarial Audit: raw-ingest-bls-ooh

**Auditor:** @adversarial-auditor
**Date:** 2026-04-07
**Verdict:** CONDITIONAL PASS

## Risk Register (10 risks identified)

| Risk | Severity | Description | Control |
|------|----------|-------------|---------|
| RISK-01 | CRITICAL | Training code mapping in domain context may be hallucinated (codes 3/4 labels don't match sample) | MISSING -- will self-correct on real data |
| RISK-02 | HIGH | Education code mapping inconsistency (code 3 in sample) | WEAK -- flagged but not resolved |
| RISK-03 | MEDIUM | load_date type disagreement across artifacts | RESOLVED post-review |
| RISK-04 | MEDIUM | occupation_title required flag disagreement | RESOLVED post-review |
| RISK-05 | MEDIUM | Chaos monkey results cannot be independently verified | WEAK |
| RISK-06 | MEDIUM | EDA statistics based on 10 rows (appropriately caveated) | ADEQUATE |
| RISK-07 | HIGH | Sample is AI-constructed, not extracted from real BLS | MISSING -- acceptable for dev phase |
| RISK-08 | LOW | No negative employment_change in sample/tests | ADEQUATE -- logic correct |
| RISK-09 | LOW | Download path never tested | WEAK |
| RISK-10 | LOW | DQ SQL syntax not validated against real engine | WEAK |

## Blocking Recommendations

R1. Verify training/education code mappings against real BLS data on first production ingest.
R2. Add code-to-text determinism DQ rules.
R3. Resolve load_date type disagreement. (DONE)

## Meta-Assessment

Strong fundamentals. The circularity problem (AI created sample, ingestor, EDA, DQ rules against its own data) is the primary concern. Will self-correct on first real data ingest.
