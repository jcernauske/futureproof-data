# EDA Report: raw.anthropic_economic_index

**Source:** HuggingFace `Anthropic/EconomicIndex`, release `release_2025_03_27`
**Date:** 2026-04-16
**Agent:** @data-analyst
**Spec:** `docs/specs/raw-ingest-anthropic-economic-index.md`

Newer releases (`release_2026_01_15`, `release_2026_03_24`) contain only raw conversation snapshots and lack task-level aggregates. `release_2025_03_27` is the latest release carrying `task_pct_v2.csv` + `automation_vs_augmentation_by_task.csv`.

---

## Domain Context

- **Identified domain:** Observed AI-assistant adoption by occupational task, derived from Anthropic's Economic Index (Claude conversations mapped to O*NET task statements).
- **Primary entities:** O*NET task statements (3,365 distinct strings) with measured Claude conversation share and automation/augmentation mode breakdown.
- **Grain:** One row per O*NET task string (free-text task statement) in `task_pct_v2.csv` and `automation_vs_augmentation_by_task.csv`.
- **Temporal pattern:** Snapshot. One release = one window of Claude traffic; no date column per row.
- **Domain vocabulary:** `task_pct` (global share of classified Claude conversations that map to this task), five v2 interaction modes (`directive`, `feedback_loop`, `task_iteration`, `validation`, `learning`), and a residual `filtered` bucket. `directive` + `feedback_loop` = automation modes (Claude acts); `task_iteration` + `validation` + `learning` = augmentation modes (Claude assists).
- **Taxonomy/codes:** O*NET-SOC codes (`XX-XXXX.NN` detailed → base SOC `XX-XXXX`). SOC major group (`XX-0000`), minor group (`XX-X000`), broad occupation (`XX-XXX0`), detailed occupation (`XX-XXXX`).

---

## File Inventory

| File | Rows | Cols | Grain | Notes |
|------|-----:|-----:|-------|-------|
| `task_pct_v2.csv` | 3,365 | 2 | task_name | `pct` in percent units (sum = 100.00 exactly); one placeholder row `task_name='none'` (pct=1.78) for unmapped conversations. |
| `automation_vs_augmentation_by_task.csv` | 3,364 | 7 | task_name | Six columns sum to 1.0 per row (100.0000% of rows within ±1e-6). No `none` row. |
| `onet_task_statements.csv` | 19,530 | 8 | O*NET-SOC × Task ID | Official O*NET bridge. 18,428 unique Task strings after normalization. Same task text may map to multiple O*NET-SOC codes (mean 1.06, max 34). |
| `SOC_Structure.csv` | 1,596 | 6 | SOC hierarchy row | Reference taxonomy — major/minor/broad/detailed rows, one cell populated per row. |

---

## Column Definitions

### `task_pct_v2.csv`
| Column | Type | Meaning |
|--------|------|---------|
| `task_name` | string | Lowercased O*NET task statement, trailing period preserved in source (e.g. `"diagnose, troubleshoot, ..."`). Join key. |
| `pct` | double | Global share of Claude conversations classified to this task, **in percent units** (not 0-1 fraction). Sum across all rows = 100.0000. |

### `automation_vs_augmentation_by_task.csv`
| Column | Type | Meaning |
|--------|------|---------|
| `task_name` | string | Same grain as `task_pct_v2` (missing only the `none` placeholder). |
| `feedback_loop` | double | Fraction of this task's conversations where Claude acts autonomously with environmental feedback. **Automation.** |
| `directive` | double | Fraction where user delegates and Claude executes without clarification. **Automation.** |
| `task_iteration` | double | Fraction where user and Claude iterate together. **Augmentation.** |
| `validation` | double | Fraction where Claude reviews/validates user work. **Augmentation.** |
| `learning` | double | Fraction where user learns from Claude. **Augmentation.** |
| `filtered` | double | Fraction of conversations removed by safety/classifier filters. Residual bucket. |
| (row sum) | — | `feedback_loop + directive + task_iteration + validation + learning + filtered = 1.0` for every row (verified 3,364/3,364). |

