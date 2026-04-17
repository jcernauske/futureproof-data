# Audit Trail: DQ Rules for Anthropic Economic Index

**Agent:** @dq-rule-writer
**Date:** 2026-04-16
**Spec:** `docs/specs/raw-ingest-anthropic-economic-index.md`
**Evidence:** `governance/eda/raw-anthropic-economic-index-eda.md`
**Domain context:** `governance/domain-context.md` (Anthropic Economic Index section)

## Files written

- `governance/dq-rules/raw-anthropic-economic-index.json` — 18 Bronze rules
- `governance/dq-rules/silver-anthropic-observed-exposure.json` — 15 Silver rules
- `governance/dq-rules/gold-ai-exposure-anthropic.json` — 8 Gold rules

Gold rules were placed in a **new file** (not appended to `gold-ai-exposure.json`) because the existing Gold rules file is already approved/signed and this spec is an additive schema evolution. This mirrors the `gold-futureproof-engine-backfill-ai.json` precedent.

## Rule counts

| Zone | P0 | P1 | P2 | P3 | Total |
|------|---:|---:|---:|---:|------:|
| Bronze | 8 | 7 | 2 | 0 | 18 |
| Silver | 8 | 5 | 1 | 1 | 15 |
| Gold | 2 | 3 | 3 | 0 | 8 |
| **Total** | **18** | **15** | **6** | **1** | **41** |

## Threshold divergences from spec

| Rule | Spec said | Written as | Why |
|------|-----------|------------|-----|
| `SLV-AOE-004` (Silver row count) | 700-900 | 500-650 | EDA revealed actual is 588 SOCs (spec was pre-EDA optimistic estimate). Band centered on observed count. |
| `SLV-AOE-006` (SOC match coverage) | >= 80% | >= 60% | EDA: actual 61.3% (510/832). Claude traffic skews to knowledge work; 315 target SOCs in trades/production/transport/food-service have zero Anthropic tasks. Dataset limitation, not ingestor defect. |
| `GLD-AIE-ANT-001` (observed_exposure_pct populated) | >= 70% | >= 60% | Bounded above by Silver SOC-match rate (61.3%). Even a perfect LEFT JOIN can't exceed 61.3%, so 70% was unreachable. Propagates the Silver 60% floor. |

All three divergences flow from the same EDA finding: Anthropic's SOC overlap with `consumable.occupation_profiles` is 61.3%, not the 80% the spec originally targeted.

## Grain uniqueness NULL-handling decision

Bronze composite grain `(task_id, soc_code)` includes one expected NULL `soc_code` row (the `task_name='none'` placeholder). Rule `RAW-AEI-001` coalesces NULL to a sentinel `'__NULL__'` so the placeholder participates in the uniqueness check. This is safe because exactly one NULL is expected, and the coalesce lets the rule detect a future second NULL as a duplicate (rather than silently tolerating unlimited NULL-soc rows).

## Adversarial-pattern coverage (per pattern in `governance/dq-rule-templates/adversarial-patterns.json`)

Structural integrity:
- **ADV-GRAIN-UNIQUE** — Bronze: `RAW-AEI-001`. Silver: `SLV-AOE-001`, `SLV-AOE-008`.
- **ADV-FK-VALID** — Bronze: `RAW-AEI-008` (SOC format validates joinability to BLS/O*NET SOC universe). Silver: `SLV-AOE-006` (soc_match coverage against `consumable.occupation_profiles`), `SLV-AOE-007` (SOC format).
- **ADV-CROSS-COLUMN** — Bronze: `RAW-AEI-009`, `RAW-AEI-010`, `RAW-AEI-012`. Silver: `SLV-AOE-009`, `SLV-AOE-010`. Gold: `GLD-AIE-ANT-002` (consistency of populated Anthropic fields), `GLD-AIE-ANT-007` (regression vs pre-Anthropic baseline).

Semantic validity:
- **Impossible values** — `RAW-AEI-004` (task_pct 0-100), `SLV-AOE-002` (observed_exposure_pct 0-100), `SLV-AOE-011` (automation/augmentation 0-1), `GLD-AIE-ANT-004`, `GLD-AIE-ANT-005`.
- **Cross-column sum invariants** — `RAW-AEI-003` (global share sum = 100), `SLV-AOE-003` (global share sum = 98.22 after 'none' drop), `RAW-AEI-009`, `RAW-AEI-012`, `SLV-AOE-009`.
- **ADV-TEMPORAL-ORDER** — N/A for this dataset. Anthropic Economic Index is a snapshot with no per-row temporal fields (no start/end dates, no period_begin/period_end). The only date field is `load_date`. Documented as N/A per this audit.

