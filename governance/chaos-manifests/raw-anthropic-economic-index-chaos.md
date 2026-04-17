# Chaos Manifest — raw-ingest-anthropic-economic-index

**Spec:** `docs/specs/raw-ingest-anthropic-economic-index.md`
**Tables under test:**
- `raw.anthropic_economic_index` (Bronze)
- `base.anthropic_observed_exposure` (Silver)
- `consumable.ai_exposure` (Gold — S3 additive columns)

**Runner:** `governance/chaos-manifests/anthropic_economic_index_chaos_runner.py`
**JSON manifest:** `governance/chaos-manifests/raw-ingest-anthropic-economic-index-manifest.json`
**Status:** HARDENED — 2026-04-17
**Initial run:** 2026-04-16 (5 cycles, 1 persistent P1 gap)
**Re-run after primary-agent fix:** 2026-04-17 (2 cycles, 16/16 PASS both)

**Information barrier:** Runner written WITHOUT reading DQ rule JSON files. Scenarios derived from the spec's chaos manifest, the ingestor/transformer source, and the EDA report only. Related-DQ-rule labels are educated guesses from spec §"Bronze/Silver DQ Rules" tables plus the new `RAW-AEI-019` rule id the primary agent mentioned in the fix handoff — not verified against the rule files.

---

## Approach

Sixteen scenarios were injected across three failure surfaces:

1. **Source acquisition** (S1, S2, S8) — network loss, LFS stubs, release fallback.
2. **Source-file corruption** (S3, S4, S5, S6, S7, S9, S10, S11, S13, S15) — column drift, missing columns, malformed SOC codes, empty files, duplicate tasks, extra columns, fully-filtered tasks, synthetic fan-out stress, unicode, normalized-key collisions.
3. **Numeric / invariant** (S12, S14) + pipeline plumbing (S16) — negative/NaN pct, out-of-range pct, and empty-Bronze Silver.

Every scenario builds a fresh temp fixtures directory from the real `release_2025_03_27` CSVs, mutates the copy, then runs the ingestor (`fetch` → `flatten`) and in some cases the Silver transformer (`transform_rows`) against it. Verdicts compare the actual output to the behavior the spec and post-fix ingestor promise.

The scenarios are **deterministic** — the same mutations apply each cycle. Running two cycles confirms stability (no flaky tests) rather than randomized stress, which is appropriate because the injected faults are structural, not statistical.

---

## What Changed Between Runs

After the initial run (2026-04-16) reported a P1 gap on `S5` (SOC format), the primary agent landed:

1. **`src/raw/anthropic_economic_index_ingestor.py` — `_normalize_onet_soc`**: now validates against `^\d{2}-\d{4}$` after the overlay-suffix strip. Unambiguous dash-less 6-digit SOCs are recovered (`"151252"` → `"15-1252"`). Every other malformed shape (5-digit, 7-digit, dotted, letters, embedded whitespace, placeholders) returns `None` and the bridge row is dropped. Tasks whose ALL bridge SOCs are malformed are dropped entirely (to preserve the NULL-SOC-singleton invariant that `task_name='none'` is the only legitimate null-SOC row).
2. **`fetch()` fast-fail header check**: calls `_validate_csv_headers()` against each of the three source CSVs at the ingestion-start boundary. A source file missing any required column now raises `ValueError` with an explicit diff of required-vs-found columns instead of silently emitting `None`-filled rows.
3. **New DQ rule `RAW-AEI-019` (P0)** enforces `soc_code REGEXP '^[0-9]{2}-[0-9]{4}$' OR soc_code IS NULL`.

The runner was updated for scenarios S3, S4, and S5 to assert the new expected behaviors (fast-fail on header drift; canonical-or-null SOC shape). Scenarios S1, S2, S6–S16 (except those just listed) were unchanged.

---

## Scenario Results (post-fix, both cycles identical)