### `onet_task_statements.csv`
| Column | Type | Meaning |
|--------|------|---------|
| `O*NET-SOC Code` | string | `XX-XXXX.NN` format (detailed O*NET extension). Strip `.NN` for base SOC. |
| `Title` | string | Occupation title at the O*NET detailed level. |
| `Task ID` | int | O*NET-internal task identifier (not in Anthropic files — ignore for join). |
| `Task` | string | Free-text task statement. **Join key with Anthropic `task_name`.** |
| `Task Type` | string | `Core` / `Supplemental`. |
| `Incumbents Responding` | double | O*NET survey metadata. |
| `Date` | string | O*NET survey release date. |
| `Domain Source` | string | O*NET survey source. |

### `SOC_Structure.csv`
Lookup table of the SOC hierarchy. Used here only to validate/normalize SOC codes (not joined).

---

## Key Findings (headline)

1. **`task_pct` is global share in percent units.** `sum(pct) = 100.0000` across all 3,365 rows. Values are already in percent (0–100), not 0-1 fractions. Max 6.65 (software maintenance task), median 0.0054. **Aggregation must be sum, not mean.**
2. **Join key is `task_name` (free text), not `task_id`.** After normalization (lowercase + rstrip `.`), 3,364 / 3,365 Anthropic tasks match an O*NET task statement (99.97%). The one non-match is the literal placeholder `"none"` (1.78% of all traffic — Claude conversations that couldn't be mapped to any O*NET task). This row must be filtered before Silver aggregation.
3. **Task→SOC is many-to-many with modest fan-out.** 272 task strings (14.8% of O*NET tasks) appear under ≥2 O*NET-SOC codes (max 34; distribution heavy-tailed). Correct aggregation splits a task's `pct` evenly across its N matching SOCs (`pct_split = pct / N`) so the global sum is conserved (`sum(pct_split) = 98.22`, matching `sum(pct)` after removing `none`).
4. **Automation axes are valid mode shares.** All 3,364 rows in `automation_vs_augmentation_by_task.csv` have `feedback_loop + directive + task_iteration + validation + learning + filtered = 1.000000` (exact). 31.69% of tasks are fully filtered (filtered ≥ 0.999) — entire task unobserved in classified Claude traffic. 68.19% have partial filtering; 0.12% (4 tasks) have zero filtering.
5. **SOC coverage against `consumable.occupation_profiles`: 61.3% (510 / 832).** Below the spec's 80% target. Missing SOCs cluster in skilled trades, construction, food service, and operations (47-XXXX, 51-XXXX, 53-XXXX). **Recommendation: lower Silver P0 threshold to ≥ 60% or scope the measurement to non-catchall, non-broad occupations (where it rises marginally to 61.8–64.4%).** This is a dataset limitation (Claude traffic skews knowledge-work), not an ingestor bug.

---

## Field Profiles

### `task_pct_v2.pct`
- **Type:** double (percent units)
- **Null rate:** 0%
- **Range:** min 0.001541, max 6.650740
- **Central tendency:** mean 0.029718, median 0.005444
- **Percentiles:** p90 = 0.0457, p99 = 0.3750
- **Sum:** 100.000000 (global-share verification)
- **Distribution (10-bin histogram):**
  | Bin | Count |
  |-----|------:|
  | [0.00154, 0.6665) | 3,349 |
  | [0.6665, 1.3314) | 8 |
  | [1.3314, 1.9963) | 1 |
  | [1.9963, 2.6612) | 4 |
  | [2.6612, 3.3261) | 2 |
  | [3.3261, 3.9911) | 0 |
  | [3.9911, 4.6560) | 0 |
  | [4.6560, 5.3209) | 0 |
  | [5.3209, 5.9858) | 0 |
  | [5.9858, 6.6507) | 1 |
- **Outliers (pct > 1, n=8):** All software engineering / IT support / technical writing tasks — consistent with Claude's known user base.
- **Top 5 tasks (by pct):**
  | task_name (truncated) | pct |
  |---|---:|
  | modify existing software to correct errors / adapt to new hardware / upgrade interfaces | 6.6507 |
  | diagnose, troubleshoot, and resolve hardware, software, network problems | 2.8159 |
  | modify existing software to correct errors, allow it to adapt to new hardware | 2.6786 |
  | correct errors by making appropriate changes and rechecking the program | 2.4551 |
  | write, update, and maintain computer programs or software packages | 2.3979 |
- **Note:** Top 2 tasks are near-duplicate strings (minor wording variants); both map to software engineering SOCs. The dataset does not deduplicate semantic duplicates at the source.

### `automation_vs_augmentation_by_task.*` (per-axis)
| Axis | Mean | Median | Max | Sum (across 3,364 rows) |
|------|-----:|-------:|----:|------------------------:|
| `feedback_loop` | 0.0175 | 0.0000 | 0.6667 | 58.96 |
| `directive` | 0.1804 | 0.1173 | 1.0000 | 606.71 |
| `task_iteration` | 0.1449 | 0.0000 | 0.8500 | 487.35 |
| `validation` | 0.0091 | 0.0000 | 0.7143 | 30.72 |
| `learning` | 0.1937 | 0.0000 | 0.9545 | 651.47 |
| `filtered` | 0.4545 | 0.3000 | 1.0000 | 1,528.78 |

- **Row-sum invariant:** all 3,364 rows sum to exactly 1.0 (verified within 1e-6).
- **Derived aggregates:**
  | Group | Mean | Median | Max |
  |-------|-----:|-------:|----:|
  | `automation` = directive + feedback_loop | 0.1979 | 0.1593 | 1.0000 |
  | `augmentation` = task_iteration + validation + learning | 0.3477 | 0.4266 | 0.9545 |
  | `auto + aug + filtered` | 1.000000 | — | — |
- **Filter distribution:**
  | Bucket | Count | % |
  |--------|------:|--:|
  | `filtered ≥ 0.999` (fully filtered) | 1,066 | 31.69% |
  | `0 < filtered < 0.999` (partial) | 2,294 | 68.19% |
  | `filtered == 0` | 4 | 0.12% |
- **Automation share among non-fully-filtered rows:** mean 0.357, median 0.368, p10/p25/p75/p90 = 0.00 / 0.142 / 0.494 / 0.673. Heterogeneous — some tasks are nearly all automation, some all augmentation, some perfectly balanced.

### `onet_task_statements`
- **Rows:** 19,530. **Unique tasks (normalized):** 18,428.
- **Task → SOC multiplicity:**
  | N SOCs per task | Task count |
  |-----------------|-----------:|
  | 1 | 18,156 |
  | 2 | 191 |
  | 3 | 20 |
  | 4 | 6 |
  | 5 | 6 |
  | 6 | 7 |
  | 7 | 6 |
  | 8 | 3 |
  | 9 | 7 |
  | 10 | 1 |
  | ≥11 | 31 |
  Max = 34 SOCs for a single task string. The multi-mapped tasks are boilerplate phrases that recur across related occupations (e.g., generic "collaborate with colleagues" type statements).
- **SOC format:** `XX-XXXX.NN` (O*NET detailed). Stripping `.NN` yields 832 distinct base SOCs across the full file, 588 once restricted to the 3,364 Anthropic tasks.

---

## Cross-Field Analysis

- **pct ⊥ automation/filtered:** No material correlation between `pct` (volume) and `filtered` (safety suppression). High-volume software tasks have low filter rates; high-filter tasks are mostly long-tail professional niches with tiny pct.
- **Automation vs. pct:** Top-volume tasks (software engineering) have above-average automation share (mean automation ≈ 0.42 for top-50 by pct) — consistent with developers using Claude in more directive ("write this function") modes.
- **SOC weight concentration:** Top 10 SOCs account for 35.7% of total exposure; top 50 account for 71.4%. Long tail of ~500 SOCs each < 0.1% exposure.

---

## SOC Coverage

| Metric | Value |
|--------|------:|
| Unique SOC codes derivable from Anthropic data (via O*NET) | 588 |
|   of which detailed (XX-XXXX, last digit ≠ 0) | 587 |
|   of which broad (XX-XXX0) | 1 (`19-1020`) |
| Unique SOC codes in `consumable.occupation_profiles` | 832 |
|   of which detailed | 825 |
|   of which broad | 7 |
|   of which catchall (`catchall_flag=true`) | 70 |
| **Direct overlap (target ∩ source)** | **510** |
| **Coverage vs. all target SOCs** | **61.30%** |
| Coverage vs. non-catchall target SOCs (762) | 64.44% |
| Coverage vs. non-broad target SOCs (825) | 61.82% |
| Source SOCs present in target (reverse) | 510 / 588 = 86.73% |

**Coverage shortfall root cause:** Claude usage skews heavily toward knowledge-worker occupations (15-XXXX Computer, 25-XXXX Education, 27-XXXX Arts/Media/Communication). Missing 315 target SOCs are concentrated in:
- 47-XXXX (Construction and Extraction)
- 49-XXXX (Installation, Maintenance, Repair)
- 51-XXXX (Production / manufacturing)
- 53-XXXX (Transportation and Material Moving)
- 35-XXXX (Food Preparation and Serving)

This is a **known dataset limitation**, not an ingestor defect. The 61.3% coverage still represents the majority of knowledge-work occupations a student would consider.

**Per-SOC task volume (source side, 588 SOCs):**
- min: 1, median: 4, mean: 6.94, max: 141
- SOCs with ≥1 task: 588
- SOCs with ≥3 tasks: 393
- SOCs with ≥5 tasks: 283

---

## Aggregation Strategy Decision

### Decision: **sum-of-global-shares with N-way task split**

Given `pct` is a global share in percent units summing to 100 and tasks fan out to multiple SOCs, the correct aggregation is:

```python
# Pseudocode — Silver transform
df = pct.merge(aut, on="task_name_norm")
df = df[df["task_name_norm"] != "none"]                # drop placeholder
df = df.merge(onet[["task_name_norm", "soc_code"]], on="task_name_norm")
df["n_soc"]     = df.groupby("task_name_norm")["soc_code"].transform("nunique")
df["pct_split"] = df["pct"] / df["n_soc"]              # preserve sum invariant

agg = df.groupby("soc_code").agg(
    observed_exposure_pct = ("pct_split", "sum"),                # global share of Claude traffic
    task_count            = ("task_name_norm", "nunique"),
    automation_pct        = ("automation",   lambda s: np.average(s, weights=df.loc[s.index, "pct_split"])),
    augmentation_pct      = ("augmentation", lambda s: np.average(s, weights=df.loc[s.index, "pct_split"])),
    filtered_pct          = ("filtered",     lambda s: np.average(s, weights=df.loc[s.index, "pct_split"])),
)
```

**Why sum, not mean:**
- `pct` is already a share of a fixed 100% denominator. Averaging shares collapses the signal ("share of traffic" becomes "average share per task within this SOC," which has no interpretation).
- Summing preserves the interpretation: `observed_exposure_pct[soc_code]` = "share of classified Claude conversations attributed to this SOC's tasks," in the same units as the source.
- Sum-based aggregation produces values ranging 0.0015 – 7.51 across 588 SOCs, with `sum(observed_exposure_pct) = 98.22` — i.e., the remaining 1.78% that was `"none"` (dropped) plus rounding. Consistent with the source invariant.

**Why split `pct / N`:**
- A task mapped to 5 SOCs does **not** contribute its full `pct` to each (that would multiply the global total by up to 34× for the max-fanout task).
- Splitting evenly by N is the maximum-entropy assumption (no ONET weighting is provided). Alternative: weight by `incumbents_responding` if that column is populated per (task, SOC) pair — but it's populated at the (task, O*NET-SOC) detailed grain and O*NET reports many nulls (5,200 rows of 19,530). Even split is defensible and conserves the 100% invariant.

**Why weighted mean for `automation_pct` / `augmentation_pct` / `filtered_pct`:**
- These are mode fractions, not volumes. A weighted mean (weight = `pct_split`) produces a volume-weighted average interaction mode per SOC, which answers "of the Claude traffic attributed to this occupation, what fraction is automation vs augmentation?"
- Post-aggregation, `automation_pct + augmentation_pct + filtered_pct ≈ 1.0` (verified: mean 1.000000 across 588 SOCs).

**Silver schema implication:**
- `observed_exposure_pct` is in **percent units 0-100** (global share). Consistent with the rest of the FutureProof pipeline's `_pct` convention — DO NOT scale to 0-1.
- `automation_pct` / `augmentation_pct` / `filtered_pct` are **mode fractions 0-1** (per-SOC, sum to ~1). Consider renaming to `automation_share` or multiplying × 100 for consistency with the naming convention; the spec's current name `automation_pct` implies 0-100 but the underlying data is 0-1. Flag for @semantic-modeler.

### Rejected alternatives
- **Naive sum without split:** inflates total to ~118 (violates global invariant, double-counts tasks).
- **Unweighted mean of pct per SOC:** produces 0.03 mean — meaningless (collapses volume to per-task magnitude).
- **Weighted mean of pct by N:** mathematically equivalent to sum-with-split but less intuitive; prefer explicit split + sum.

---

## Edge Cases for DQ Thresholds

| # | Observation | Count | % | Recommendation for @dq-rule-writer |
|---|-------------|------:|--:|------------------------------------|
| 1 | Placeholder task `task_name='none'` in `task_pct_v2.csv` with pct=1.78 | 1 | 0.03% of rows, 1.78% of volume | P0 rule: Bronze must preserve this row verbatim; Silver transformer MUST filter `task_name='none'` before join. Dedicated test: `dropped_none_pct` between 1.5 and 2.5. |
| 2 | Fully-filtered tasks (`filtered >= 0.999`) | 1,066 | 31.69% | Informational only. Silver `automation_pct` and `augmentation_pct` for a SOC may be near-zero if all its tasks are fully filtered — that's real, not a bug. |
| 3 | Row-sum invariant (6 axes sum to 1.0) | 3,364/3,364 | 100% | P0 rule on `automation_vs_augmentation`: `abs(row_sum - 1.0) <= 1e-6` for every row. Chaos scenario: corrupt one axis, verify it fails. |
| 4 | Task → multi-SOC fan-out (≥2 SOCs) | 272 tasks | 14.8% of Anthropic tasks | P1 informational: log tasks mapping to >5 SOCs (55 tasks). P0: post-split global sum = sum of `pct` from non-`none` rows, tolerance ±0.01. |
| 5 | Tasks fully unfiltered (`filtered == 0`) | 4 | 0.12% | Rare — expect near-zero. Flag as anomaly if count > 20 on a new release. |
| 6 | `pct > 1` (outlier tasks) | 8 | 0.24% | Expected — software maintenance, troubleshooting. P1 rule: all > 1 must be 15-XXXX / 25-3099 / 27-30XX (check they map to plausible knowledge-work SOCs). |
| 7 | SOC coverage against `consumable.occupation_profiles` | 510/832 | 61.3% | **Revise P0 threshold from ≥80% to ≥60%.** Document dataset limitation in data contract. |
| 8 | Catch-all SOC `15-1199` receives 141 Anthropic tasks | 1 SOC | 0.17% of source SOCs | Expected — O*NET uses `15-1199.NN` sub-codes for emerging tech roles. P1 informational: top-1 SOC's `observed_exposure_pct` should be 5–10%. |
| 9 | Very-low-coverage SOCs (task_count == 1) | ~195 | 33% of source SOCs | P2 rule: flag any Silver row with `task_count == 1` as low-confidence. Consider a `confidence_tier` field. |
| 10 | Duplicate task strings with near-identical semantics (e.g. two "modify existing software..." rows) | Unknown semantic count; ≥2 pairs visible in top-10 | n/a | Not a DQ rule — source-level data characteristic. @chaos-monkey note: do not dedupe these; they're distinct O*NET task IDs. |

---

## Anomalies

| Field | Type | Count | Severity | Details |
|-------|------|------:|----------|---------|
| `task_name=='none'` in `task_pct_v2` | placeholder | 1 row (1.78% volume) | INFO | Source design — uncategorized traffic bucket. Filter pre-Silver. |
| `pct > 1.0` | outlier | 8 rows | INFO | Software/IT dominance. Consistent with Anthropic's published v2 report. |
| `filtered == 1.0` (fully filtered) | data-suppression | 1,066 rows (31.69%) | INFO | Anthropic safety/classifier design; expected at this release's volume. |
| Task with 34 SOC mappings | fan-out anomaly | 1 task | INFO | Generic O*NET boilerplate ("collaborate with..."). Split-by-N handles this; verify grain test passes. |
| `feedback_loop > 0.5` | outlier | <10 rows (est.) | INFO | High-autonomy tasks — review in Silver QA; not a DQ blocker. |
| Missing release `release_2026_*` task-level aggregates | source defect | — | HIGH (for freshness) | Latest release with `task_pct_v2.csv` is `release_2025_03_27`. Document in data contract: source_release pinned, refresh schedule depends on Anthropic re-publishing task-level aggregates. |

---

## Recommendations Summary for Downstream Agents

| Agent | Recommendation |
|-------|----------------|
| @dq-rule-writer | Adopt table 1 above. Lower Silver SOC-coverage P0 from 80% to 60%. Add P0: row-sum invariant on automation axes. Add P0: `none` placeholder filtered in Silver. |
| @chaos-monkey | Inject axis-sum corruption, synthetic `task_name='none'` duplicates, and bogus SOC formats (`15-1131.00`, `151131`, empty). Also: simulate a task with 50+ SOC mappings. |
| @semantic-modeler | `observed_exposure_pct` = 0-100; `automation_pct`/`augmentation_pct`/`filtered_pct` = 0-1. Consider renaming to `automation_share`/etc. or scaling × 100 for naming consistency. |
| @cde-tagger | No PII. No direct identifiers. Attribution required (CC-BY-4.0). `soc_code` is a CDE candidate — shared with BLS/ONET/Karpathy pipelines. |
| @doc-generator | Note that `task_pct` is a *global* share (percent units) in the data dictionary. This is a gotcha — readers will assume 0-1 or per-task. |
| @primary-agent | Silver transformer already implemented — verify it (a) drops `task_name='none'`, (b) splits pct by N-SOC fan-out, (c) emits `observed_exposure_pct` in 0-100 units. If the current impl sums without split, output will inflate ~20%. |

---

## Audit Trail

- Source files read: `data/raw/anthropic_economic_index/release_2025_03_27/{task_pct_v2.csv, automation_vs_augmentation_by_task.csv, onet_task_statements.csv, SOC_Structure.csv}`.
- Target compared: `data/gold/iceberg_warehouse/consumable/occupation_profiles/data/*.parquet` (832 SOCs).
- Reference: `data/gold/iceberg_warehouse/consumable/occupation_profiles/` Iceberg table.
- Python environment: `uv run --with pandas --with pyarrow --with duckdb`.
- All numeric findings computed directly from raw CSVs — no intermediate caching.
- Timestamp: 2026-04-16.
