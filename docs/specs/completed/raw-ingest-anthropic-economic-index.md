# Spec: raw-ingest-anthropic-economic-index

**Status:** DRAFT
**Zone:** Raw → Silver → Gold
**Primary Agent:** @primary-agent
**Created:** 2026-04-16
**Blocked By:** None
**Blocks:** S4 `three-signal-ai-exposure-composite`

---

## Problem Statement

Ingest Anthropic's Economic Index observed AI exposure data from the HuggingFace dataset into the FutureProof pipeline. This is the missing "observed exposure" signal needed for S4's three-signal composite.

The Anthropic Economic Index measures **actual** AI task usage across occupations — not theoretical capability (what AI *could* do) but empirical observation (what AI *is* doing). This data comes from millions of real Claude conversations mapped to O*NET tasks and SOC occupation codes.

Combined with Gemma's theoretical scoring (S1), this enables the S4 three-signal composite: theoretical ceiling × observed adoption × velocity.

---

## Data Source

- **Source:** HuggingFace dataset `Anthropic/EconomicIndex`
- **License:** CC-BY 4.0 (open for commercial use with attribution)
- **Primary release:** `release_2026_03_24/` (latest with Opus 4.5/4.6 data)
- **Fallback releases:** `release_2026_01_15/`, `release_2025_03_27/`
- **User-Agent:** FutureProof/0.1 (jeff@hyenastudios.com)

### Key Files

| File | Description | Est. Rows |
|------|-------------|-----------|
| `task_pct_v2.csv` | Task-level AI usage percentages by O*NET task ID | ~3,500 |
| `automation_vs_augmentation_by_task.csv` | Automation vs augmentation breakdown per task | ~3,500 |
| `onet_task_statements.csv` | O*NET task IDs mapped to task descriptions | ~19,000 |
| `SOC_Structure.csv` | SOC hierarchy (major groups, detailed codes) | ~900 |
| `onet_task_mappings.csv` | O*NET task → SOC occupation mapping | ~19,000 |

### Aggregation Logic

The Anthropic data is at O*NET **task** level. FutureProof operates at **occupation** (SOC) level. We aggregate:

```python
# For each SOC code:
#   1. Get all O*NET tasks mapped to that SOC
#   2. For each task, get task_pct (% of Claude usage on this task)
#   3. Weight by task prevalence within occupation
#   4. Produce occupation-level observed_exposure_pct

observed_exposure_pct = sum(task_pct * task_weight) / sum(task_weight)
```

**Clarification needed from EDA:** Determine if `task_pct` is global % (sum = 100%) or per-task % (each 0-100 independently).

---

## Success Criteria

- [ ] HuggingFace dataset cloned to `data/raw/anthropic_economic_index/`
- [ ] Raw data lands in Iceberg table `raw.anthropic_economic_index`
- [ ] Silver base table `base.anthropic_observed_exposure` with SOC-level aggregation
- [ ] Gold update: `consumable.ai_exposure` gains `observed_exposure_pct`, `automation_pct` columns
- [ ] SOC join coverage ≥ 80% against `consumable.occupation_profiles`
- [ ] DQ rules passing at each zone
- [ ] Data provenance: source release version tracked
- [ ] CC-BY attribution documented in `LICENSE_SOURCES.md`

---

## Zone 0: Data Acquisition

### Clone Script

```bash
cd ~/code/bright/futureproof-data/data/raw
git clone https://huggingface.co/datasets/Anthropic/EconomicIndex anthropic_economic_index
cd anthropic_economic_index
git lfs pull
```

### Release Selection

Check for releases in order of preference:
1. `release_2026_03_24/` (latest)
2. `release_2026_01_15/`
3. `release_2025_03_27/`

Use the first one that contains `task_pct_v2.csv`.

### Offline Fallback

If `git clone` or `git lfs pull` fails (network error, HuggingFace rate limit, git-lfs unavailable):

1. Check `data/raw/anthropic_economic_index_cache/` for last successful clone
2. If cache exists and is <30 days old, use cached files with warning log
3. If cache is stale (>30 days), use cached files with warning + flag for manual update
4. If no cache exists, fail with clear error:
   ```
   ERROR: Cannot fetch Anthropic Economic Index and no cache available.
   Manual action required: Clone dataset manually or check network.
   ```

