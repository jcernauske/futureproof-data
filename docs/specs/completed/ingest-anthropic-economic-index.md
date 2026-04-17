# Spec: ingest-anthropic-economic-index

**Status:** COMPLETE
**Zone:** Raw → Silver → Gold
**Primary Agent:** @fp-data-reviewer
**Created:** 2026-04-16
**Blocked By:** None
**Blocks:** S4 `three-signal-ai-exposure-composite`

---

## Problem Statement

Ingest Anthropic's Economic Index observed AI exposure data from the HuggingFace dataset into the FutureProof pipeline. This is the missing "observed exposure" signal needed for S4's three-signal composite.

The Anthropic Economic Index measures **actual** AI task usage across occupations — not theoretical capability (what AI *could* do) but empirical observation (what AI *is* doing). This data comes from millions of real Claude conversations mapped to O*NET tasks and SOC occupation codes.

Combined with Gemma's theoretical scoring (S1), this enables the S4 three-signal composite: theoretical ceiling × observed adoption × velocity.

## Source Data

- **Source:** HuggingFace dataset `Anthropic/EconomicIndex`
- **License:** CC-BY (open for commercial use with attribution)
- **Primary release:** `release_2026_03_24/` (latest with Opus 4.5/4.6 data)
- **Fallback release:** `release_2026_01_15/` or `release_2025_03_27/`

### Key Files

| File | Description |
|------|-------------|
| `task_pct_v2.csv` | Task-level AI usage percentages by O*NET task ID |
| `automation_vs_augmentation_by_task.csv` | Automation vs augmentation breakdown per task |
| `onet_task_statements.csv` | O*NET task IDs mapped to task descriptions |
| `SOC_Structure.csv` | SOC hierarchy (major groups, detailed codes) |
| `onet_task_mappings.csv` | O*NET task → SOC occupation mapping |

### Data Flow

```
onet_task_mappings.csv (task → SOC)
  + task_pct_v2.csv (task → usage %)
  + automation_vs_augmentation_by_task.csv (task → automation/augmentation split)
  ↓
Aggregate to SOC-level:
  - observed_exposure_pct = weighted avg of task usage % by task prevalence
  - automation_pct = weighted avg of automation % by task usage
  ↓
Join to our SOC codes via consumable.occupation_profiles
```

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

Where `task_weight` could be:
- Equal weight (1.0 per task) — simple
- O*NET task importance scores — if available in source
- Task frequency in Claude conversations — implicit in task_pct

### Expected Output

~800 SOC codes with:
- `observed_exposure_pct` (0-100): % of occupation tasks being performed with AI
- `automation_pct` (0-100): % of AI usage that is automation (vs augmentation)
- `task_count`: number of O*NET tasks mapped

---

## Success Criteria

- [ ] HuggingFace dataset cloned to `data/raw/anthropic_economic_index/`
- [ ] Raw data lands in Iceberg table `raw.anthropic_economic_index`
- [ ] Silver base table `base.anthropic_observed_exposure` with SOC-level aggregation
- [ ] Gold update: `consumable.ai_exposure` gains `observed_exposure_pct`, `automation_pct` columns
- [ ] SOC join coverage ≥ 80% against `consumable.occupation_profiles`
- [ ] DQ rules passing at each zone
- [ ] Data provenance: source release version tracked

---

## Zone 0: Data Acquisition

### Clone Script

```bash
cd ~/code/bright/futureproof-data/data/raw
git clone https://huggingface.co/datasets/Anthropic/EconomicIndex anthropic_economic_index
cd anthropic_economic_index
git lfs pull
```

If the latest release (`release_2026_03_24/`) isn't available, fall back to `release_2026_01_15/` or `release_2025_03_27/`.

### Verify Files Exist

```bash
ls data/raw/anthropic_economic_index/release_2026_03_24/
# Expected: task_pct_v2.csv, automation_vs_augmentation_by_task.csv, onet_task_mappings.csv, etc.
```

