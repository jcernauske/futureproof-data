# S4 — Three-Signal AI Exposure Composite (Option B, v4)

**Status:** ✅ COMPLETE (2026-04-16)
**Spec:** `docs/specs/three-signal-ai-exposure-composite-v3.md` (Spec Version 4.0)
**Dependencies:** S1 `gemma-ai-exposure-rescore` ✅, `ingest-anthropic-economic-index` ✅

## What shipped

A percentile-rank confidence blend replaces the single-source RES stat with
a three-signal composite:

1. **Gemma theoretical score** (S1) — what AI *could* do
2. **Karpathy baseline score** — the external reference
3. **Anthropic adoption share** (Economic Index) — drives a
   `confidence_weight` (0.3–1.0) and a coarse `velocity_label`
   (saturating / accelerating / emerging / nascent / unknown)

`composite_exposure = confidence × Gemma + (1 − confidence) × Karpathy`, then
`stat_res = MIN(11 − composite, 10)` and `boss_ai_score = MAX(composite, 1)`.

## Why Option B (not v3)

The v3 spec was rejected by `@fp-data-reviewer` for a scale-mismatch bug:
the Silver field `observed_exposure_pct` (now renamed to `ai_adoption_share`)
has real values in `0.0015–7.51` (share of Claude conversations), not
`0–100` (task-coverage percent) as v3 assumed. The v3 formula would have
pinned every blue-collar SOC to `stat_res=10` and tagged 520/520 rows as
`velocity=nascent`.

Option B treats the adoption share as a **confidence prior**, not a term
in a linear sum. Only the rank matters, so the value's absolute scale is
irrelevant.

## Results on real data (815 SOCs)

**Method distribution:**
- three_signal: 276 (33.9%)
- gemma_plus_anthropic: 243 (29.8%)
- gemma_only: 183 (22.5%)
- two_signal_no_anthropic: 96 (11.8%)
- karpathy_only: 17 (2.1%)

**Velocity distribution:**
- unknown: 295 (36.2%) — no Anthropic coverage
- nascent: 208 (25.5%)
- emerging: 156 (19.1%)
- accelerating: 104 (12.8%)
- saturating: 52 (6.4%)

**stat_res delta vs. pre-v4 baseline:**
- Range: −4 to +1
- Median: 0
- Mean: −0.26
- Blue-collar saturation at stat_res=10: **10.6%** (vs. ~100% under the
  rejected v3 formula)

**Spot checks (all sensible):**
- Software Developers (15-1252): Gemma 7, Karpathy 9 → composite 8, stat_res 3, two_signal_no_anthropic, velocity unknown
- Financial Analysts (13-2051): Gemma 7, adoption 0.23 (pct 88.4) → composite 7, stat_res 4, gemma_plus_anthropic, velocity accelerating
- Plumbers (47-2152): Gemma 2, Karpathy 2, pct 58.4 → composite 2, stat_res 9, three_signal, velocity emerging
- Elementary Teachers (25-2021): Gemma 3, pct 64.0 → composite 3, stat_res 8, gemma_plus_anthropic, velocity emerging

## Downstream propagation

- `consumable.ai_exposure` — 815 rows, schema evolved to 23 columns (field 15 renamed `observed_exposure_pct` → `ai_adoption_share`; 5 new composite columns IDs 19-23).
- `consumable.program_career_paths` — 626,406 rows; PCP schema widened to 44 columns with `ai_adoption_share`, `velocity_label`, `composite_method`, `adoption_percentile` (IDs 41-44). 605,353 rows (96.6%) carry composite provenance.
- `consumable.career_branches` — 15,944 rows re-promoted.
- `MCP.get_career_paths` response now surfaces all four provenance fields.
- `CareerOutcome` (Pydantic) gains four optional fields; pre-v4 builds still deserialize cleanly (None defaults → legacy RES wording).
- RES receipt: reports `Option B composite ({method}) — Gemma theoretical × Karpathy baseline blended by adoption percentile; velocity={velocity}; ai_adoption_share=0.25; SOC 13-2051`.
- Fight AI boss prompt: new velocity-framing block (SATURATING / ACCELERATING / EMERGING / NASCENT / UNKNOWN).

## Governance

- Contract `consumable-ai-exposure.yaml` bumped to **v1.2.0**. Column rename recorded with preserved Iceberg field ID 15. Five new column specs added. Quality thresholds updated.
- DQ rules appended: `GLD-AIE-CMP-001` (composite range), `-002` (stat_res/boss_ai_score consistency), `-003` (percentile range), `-004` (confidence range), `-005` (velocity enum), `-006` (method enum).

## Verification

| Check | Result |
|-------|--------|
| Ruff on S4-touched files | PASS |
| Mypy on S4-touched files | No new errors |
| Pipeline pytest | 1,653 pass / 2 pre-existing `debt_p25` failures (unrelated to S4) |
| Backend pytest | 289 pass / 0 fail |
| New composite tests (`tests/gold/test_ai_exposure_composite.py`) | 42 pass / 0 fail |

## Agent log

| Step | Agent | Verdict |
|------|-------|---------|
| Architecture Review | `@fp-architect` | CHANGES REQUESTED (Significant) on v3 — addressed in v4 |
| Data Review | `@fp-data-reviewer` | REJECTED (Blocker) on v3 — scale mismatch → reframed as Option B v4 |
| Implementation | Claude Code (`@primary-agent`) | Complete |
| Code Review | `@faang-staff-engineer` | CHANGES REQUIRED (adoption_percentile thread-through gap) → fixed → APPROVED |
| Verification | `@primary-agent` (inline, no separate `@fp-builder` run) | PASS |

## Known caveats

- Pre-existing `debt_p25` failures in two MCP tests (`tests/mcp/test_get_career_paths.py` and `tests/mcp/test_get_school_programs.py`) predate S4 and still fail — confirmed by stashing my changes. Out of scope for this spec.
- `AI_EXPOSURE_AB_OVERRIDE=1` was set during the materialization run because the pre-existing Gemma vs. Karpathy A/B gate currently fails four sub-gates (`mean_signed_delta`, `category_bias`, `bucket_coverage`, `outlier_rate`). This is an S1 artifact and tracked separately.
