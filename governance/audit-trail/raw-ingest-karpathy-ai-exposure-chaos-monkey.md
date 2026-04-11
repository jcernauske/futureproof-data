# After-Action Report: Chaos Monkey Adversarial Hardening

**Spec:** raw-ingest-karpathy-ai-exposure
**Table:** bronze.karpathy_ai_exposure (342 rows)
**Agent:** @chaos-monkey
**Date:** 2026-04-09
**Cycles completed:** 5

## Executive Summary

Ran 5-cycle adversarial DQ hardening against `bronze.karpathy_ai_exposure` with escalating corruption rates (5% through 10%). All 10 DQ dimensions were injected in every cycle. Of the 18 DQ rules, 8 rules fired at least once across cycles, 1 rule consistently errored (RAW-KAI-009), and 9 rules never fired despite relevant corruptions being injected. The consistently-firing rules (RAW-KAI-004, RAW-KAI-005) demonstrate strong detection of volume anomalies and at least one other dimension. However, the majority of corruptions --- particularly in freshness, consistency, accuracy, and referential integrity --- passed through undetected in most cycles.

## Corruption Strategy

Each cycle injected exactly 11 corruptions across all 10 DQ dimensions (1 per dimension, 2 for coverage). The low per-dimension count reflects the 5-10% injection cap against 342 rows.

| Dimension | Strategy | Target Fields |
|-----------|----------|---------------|
| Completeness | Null required fields | slug, occupation_title, exposure_score, rationale, category |
| Validity | Out-of-range scores, bad SOC formats, empty strings | exposure_score (-1, 11, 99, 999), soc_code (malformed), slug (empty) |
| Uniqueness | Exact duplicate rows | Full row duplication |
| Consistency | Mismatched field combinations | slug vs title, invalid category, wrong source_method |
| Accuracy | Plausible but wrong values | Wrong SOC prefix, swapped pay/jobs, shifted scores |
| Reasonableness | Extreme outliers | median_pay_annual (5M-99M, negative), num_jobs_2024 (500M+, negative) |
| Freshness | Stale/future timestamps | load_date (2020, 2030), ingested_at (2030) |
| Volume | Mass row duplication | Added 50-68 duplicate rows per cycle |
| Referential Integrity | Orphan SOC codes | soc_code = 90-99XX (nonexistent major groups) |
| Coverage | Category removal | Removed all rows for 2 categories per cycle |

## Per-Cycle Results

| Cycle | Rate | Corruptions | Row Count | Rules Fired | Rules Silent | Detection Rate |
|-------|------|-------------|-----------|-------------|--------------|----------------|
| 1 | 5% | 11 | 383 | 4 | 13 | 22.2% |
| 2 | 6% | 11 | 384 | 5 | 12 | 27.8% |
| 3 | 7% | 11 | 394 | 5 | 12 | 27.8% |
| 4 | 8% | 11 | 367 | 3 | 14 | 16.7% |
| 5 | 10% | 11 | 394 | 2 | 15 | 11.1% |

## Rule Fire Matrix

| Rule ID | C1 | C2 | C3 | C4 | C5 | Fire Rate |
|---------|----|----|----|----|----|----|
| RAW-KAI-001 | pass | pass | pass | pass | pass | 0/5 |
| RAW-KAI-002 | pass | pass | FAIL (3) | pass | pass | 1/5 |
| RAW-KAI-003 | FAIL (1) | pass | pass | pass | pass | 1/5 |
| RAW-KAI-004 | FAIL (63) | FAIL (58) | FAIL (64) | FAIL (57) | FAIL (56) | 5/5 |
| RAW-KAI-005 | FAIL (1) | FAIL (1) | FAIL (1) | FAIL (1) | FAIL (1) | 5/5 |
| RAW-KAI-006 | pass | FAIL (1) | FAIL (1) | pass | pass | 2/5 |
| RAW-KAI-007 | pass | pass | pass | pass | pass | 0/5 |
| RAW-KAI-008 | pass | FAIL (1) | pass | pass | pass | 1/5 |
| RAW-KAI-009 | ERROR | ERROR | ERROR | ERROR | ERROR | 0/5 (broken) |
| RAW-KAI-010 | pass | pass | pass | pass | pass | 0/5 |
| RAW-KAI-011 | pass | pass | pass | FAIL (1) | pass | 1/5 |
| RAW-KAI-012 | pass | pass | pass | pass | pass | 0/5 |
| RAW-KAI-013 | pass | pass | pass | pass | pass | 0/5 |
| RAW-KAI-014 | pass | pass | pass | pass | pass | 0/5 |
| RAW-KAI-015 | pass | pass | pass | pass | pass | 0/5 |
| RAW-KAI-016 | FAIL (1) | FAIL (2) | FAIL (1) | pass | pass | 3/5 |
| RAW-KAI-017 | pass | pass | pass | pass | pass | 0/5 |
| RAW-KAI-018 | pass | pass | pass | pass | pass | 0/5 |