---

## Zone 1: Bronze (Raw Ingest)

### Iceberg Table: raw.anthropic_economic_index

- **Grain:** One row per O*NET task
- **Dedup grain:** [task_id]
- **Expected rows:** ~3,500 tasks (based on onet_task_mappings.csv)

### Ingestor

- **Class:** `AnthropicEconomicIndexIngestor` (extends `BaseIngestor`)
- **Location:** `src/raw/anthropic_economic_index_ingestor.py`
- **Implementation:**
  1. Read `onet_task_mappings.csv` — columns: `task_id`, `soc_code`, `task_statement`, etc.
  2. Read `task_pct_v2.csv` — columns: `task_id`, `pct` (% of Claude usage)
  3. Read `automation_vs_augmentation_by_task.csv` — columns: `task_id`, `automation_pct`, `augmentation_pct`
  4. Join on `task_id`
  5. Output one row per task with all fields

### Raw Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| task_id | string | yes | O*NET task identifier |
| task_statement | string | yes | Task description text |
| soc_code | string | no | SOC code (may be broad XX-XXX0 or detailed XX-XXXX) |
| soc_title | string | no | Occupation title |
| task_pct | double | yes | % of Claude conversations involving this task (0-100) |
| automation_pct | double | no | % of task usage that is automation (0-100) |
| augmentation_pct | double | no | % of task usage that is augmentation (0-100) |
| source_release | string | yes | "release_2026_03_24" |
| ingested_at | timestamp | yes | |
| load_date | date | yes | |

### DQ Rules (Bronze)

- task_id uniqueness (P0)
- task_pct range: 0 ≤ task_pct ≤ 100 (P0)
- automation_pct + augmentation_pct ≈ 100% where both present (P1, allow 5% tolerance for rounding)
- Row count: 3000-5000 (P0 — based on O*NET task coverage)
- soc_code non-null coverage ≥ 90% (P1)

---

## Zone 2: Silver (Aggregate to SOC Level)

### Iceberg Table: base.anthropic_observed_exposure

- **Grain:** One row per SOC code
- **Dedup grain:** [soc_code]
- **Promote pattern:** `compute_grain_id(row, ['soc_code'], prefix='aoe')`

### Silver Transformations

1. **SOC normalization:** Standardize to XX-XXXX format. Handle broad codes (XX-XXX0) by expanding to detailed codes where possible.

2. **Task aggregation:** For each SOC code:
   ```python
   observed_exposure_pct = sum(task_pct for all tasks mapped to this SOC) 
   # Note: task_pct is already a % of total Claude usage, so sum gives total occupation exposure
   
   # Or if task_pct is per-task within occupation:
   observed_exposure_pct = mean(task_pct for tasks in this SOC)
   ```
   
   **Clarification needed:** Review actual data to determine if `task_pct` is:
   - Global % (sum across all tasks = 100%) → use sum per SOC
   - Per-task % (each task 0-100% independently) → use mean per SOC

3. **Automation ratio:** 
   ```python
   automation_pct = weighted_avg(task.automation_pct, weights=task.task_pct)
   ```

4. **SOC join validation:** Flag `soc_match = true/false` based on join to `base.bls_ooh.soc_code`.

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
| soc_match | boolean | yes | True if soc_code exists in our BLS data |
| source_release | string | yes | |
| promoted_at | timestamp | yes | |

### DQ Rules (Silver)

- soc_code uniqueness (P0)
- observed_exposure_pct range: 0 ≤ x ≤ 100 (P0)
- soc_match = true for ≥ 80% of rows (P0)
- Row count: 700-900 (based on SOC coverage)
- task_count ≥ 1 for all rows (P0)

---

## Zone 3: Gold (Merge into consumable.ai_exposure)

### Updates to consumable.ai_exposure