Cache refresh on successful clone:
```bash
cp -r data/raw/anthropic_economic_index/release_*/ data/raw/anthropic_economic_index_cache/
```

---

## Zone 1: Bronze (Raw Ingest)

### Iceberg Table: raw.anthropic_economic_index

- **Grain:** One row per (O*NET task, SOC code) pair — composite.
  Task-to-SOC is many-to-many in O*NET (up to 34-way fan-out); a task
  mapping to N distinct SOCs produces N Bronze rows with
  `task_pct = raw_pct / N` so the global 100% invariant is preserved
  across the fan-out.
- **Dedup grain:** `[task_id, soc_code]` — composite key.
- **Expected rows:** **4,082** for `release_2025_03_27`, derived as:
  - 3,365 source tasks in `task_pct_v2.csv`
  - 1 is the `task_name='none'` placeholder (no O*NET mapping) →
    1 Bronze row with `soc_code=NULL`
  - 3,364 tasks join to O*NET task statements
  - Of those, 82 tasks fan out to ≥2 distinct SOCs (max 34-way)
  - Total SOC-matched (task, SOC) pairs = 4,081
  - Total Bronze rows = 4,081 + 1 = **4,082**
  - Tolerance band: 3,800–4,400 rows.

### Ingestor

- **Class:** `AnthropicEconomicIndexIngestor` (extends `BaseIngestor`)
- **Location:** `src/raw/anthropic_economic_index_ingestor.py`

### Implementation Notes

1. Read `task_pct_v2.csv` — columns: `task_name`, `pct` (global share
   in 0-100 percent units; source column sums to 100.0).
2. Read `automation_vs_augmentation_by_task.csv` — columns:
   `task_name`, `feedback_loop`, `directive`, `task_iteration`,
   `validation`, `learning`, `filtered` (6-axis fractions summing to
   1.0 per row).
3. Read `onet_task_statements.csv` — used as the SOC bridge; task text
   is the join key (case-insensitive, trailing "." stripped).
4. LEFT JOIN on normalized task text; for each task, emit one Bronze
   row **per distinct SOC** the task maps to.
5. Split `task_pct = raw_pct / n_soc_per_task` so the per-(task, SOC)
   value is comparable to the original global share.
6. Collapse automation via Anthropic v2 methodology:
   - `automation_pct = (directive + feedback_loop) * 100`
   - `augmentation_pct = (task_iteration + validation + learning) * 100`
   - `learning` is user-learns-from-Claude → Claude is assisting →
     contributes to **augmentation**, NOT automation.
   - When `filtered >= 0.999`, both fields emit None.
7. Keep the `task_name='none'` placeholder row with `soc_code=NULL`
   and `task_pct` unchanged (no split) — Silver excludes it from
   per-SOC aggregation.

### Raw Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| task_id | string | yes | O*NET task identifier (part of composite grain; not unique alone — a task fanning out to N SOCs produces N rows sharing this task_id) |
| task_statement | string | yes | Task description text |
| soc_code | string | no | SOC code (XX-XXXX). Part of composite grain. NULL only for the `task_name='none'` placeholder row. |
| soc_title | string | no | Occupation title |
| task_pct | double | no | Per-(task, SOC) share of global Claude conversations, already split across the fan-out. Value = `raw_source_pct / n_soc_per_task`. Units: 0-100 percent. |
| automation_pct | double | no | (directive + feedback_loop) × 100. NOT including learning. |
| augmentation_pct | double | no | (task_iteration + validation + learning) × 100. |
| source_release | string | yes | e.g. "release_2025_03_27" |
| ingested_at | timestamp | yes | |
| source_url | string | yes | HuggingFace dataset URL |
| source_method | string | yes | "hf_git_clone" |
| load_date | date | yes | |

### Bronze DQ Rules