| # | Scenario | Verdict | Evidence | Related DQ Rule |
|---|----------|---------|----------|-----------------|
| S1 | Network failure, no cache | PASS | `FileNotFoundError` raised with clone+lfs instructions | N/A — pre-DQ guard |
| S2 | git-lfs pointer stubs | PASS | Ingestor parses stubs, emits 0 rows; row-count DQ would fail | `raw.row_count_in_range` |
| S3 | Malformed headers (`pct` → `Percentage`) | **PASS** (was PARTIAL) | `ValueError: CSV task_pct_v2.csv is missing required columns: ['pct']. Found columns: ['Percentage', 'task_name'].` — fast-fails at `fetch()` before any Bronze row is written. | Ingestor fast-fail guard + `raw.task_pct_global_sum` |
| S4 | Missing required column (`task_name`) | PASS | `ValueError: CSV task_pct_v2.csv is missing required columns: ['task_name']. Found columns: ['pct'].` — fast-fails at `fetch()`. | Ingestor fast-fail guard + `raw.row_count_in_range` |
| S5 | SOC code format variations | **PASS** (was FAIL) | All 4082 emitted rows have soc_code matching `^\d{2}-\d{4}$` or NULL. `"151252"` recovered to `"15-1252"` (unambiguous 6-digit). `"11-1011.99"` overlay normalized to `"11-1011"`. Every other variant (`"15.1252"`, `"15-12520"`, `"XX-XXXX"`, `""`, `"NULL"`) rejected cleanly. | `RAW-AEI-019` (P0) + `silver.soc_code_format` |
| S6 | Empty `task_pct_v2.csv` | PASS | 0 Bronze rows | `raw.row_count_in_range` |
| S7 | Duplicate source rows | PASS | 4082 rows, 0 duplicate (task_id, soc_code) grains (seen_grain dedup works) | `raw.composite_uniqueness` |
| S8 | Release folder missing → fallback | PASS | `source_method == "local_cache"`; 4082 rows emitted from cache | N/A — acquisition resilience |
| S9 | Extra unexpected columns | PASS | 4082 rows emitted; ignored `debug_score` column (header check uses superset, not equality) | N/A — schema robustness |
| S10 | Fully-filtered task (filtered=1.0) | PASS | 38 Bronze rows have `automation_pct=None` AND `augmentation_pct=None` | `raw.automation_augmentation_sum` (nulls tolerated) |
| S11 | Stress fan-out to 50 SOCs | PASS | 50 rows, each `task_pct = 0.1 = 5.0/50`, all SOCs distinct, split math correct | `raw.composite_uniqueness` + `raw.task_pct_global_sum` |
| S12 | Negative / NaN / garbage `pct` | PASS | 38 negatives + 10 NaN pass through (as raw values); 3 garbage strings → null. SUM drifts by 7.91 → DQ catches. | `raw.task_pct_range` + `raw.task_pct_global_sum` |
| S13 | Unicode / smart quotes in task_name | PASS | No crash; 4082 rows; 3 additional NULL-SOC rows (smart-quoted names don't match O*NET plain-ASCII names) | Implicit — SOC-join coverage drifts |
| S14 | Very large single pct (500.0) | PASS | Bronze SUM(task_pct) = 600.00 (invariant DQ fails as expected); Silver **clamps** `observed_exposure_pct` to 100.00 via `_aggregate_observed_exposure`. | `raw.task_pct_range` + `silver.observed_exposure_pct_range` |
| S15 | Normalized task_name collision | PASS | Composite grain unique (4048 rows); both `'foo.'` and `'FOO'` emit rows independently via distinct task_ids | `raw.composite_uniqueness` |
| S16 | Silver with empty Bronze | PASS | `transform_rows([], [])` returns `[]` — no crash | `silver.row_count_in_range` |

**Totals (both cycles):** 16 PASS / 0 PARTIAL / 0 FAIL / 0 ERROR.

---

## Gap Closure Summary

### Gap 1 — P1: `_normalize_onet_soc` accepted no-dash codes → **CLOSED**

Previously `"151252"` leaked through `_normalize_onet_soc` unchecked and landed in Bronze with a malformed (dash-less) shape. The primary agent's fix now validates against `^\d{2}-\d{4}$` after overlay-strip. Two outcomes are legal:

1. Canonical form (`XX-XXXX`) — kept as-is.
2. Unambiguous dash-less 6-digit (`XXXXXX`) — recovered to `XX-XXXX`. This is the only non-canonical shape accepted, because 5-digit and 7-digit strings are ambiguous about where the dash should go.

Everything else returns `None`. When `None` is returned for a task-statement row, the caller drops the (task, SOC) mapping. If ALL of a task's SOC mappings are malformed, `flatten` drops the task entirely — preserving the RAW-AEI-017 invariant that `task_name='none'` is the only legitimate null-SOC Bronze row.

**Evidence:** S5 cycles both runs — 4082 rows emitted, zero malformed SOCs, `"151252"` and `"11-1011.99"` visible as normalized-in-place.

**DQ coverage:** `RAW-AEI-019` (P0) now enforces `soc_code REGEXP '^[0-9]{2}-[0-9]{4}$' OR soc_code IS NULL`.

### Gap 2 — P2: Ingestor silent on missing/renamed required columns → **CLOSED**

Previously `csv.DictReader` accepted any header and `row.get("pct")` returned `None` for the missing key, producing 4082 silent-null Bronze rows. The primary agent added `_validate_csv_headers(path, required)` invoked at the top of `fetch()` for all three source CSVs. A column rename now raises a `ValueError` with an explicit missing-vs-found diff before any row is read.

**Evidence:**
- S3 run output (both cycles): `ValueError: CSV task_pct_v2.csv is missing required columns: ['pct']. Found columns: ['Percentage', 'task_name']. This indicates source schema drift — inspect the file and update the ingestor if the source format has changed.`
- S4 (`task_name` deleted): same fast-fail path, names `['task_name']` as missing.

### Gap 3 — P2: Silver clamp silently masks invariant violations → **UNCHANGED (advisory)**

Not in the primary agent's fix scope for this re-run. Silver's `_aggregate_observed_exposure` still clamps to `[0, 100]` and still masks upstream violations at the Silver layer. This was and remains advisory — Bronze's `raw.task_pct_range` and `raw.task_pct_global_sum` rules continue to provide the signal, and S14 confirms the Bronze-side DQ rules catch a 500.0 injection even though Silver clamps to 100.00. Recommend a follow-up spec for a `saturation_flag` Silver column or clamp-counter metric if downstream observability is desired. Not blocking.

---

## Cycles and Certification

| Cycle | Pass | Fail | Partial | Error |
|-------|-----:|-----:|--------:|------:|
| 1 | 16 | 0 | 0 | 0 |
| 2 | 16 | 0 | 0 | 0 |

- **Cycles completed:** 2/2
- **Consecutive clean cycles:** 2
- **HARDENED verdict:** **YES.**

The two P1/P2 gaps identified in the initial 2026-04-16 run (SOC format, missing-column fast-fail) are closed by the primary agent's patches and verified by S3, S4, and S5 in both cycles. Gap 3 remains advisory (clamp observability) and is not a certification blocker.

---

## Historical Record — 2026-04-16 Initial Run

Preserved for audit trail.

| Cycle | Pass | Fail | Partial | Error |
|-------|-----:|-----:|--------:|------:|
| 1 | 15 | 1 | 0 | 0 |
| 2 | 15 | 1 | 0 | 0 |
| 3 | 15 | 1 | 0 | 0 |
| 4 | 15 | 1 | 0 | 0 |
| 5 | 15 | 1 | 0 | 0 |

- **Initial verdict:** NO — conditional on Gap 1 fix.
- The single deterministic S5 failure persisted across all five cycles.
- Gaps 1 and 2 handed off to `@primary-agent` and `@dq-rule-writer`.
- Re-run after patches landed produced the HARDENED result recorded above.

---

## What This Run Did NOT Cover

Unchanged from the initial run's follow-up list:

- **Parquet-level DQ-runner integration** — this runner tests ingestor code paths, not the full shadow-table + `dq_runner.run_rules(shadow=True)` integration that peer chaos runners use (e.g. `karpathy_ai_exposure_chaos_runner.py`). A peer agent with access to `governance/dq-rules/` should run that pass.
- **Gold-zone A/B regression** — `consumable.ai_exposure`'s four S3-additive columns were NOT stress-tested here (the LEFT JOIN is simple and the source of truth is covered at Bronze/Silver).
- **Multi-release drift** — this run uses only `release_2025_03_27`. When newer releases gain `task_pct_v2.csv`, a release-forward diff test should be added.
- **Randomized row-level mutation** — this run is deterministic-scenario only. A second pass with randomized injection rates (5–10%) akin to peer `karpathy_ai_exposure_chaos_runner.py` would stress volume/coverage rules.

---

## Re-run Command

```bash
uv run python governance/chaos-manifests/anthropic_economic_index_chaos_runner.py
```