Distribution expectations:
- **Row count range** — `RAW-AEI-002` (Bronze 3800-4400), `SLV-AOE-004` (Silver 500-650).
- **ADV-VALUE-RANGE** — `RAW-AEI-013` (pct>1 outliers must map to expected SOCs), `SLV-AOE-014` (observed_exposure_pct > 5 count tracking).
- **ADV-DISTRIBUTION-VARIANCE** — `RAW-AEI-018` (fully-filtered task share 25-38%), `SLV-AOE-015` (low-confidence task_count=1 rate tracked).

Coverage guarantees:
- **ADV-ENTITY-COVERAGE** — `SLV-AOE-006` (SOC match coverage >= 60%), `GLD-AIE-ANT-001` (Anthropic field population >= 60%).
- **ADV-PERIOD-COVERAGE** — N/A. Single snapshot; no period dimension.
- **Freshness** — `RAW-AEI-015` (30-day load_date), `RAW-AEI-017` (placeholder row preserved), `SLV-AOE-012` and `GLD-AIE-ANT-008` (source release pinned).

Provenance:
- `RAW-AEI-011` (source_release), `RAW-AEI-014` (source_url + attribution), `RAW-AEI-016` (source_method). Silver: `SLV-AOE-012` (pinned release). Gold: `GLD-AIE-ANT-003`, `GLD-AIE-ANT-008`.

Placeholder integrity (Anthropic-specific):
- `RAW-AEI-017` — exactly one `task_name='none'` row with NULL soc_code preserved in Bronze (Silver filters it). This is the headline invariant from EDA Edge Case #1.

## Consumable-pattern evaluation (per `governance/dq-rule-templates/consumable-patterns.json`)

Gold file augments an existing Gold table (`consumable.ai_exposure`); grain-level patterns are already enforced by `governance/dq-rules/gold-ai-exposure.json` and not re-stated here. This spec's Gold rules focus on the incremental Anthropic columns.

- **CONS-GRAIN-UNIQUE** — Covered by existing `GLD-AIE-001` in `gold-ai-exposure.json`. Not duplicated.
- **CONS-IMPOSSIBLE-VALUE** — `GLD-AIE-ANT-004`, `GLD-AIE-ANT-005`, `GLD-AIE-ANT-006`.
- **CONS-CROSS-TABLE** — `GLD-AIE-ANT-007` (regression vs pre-Anthropic baseline snapshot) covers the "added column must not mutate existing columns" cross-version consistency.
- **CONS-GOLDEN-DATASET** — No golden dataset for Anthropic-sourced columns exists yet. Not written; flagged for @primary-agent to author 3+ verifiable values (e.g., expected `observed_exposure_pct` for well-known SOCs like 15-1252 Software Developers, 15-1212 Information Security Analysts, 25-2021 Elementary School Teachers). Marked as DEFERRED in this audit; requires human override to close without creation.
- **CONS-COLLISION-RESOLVED** — N/A. No concept normalization at this layer (SOC is a single canonical taxonomy; O*NET `.NN` sub-codes are collapsed to base SOC at Bronze, not collided).
- **CONS-COVERAGE-FLOOR** — `GLD-AIE-ANT-001` (>= 60%) serves as the coverage floor.

## Rules considered but not written

- **Broad-SOC expansion check** — EDA notes one broad SOC `19-1020` slips through. Not written as a separate rule because `SLV-AOE-007` (XX-XXXX format) already accepts broad codes (both detailed `XX-XXXX` where last digit != 0 and broad `XX-XXX0` match the regex). A future refinement could split detailed-vs-broad coverage; left out for now since the single broad code is documented and intended.
- **Per-SOC automation share distribution bounds** — EDA shows automation share mean 0.357 across 588 SOCs with heterogeneous distribution; no tight bound is defensible without more domain input. Left unwritten; `SLV-AOE-011` (range 0-1) and `SLV-AOE-009` (sum invariant) cover the must-hold case.
- **Task-count ceiling** — EDA max is 141 tasks for one SOC (`15-1199`). Not written because there's no defensible upper bound — 141 is expected for catchall codes.

## Next steps

- @dq-engineer executes all 41 rules against the actual Bronze/Silver/Gold tables and produces scorecards. Any rule that fails at initial execution needs threshold revisit.
- @primary-agent creates `consumable.ai_exposure_baseline_pre_anthropic` snapshot (or equivalent) to make `GLD-AIE-ANT-007` executable, or archives that rule.
- @primary-agent or human: author golden dataset for Anthropic-sourced Gold columns to unblock `CONS-GOLDEN-DATASET` pattern (currently DEFERRED).
- @governance-reviewer post-implementation review validates threshold divergences and audit trail.