| Priority | Rule | Threshold |
|----------|------|-----------|
| P0 | (task_id, soc_code) composite uniqueness | 0 duplicates |
| P0 | task_pct range | 0 ≤ x ≤ 100 |
| P0 | `SUM(task_pct)` across all rows | ≈ 100 ±0.1 (global share invariant; fan-out preserves source total) |
| P0 | Row count | 3,800–4,400 (observed 4,082 at `release_2025_03_27`) |
| P1 | `automation_pct + augmentation_pct + filtered*100 ≈ 100` (for non-fully-filtered rows) | ±1% tolerance |
| P1 | soc_code non-null | ≥ 99% (exactly 1 null expected: `task_name='none'`) |
| P1 | task_statement non-null | 100% |

---

## Zone 2: Silver (Aggregate to SOC Level)

### Iceberg Table: base.anthropic_observed_exposure

- **Grain:** One row per SOC code
- **Dedup grain:** [soc_code]
- **Promote pattern:** `compute_grain_id(row, ['soc_code'], prefix='aoe')`

### Transformer

- **Class:** `AnthropicObservedExposureTransformer`
- **Location:** `src/silver/anthropic_observed_exposure_transformer.py`

### Silver Transformations

1. **SOC normalization:** Standardize to XX-XXXX format. Expand broad codes (XX-XXX0) where possible via SOC hierarchy.

2. **Task aggregation per SOC:**
   ```python
   # Weighted mean — task_pct as weight
   observed_exposure_pct = sum(task_pct) / count(tasks)  # if task_pct is per-task
   # OR
   observed_exposure_pct = sum(task_pct)  # if task_pct is global share
   ```
   
3. **Automation ratio:**
   ```python
   automation_pct = weighted_avg(task.automation_pct, weights=task.task_pct)
   ```

4. **SOC match flag:** `soc_match = true` if soc_code exists in `base.bls_ooh`.

### Silver Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| record_id | string | yes | Grain hash (prefix: `aoe`) |
| soc_code | string | yes | Normalized XX-XXXX |
| soc_title | string | yes | |
| observed_exposure_pct | double | yes | Aggregated observed AI exposure (0-100) |
| automation_pct | double | no | Weighted automation % |
| augmentation_pct | double | no | Weighted augmentation % |
| task_count | int | yes | Number of tasks aggregated |
| soc_match | boolean | yes | True if soc_code exists in BLS data |
| source_release | string | yes | |
| promoted_at | timestamp | yes | |

### Silver DQ Rules

| Priority | Rule | Threshold |
|----------|------|-----------|
| P0 | soc_code uniqueness | 0 duplicates |
| P0 | observed_exposure_pct range | 0 ≤ x ≤ 100 |
| P0 | soc_match = true | ≥ 80% of rows |
| P0 | Row count | 700–900 |
| P0 | task_count ≥ 1 | 100% |

---

## Zone 3: Gold (Merge into consumable.ai_exposure)

### Schema Evolution: consumable.ai_exposure

Add new columns:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| observed_exposure_pct | double | no | From Anthropic (0-100) |
| automation_pct | double | no | From Anthropic (0-100) |
| anthropic_task_count | int | no | Tasks in aggregation |
| anthropic_source_release | string | no | e.g. "release_2026_03_24" |

### Gold Transformer Update

- **File:** `src/gold/ai_exposure_transformer.py`
- **Change:** LEFT JOIN `base.anthropic_observed_exposure` on `soc_code`

```python
def transform(self):
    # Existing: Gemma + Karpathy blending
    existing_df = self.load_existing_ai_exposure()
    
    # New: LEFT JOIN Anthropic observed exposure
    anthropic_df = self.load_table("base.anthropic_observed_exposure")
    
    result = existing_df.join(
        anthropic_df.select(
            "soc_code",
            "observed_exposure_pct",
            "automation_pct",
            col("task_count").alias("anthropic_task_count"),
            col("source_release").alias("anthropic_source_release"),
        ),
        on="soc_code",
        how="left",
    )
    return result
```

### Gold DQ Rules