Add new columns via schema evolution:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| observed_exposure_pct | double | no | From Anthropic (0-100) |
| automation_pct | double | no | From Anthropic (0-100) |
| anthropic_task_count | int | no | Number of O*NET tasks in aggregation |
| anthropic_source_release | string | no | "release_2026_03_24" |

### Gold Transformer Update

Modify `src/gold/ai_exposure_transformer.py`:

```python
def blend_scores(...):
    # Existing: Gemma + Karpathy blending
    # Add: LEFT JOIN base.anthropic_observed_exposure on soc_code
    # Populate new columns where Anthropic data available
```

### DQ Rules (Gold)

- observed_exposure_pct populated for ≥ 70% of rows (P1)
- Where observed_exposure_pct present, automation_pct also present (P1)
- No change to existing stat_res/boss_ai_score derivation (this spec adds data, doesn't modify formulas — that's S4's job)

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `data/raw/anthropic_economic_index/` | Create (clone) | HuggingFace dataset |
| `src/raw/anthropic_economic_index_ingestor.py` | Create | Bronze ingestor |
| `src/silver/anthropic_observed_exposure_transformer.py` | Create | Silver aggregation |
| `src/gold/ai_exposure_transformer.py` | Modify | Add Anthropic columns |
| `governance/dq-rules/raw-anthropic-economic-index.json` | Create | Bronze DQ |
| `governance/dq-rules/silver-anthropic-observed-exposure.json` | Create | Silver DQ |
| `governance/dq-rules/gold-ai-exposure.json` | Modify | Add Anthropic field rules |
| `governance/data-contracts/base-anthropic-observed-exposure.yaml` | Create | Silver contract |
| `governance/data-contracts/consumable-ai-exposure.yaml` | Modify | Add Anthropic fields |

---

## Agent Workflow

```
Read the spec at docs/specs/raw-ingest-anthropic-economic-index.md in its entirety.

Execute the following workflow:

1. DATA ACQUISITION
   - Clone the HuggingFace dataset: git clone https://huggingface.co/datasets/Anthropic/EconomicIndex data/raw/anthropic_economic_index
   - Run git lfs pull to fetch large files
   - Identify the latest release folder with task_pct data
   - If release_2026_03_24 doesn't exist, use release_2026_01_15 or release_2025_03_27

2. EDA
   - Invoke @data-analyst to explore the CSV files
   - Document: column names, row counts, task_pct distribution, SOC coverage
   - Determine aggregation strategy based on actual data structure
   - Update spec with findings in §EDA Results

3. IMPLEMENTATION
   - Build Bronze ingestor
   - Build Silver transformer (SOC aggregation)
   - Modify Gold transformer (add Anthropic columns)
   - Run ruff + mypy + pytest

4. DQ + GOVERNANCE
   - Write DQ rules for Bronze + Silver
   - Update Gold DQ rules
   - Create/update data contracts

5. VERIFICATION
   - Run full pipeline: Bronze → Silver → Gold
   - Verify consumable.ai_exposure has new columns populated
   - Log row counts and coverage stats

6. COMPLETION
   - Update THIS SPEC's Status to COMPLETE
   - Note: S4 three-signal-ai-exposure-composite is now unblocked
```

---

## EDA Results

*To be filled by @data-analyst after cloning dataset*

### File Inventory

| File | Rows | Columns | Notes |
|------|------|---------|-------|

### Column Definitions

*Document actual column names and meanings*

### Aggregation Strategy

*Document final aggregation approach based on data structure*

### SOC Coverage

| Metric | Value |
|--------|-------|
| Unique SOC codes in source | |
| SOC codes matching our pipeline | |
| Coverage % | |

---

## Post-Completion

Once this spec completes:
1. Update S4 spec (`three-signal-ai-exposure-composite.md`) to reference the new `base.anthropic_observed_exposure` table
2. S4 can proceed with three-signal composite formula implementation

---

*— End of Spec —*