## Analysis

### Rules that consistently detect corruption (strong)

- **RAW-KAI-004** (5/5 fires): Always fires with values 56-64. Likely a volume/row-count rule detecting our mass-duplication + coverage-removal creating non-standard row counts.
- **RAW-KAI-005** (5/5 fires): Always fires with value=1. Likely a uniqueness or completeness rule that our single-row corruptions reliably trigger.

### Rules that fire intermittently (threshold-dependent)

- **RAW-KAI-016** (3/5 fires): Fires when specific corruption strategies land on the right fields.
- **RAW-KAI-006** (2/5 fires): Fires inconsistently -- may have a threshold that some RNG seeds hit but others miss.
- **RAW-KAI-002, RAW-KAI-003, RAW-KAI-008, RAW-KAI-011** (1/5 fires each): Only trigger when RNG happens to select specific strategies. Very sensitive to which rows/strategies are chosen.

### Rules that never fire (potential gaps)

These 9 rules never fired across 5 cycles despite all 10 DQ dimensions being corrupted:

- **RAW-KAI-001**: Never triggered. May check a dimension/field our corruptions do not affect heavily enough (e.g., specific null thresholds on optional fields).
- **RAW-KAI-007**: Never triggered. May check a field or pattern we did not corrupt.
- **RAW-KAI-010**: Never triggered.
- **RAW-KAI-012 through RAW-KAI-015**: Block of 4 rules that never fire. May cover distribution-level or cross-row checks that single-corruption-per-dimension cannot exercise.
- **RAW-KAI-017, RAW-KAI-018**: Never triggered.

### Errored rule

- **RAW-KAI-009**: Errored on every cycle with value=None. This rule is broken in shadow mode and needs investigation. The error is consistent regardless of corruption content, suggesting a runtime issue (possibly the rule references something unavailable in shadow tables).

## Gap Recommendations for @dq-rule-writer

1. **RAW-KAI-009 is broken** -- investigate and fix the runtime error. It returned ERROR with value=None across all 5 cycles, independent of corruption content. This likely means the rule's SQL or check logic fails when run against shadow tables.

2. **Low sensitivity to single-row corruptions** -- With only 1-2 corruptions per dimension (due to the 5-10% cap on 342 rows), many rules with threshold > 1 will not fire. This is expected behavior for rules designed to catch systemic problems, but it means there are no "canary" rules that fire on even a single corruption.

3. **9 rules never fired** -- These rules (RAW-KAI-001, 007, 010, 012-015, 017, 018) may be checking:
   - Fields that we corrupted but below the rule's detection threshold
   - Dimensions or field combinations our corruption strategies did not cover
   - Cross-table referential integrity checks that shadow mode cannot evaluate
   - Distribution-level statistics that a handful of corrupted rows cannot perturb

4. **Consider adding sensitivity tests** -- Rules that require high corruption rates (>10%) to trigger may miss real-world data quality incidents that corrupt smaller slices of data.

## Information Barrier Compliance

This report was generated WITHOUT reading:
- `governance/dq-rules/raw-ingest-karpathy-ai-exposure.json`
- `governance/dq-results/` (except post-reconciliation DQ runner output)
- `governance/dq-scorecards/`

Rule behavior was observed empirically only.

## Artifacts

| Artifact | Path |
|----------|------|
| Chaos runner script | `governance/chaos-manifests/karpathy_ai_exposure_chaos_runner.py` |
| Injection manifest (JSON) | `governance/chaos-manifests/raw-ingest-karpathy-ai-exposure-manifest.json` |
| This report | `governance/audit-trail/raw-ingest-karpathy-ai-exposure-chaos-monkey.md` |