| Priority | Rule | Threshold |
|----------|------|-----------|
| P1 | observed_exposure_pct populated | ≥ 70% of rows |
| P1 | automation_pct populated where observed_exposure_pct present | 100% |
| P2 | No change to existing stat_res/boss_ai_score | Regression test |

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `data/raw/anthropic_economic_index/` | Create | HuggingFace clone |
| `data/raw/anthropic_economic_index_cache/` | Create | Offline fallback cache |
| `src/raw/anthropic_economic_index_ingestor.py` | Create | Bronze ingestor |
| `src/silver/anthropic_observed_exposure_transformer.py` | Create | Silver aggregation |
| `src/gold/ai_exposure_transformer.py` | Modify | Add Anthropic JOIN |
| `LICENSE_SOURCES.md` | Modify | Add CC-BY attribution |
| `governance/data-contracts/raw-anthropic-economic-index.yaml` | Create | Bronze contract |
| `governance/data-contracts/base-anthropic-observed-exposure.yaml` | Create | Silver contract |
| `governance/data-contracts/consumable-ai-exposure.yaml` | Modify | Add Anthropic fields |

---

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @primary-agent — Clone HF dataset, implement ingestor + transformers
3. @data-analyst — EDA: column names, row counts, task_pct distribution, SOC coverage, aggregation strategy
4. @domain-context — Append Anthropic Economic Index section to domain-context.md
5. @dq-rule-writer — Write DQ rules for Bronze + Silver
6. @dq-engineer — Execute rules, produce scorecards
7. @chaos-monkey — Adversarial hardening (5 cycles)
8. @lineage-tracker — OpenLineage capture (Bronze + Silver + Gold)
9. @cde-tagger — CDE/PII mapping
10. @doc-generator — Data dictionary entries + LICENSE_SOURCES.md update
11. @governance-reviewer — Post-implementation check
12. @staff-engineer — Final review

---

## Testing Approach

### Test Files

| File | Coverage |
|------|----------|
| `tests/raw/test_anthropic_economic_index_ingestor.py` | Bronze ingestor |
| `tests/silver/test_anthropic_observed_exposure_transformer.py` | Silver aggregation |
| `tests/gold/test_ai_exposure_transformer_anthropic.py` | Gold JOIN |

### Fixtures

Location: `tests/fixtures/anthropic_economic_index/`

| Fixture | Rows | Purpose |
|---------|------|---------|
| `task_mappings_sample.csv` | 50 | Normal tasks across 10 SOC codes |
| `task_pct_sample.csv` | 50 | Matching task_pct values |
| `automation_sample.csv` | 50 | Matching automation/augmentation splits |

Edge cases in fixtures:
- 0% exposure tasks
- 100% exposure tasks
- Missing SOC code (null)
- Broad SOC code (XX-XXX0)
- Task with no automation/augmentation data

### Chaos Manifest

Location: `governance/chaos-manifests/raw-anthropic-economic-index-chaos.md`

| Scenario | Expected Behavior |
|----------|-------------------|
| Network failure during git clone | Use cache if available, else fail with clear error |
| git-lfs not installed | Detect and fail with install instructions |
| Malformed CSV headers | Fail fast with column name mismatch error |
| Missing required columns | Fail fast listing missing columns |
| SOC code format variations | Normalize XX-XXX0 → XX-XXXX where possible |
| Empty task_pct file | Fail with "no task data" error |
| Duplicate task_ids | Dedupe on ingest, log warning |

---

## Attribution Requirements

### CC-BY 4.0 Compliance

Add to `LICENSE_SOURCES.md`:

```markdown
## Anthropic Economic Index

- **Source:** https://huggingface.co/datasets/Anthropic/EconomicIndex
- **License:** CC-BY 4.0 International
- **Citation:** "Economic Index Dataset, Anthropic (2026)"
- **Used in:** consumable.ai_exposure (observed_exposure_pct, automation_pct)
- **Attribution requirement:** Credit Anthropic in any published analysis using this data
```

### Data Contract License Block

Add to `governance/data-contracts/raw-anthropic-economic-index.yaml`:

```yaml
license:
  type: CC-BY-4.0
  attribution: "Economic Index Dataset, Anthropic (2026)"
  url: https://huggingface.co/datasets/Anthropic/EconomicIndex
  requires_citation: true
```

---

## Governance Artifacts

- [ ] EDA report: `governance/eda/raw-anthropic-economic-index-eda.md`
- [ ] Domain context: `governance/domain-context.md` (append Anthropic section)
- [ ] Data contract (Bronze): `governance/data-contracts/raw-anthropic-economic-index.yaml`
- [ ] Data contract (Silver): `governance/data-contracts/base-anthropic-observed-exposure.yaml`
- [ ] Data contract (Gold): `governance/data-contracts/consumable-ai-exposure.yaml` (update)
- [ ] DQ rules (Bronze): `governance/dq-rules/raw-anthropic-economic-index.json`
- [ ] DQ rules (Silver): `governance/dq-rules/silver-anthropic-observed-exposure.json`
- [ ] DQ scorecard: `governance/dq-scorecards/raw-anthropic-economic-index-scorecard.md`
- [ ] Chaos manifest: `governance/chaos-manifests/raw-anthropic-economic-index-chaos.md`
- [ ] Lineage (Bronze): `governance/lineage/raw-anthropic-economic-index-{timestamp}.json`
- [ ] Lineage (Silver): `governance/lineage/silver-anthropic-observed-exposure-{timestamp}.json`
- [ ] Lineage (Gold): `governance/lineage/gold-ai-exposure-anthropic-{timestamp}.json`
- [ ] Attribution: `LICENSE_SOURCES.md` entry
- [ ] Data dictionary entries for all new fields
- [ ] Staff review: `governance/reviews/raw-anthropic-economic-index-staff-review.md`

---

## Governance Review (Pre-Implementation)

**Verdict:** APPROVED (with ADVISORIES)
**Reviewer:** @governance-reviewer
**Date:** 2026-04-16
**Report:** `governance/reviews/raw-anthropic-economic-index-governance-pre.md`

**Summary:** Spec is implementation-ready. Problem statement, success criteria, per-zone schemas, DQ rules (P0/P1/P2 tiered with testable thresholds), chaos manifest, and CC-BY 4.0 attribution plan are all in place. Six advisories logged — all minor execution-time clarifications, none blocking:

1. Clarify `@primary-agent` to concrete agent names before kickoff (`@raw-ingestor` / `@silver-transformer` / `@gold-transformer`)
2. `LICENSE_SOURCES.md` does not yet exist at project root — action verb should be "Create", not "Modify"
3. No explicit path listed for the Gold DQ rules file covering the 3 new Gold rules
4. EDA must resolve whether `task_pct` is global or per-task % before Silver transformer lands
5. CDE/PII pre-assessment deferred to @cde-tagger (expected: no PII, likely no CDE)
6. Fixture row count (50) may need expansion for SOC normalization edge cases

Implementation may proceed.

---

## EDA Results

**Agent:** @data-analyst
**Date:** 2026-04-16
**Full report:** `governance/eda/raw-anthropic-economic-index-eda.md`
**Release used:** `release_2025_03_27` (later releases `release_2026_01_15` / `release_2026_03_24` only contain raw conversation snapshots and lack `task_pct_v2.csv`).

### File Inventory

| File | Rows | Columns | Grain | Notes |
|------|-----:|--------:|-------|-------|
| `task_pct_v2.csv` | 3,365 | 2 | task_name (text) | `pct` is **global share in percent units**; sum across all rows = 100.0000. One placeholder row `task_name='none'` (pct=1.78) for uncategorized conversations — **must be filtered in Silver**. |
| `automation_vs_augmentation_by_task.csv` | 3,364 | 7 | task_name (text) | Five mode fractions + `filtered`; every row's 6 columns sum to exactly 1.0. No `none` placeholder. |
| `onet_task_statements.csv` | 19,530 | 8 | O*NET-SOC × Task ID | SOC bridge. 18,428 unique task strings (after lowercase/rstrip-period normalization). Task→SOC is many-to-many: 272 tasks map to ≥2 SOCs (max 34). |
| `SOC_Structure.csv` | 1,596 | 6 | SOC hierarchy row | Reference taxonomy; not joined. |

**Join-key reality:** Files share `task_name` (free-text, not `task_id`). After normalization, 3,364 / 3,365 Anthropic tasks match an O*NET task statement (99.97%). The unmatched row is `"none"`.

### Column Definitions

`task_pct_v2.pct` — **double, 0–100 percent units.** Global share of classified Claude conversations attributed to this task statement. Range [0.001541, 6.650740]; median 0.005444; sum = 100.0000.

`automation_vs_augmentation_by_task.*` — 5 interaction-mode fractions + residual:
- `directive`, `feedback_loop` → **automation** (Claude acts)
- `task_iteration`, `validation`, `learning` → **augmentation** (Claude assists)
- `filtered` → conversations removed by safety/classifier filters (residual)
- Row sum of all 6 columns = 1.0 for every row (P0 invariant).

`onet_task_statements` — `O*NET-SOC Code` is `XX-XXXX.NN` detailed format; strip `.NN` to get base SOC. `Task` text is the join key.

### Aggregation Strategy Decision

**Chosen strategy: sum-of-global-shares with N-way task split.**

```python
# Drop placeholder
df = pct[pct["task_name_norm"] != "none"]
df = df.merge(aut, on="task_name_norm")
df = df.merge(onet[["task_name_norm","soc_code"]], on="task_name_norm")

# Preserve 100% invariant across multi-SOC fan-out
df["n_soc"]     = df.groupby("task_name_norm")["soc_code"].transform("nunique")
df["pct_split"] = df["pct"] / df["n_soc"]

agg = df.groupby("soc_code").agg(
    observed_exposure_pct = ("pct_split", "sum"),                                    # 0-100 percent units
    task_count            = ("task_name_norm", "nunique"),
    automation_pct        = weighted_mean("directive"+"feedback_loop",   w="pct_split"),
    augmentation_pct      = weighted_mean("task_iteration"+"validation"+"learning", w="pct_split"),
    filtered_pct          = weighted_mean("filtered",                    w="pct_split"),
)
```

**Justification (full math in EDA report):**
- `pct` is already a share of a fixed 100% denominator — **summing** preserves the "% of Claude traffic for this SOC" interpretation; averaging destroys it.
- Tasks fan out to multiple SOCs (max 34). **Splitting `pct / N`** conserves the global invariant `sum(observed_exposure_pct) ≈ 100 - 1.78 ("none") = 98.22`.
- Automation/augmentation/filtered use **`pct_split`-weighted means** (volume-weighted) and satisfy `automation + augmentation + filtered ≈ 1.0` per SOC after aggregation (verified mean 1.000000 across 588 SOCs).

**Rejected:**
- Unweighted mean of `pct` per SOC → produces meaningless ~0.03 average.
- Sum without split → inflates totals by up to 34× for max-fan-out tasks; global sum ~118 violates invariant.

**Silver schema units:**
- `observed_exposure_pct`: 0–100 (percent units — matches FutureProof convention).
- `automation_pct` / `augmentation_pct` / `filtered_pct`: 0–1 mode fractions in raw form; @semantic-modeler should decide whether to scale × 100 for naming consistency.

### SOC Coverage

| Metric | Value |
|--------|------:|
| Unique SOC codes in source (Anthropic via O*NET) | 588 |
|  of which detailed (XX-XXXX, last digit ≠ 0) | 587 |
|  of which broad (XX-XXX0) | 1 (`19-1020`) |
| Unique SOC codes in target (`consumable.occupation_profiles`) | 832 |
|  detailed / broad / catchall-flagged | 825 / 7 / 70 |
| **SOC codes matching (target ∩ source)** | **510** |
| **Coverage % (vs all target SOCs)** | **61.30%** |
| Coverage vs. non-catchall target SOCs (762) | 64.44% |
| Coverage vs. non-broad target SOCs (825) | 61.82% |
| Source SOCs present in target (reverse direction) | 510 / 588 = 86.73% |

**Action:** The 80% coverage target in Success Criteria is not achievable at this release — Claude's traffic is heavily skewed toward knowledge work, so 315 target SOCs in trades/production/transport/food-service have zero Anthropic tasks mapped. **Revise Silver P0 threshold from ≥80% to ≥60%** and document this as a known dataset limitation in the data contract. This is not an ingestor defect.

Per-SOC task volume (source side): min 1, median 4, mean 6.94, max 141 (`15-1199`, the O*NET umbrella covering 12 emerging-tech sub-occupations).

---

## Post-Completion

Once this spec completes:
1. Update S4 spec (`three-signal-ai-exposure-composite.md`) to reference `base.anthropic_observed_exposure`
2. S4 can proceed with three-signal composite formula implementation

---

*— End of Spec —*
