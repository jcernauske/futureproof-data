# Entity Resolution Review: raw-anthropic-economic-index

**Spec:** `docs/specs/raw-ingest-anthropic-economic-index.md`
**Release reviewed:** `release_2025_03_27`
**Date:** 2026-04-16
**Agent:** @entity-resolver
**Verdict:** **TRIVIAL (with 3 documented advisories)** — the task↔SOC join is a well-understood text crosswalk against an authoritative O*NET bridge. No canonical entity registry is warranted for this spec. Recommend two defensive hardenings be logged for a future chaos-monkey cycle; none are blockers.

---

## 1. Entities Involved

| Entity | Source file | Identifier | Notes |
|--------|-------------|-----------|-------|
| O*NET Task (by text) | `onet_task_statements.csv` | `Task` (free-text statement), with official `Task ID` int as secondary | 19,530 rows, 18,428 distinct normalized strings |
| O*NET Task (by text) | `task_pct_v2.csv` | `task_name` (free-text) | 3,365 rows; NO `Task ID` column — text is the ONLY join key |
| O*NET Task (by text) | `automation_vs_augmentation_by_task.csv` | `task_name` (free-text) | 3,364 rows (no "none" placeholder) |
| SOC Occupation | `onet_task_statements.csv` | `O*NET-SOC Code` (`XX-XXXX.NN`) | Strip `.NN` overlay → base SOC `XX-XXXX` |
| SOC Occupation | `consumable.occupation_profiles` (target) | `soc_code` (`XX-XXXX`) | 832 SOCs |

**Critical fact:** Anthropic's `task_pct_v2.csv` identifies tasks **only by the task statement text**. There is no `task_id` column in the source; the O*NET bridge (`onet_task_statements.csv`) is the only way to recover a SOC and a task_id. Text is the resolution anchor.

---

## 2. Task Text Normalization — Robustness Assessment

### Current normalizer
```python
s = str(value).strip().lower()
s = " ".join(s.split())     # collapse interior whitespace
if s.endswith("."): s = s[:-1]
```

### Empirical check against the actual source (all three files, full release)

| Property | Finding |
|----------|---------|
| Non-ASCII characters in `task_pct_v2.task_name` | **0 / 3,365 rows** |
| Non-ASCII characters in `onet_task_statements.Task` | **0 / 19,530 rows** |
| Smart quotes (`'‘'`, `'’'`, `'"'`, `'"'`, `'–'`, `'—'`) | **0 rows in either file** |
| `task_pct_v2` case convention | All rows lowercase |
| `onet_task_statements` case convention | All 19,530 rows uppercase-first |
| `onet_task_statements` trailing-period convention | 100% (19,530/19,530) end with exactly one `.` |
| `task_pct_v2` trailing-period convention | Mixed — some rows have trailing `.`, some do not |
| `task_pct_v2` normalization collisions (distinct `task_name` → same norm key) | **0 collisions** |

**Verdict:** the current `lowercase + whitespace-collapse + rstrip("\\.")` recipe is **sufficient for this release** — it resolves 3,364 / 3,365 (99.97%) of tasks. The one non-match is the `task_name='none'` placeholder by design (not a normalization miss).

### Residual risks (future releases)

1. **Unicode drift risk.** If Anthropic re-runs the pipeline and sources start including Unicode apostrophes (`'`) instead of ASCII (`'`), or em-dashes instead of hyphens, the current normalizer would silently drop matches. The O*NET bridge is strictly ASCII, so Anthropic text drifting off-ASCII would cause the join to regress.
   - **Recommendation:** Add a future hardening — unicode-normalize `NFKC` then ASCII-fold smart quotes (`'’' → "'"`, `'—' → "-"`) before the case/whitespace pass. **Not required today** (0/3,365 affected).
2. **Multi-period tails risk.** If a task text ever ends `..` (sentence fragment with abbreviation) the current `rstrip("\\.")` only strips one. Current source has 0/19,530 such rows — **not required today**.
3. **Punctuation variance risk.** The source uses both straight comma-wrap and unquoted statements. CSV parsing handles this; normalizer is agnostic. **No concern.**

---

## 3. task_id Collision Analysis

### Reviewer claim in request: "1 collision: `task_name='none'` placeholder"
Accurate — the ingestor synthesizes `task_id = task_name_key` when a task has no O*NET match. For the `none` placeholder this produces `task_id="none"`, `soc_code=NULL`. The O*NET canonical task_id namespace is integer-valued (sampled: `8823`, `8831`, `3245`, etc.); zero O*NET task IDs equal the literal string `"none"` (verified — 0/19,530). **No real collision possible.**

### Additional finding not in EDA: 7 `(text_key, SOC)` pairs with multiple O*NET task_ids

Same normalized task text appears twice within the same SOC in O*NET with **different `Task ID` values**. Examples:

| SOC | task_ids that collapse to one text-key | Sample text (truncated) |
|-----|-----------------------------------------|-------------------------|
| `15-1199` | `{18118, 16086}` | "read current literature, talk with colleagues…" |
| `17-3029` | `{19708, 19718, 19730}` | "conduct statistical studies…" |
| `17-3029` | `{18210, 16675}` | "create computer applications for manufacturing…" |
| `29-1069` | `{17242, 17146}` | "prepare comprehensive interpretive reports…" |
| `29-1125` | `{19168, 19142}` | "communicate client assessment findings…" |
| `27-3091` | `{…, …}` | — |
| `…`       | `{…, …}` | — |

The ingestor's `seen_pairs` dedupe on `(text_key, soc_code)` retains the **first** task_id it sees and drops the rest. Bronze grain `[task_id, soc_code]` stays unique, but the specific `task_id` emitted is **dependent on O*NET file row order** (non-deterministic on re-publish). Zero impact on downstream Silver aggregation (Silver keys on SOC, not task_id) and zero impact on DQ row-count (the 4,082-row count was computed with this same dedupe logic).

**Advisory (informational, not a blocker):** If lineage ever needs to re-trace a Bronze `task_id` back to O*NET, the mapping is not 1:1 for these 7 cases. Document in the data dictionary that `task_id` for multi-mapped texts is "the lexicographically or row-order first Task ID O*NET publishes for this (text, SOC) pair." Do not add a new DQ rule for this — it's a 7-row edge case in a 19,530-row bridge and the Silver layer never sees the task_id.

---

## 4. SOC Code Resolution Assessment

### Current normalizer (`_normalize_onet_soc`)

| Input | Output | Reason |
|-------|--------|--------|
| `""`, `None`, `"nan"`, `"none"`, `"null"` | `None` | Sentinel rejection |
| `"15-1252.00"` | `"15-1252"` | Strip overlay suffix (good) |
| `"15-1252.NN"` | `"15-1252"` | Strip overlay suffix (good) |
| `"15-1252"` | `"15-1252"` | Canonical passthrough |
| `"151252"` | `"15-1252"` | 6-digit dashless recovery (good chaos-monkey fix) |
| `"15125"` / `"1512522"` | `None` | Ambiguous digit count → reject |
| `"15-125"` / `"15-12522"` | `None` | Wrong shape → reject |
| `"ABC-1252"` | `None` | Non-numeric → reject |
| `"15 1252"` | `None` | Whitespace instead of dash → reject |
| `"19-1020"` (broad, ends in `0`) | `"19-1020"` | Accepted as canonical XX-XXXX |

**Verdict:** sound. Every case is unambiguous (or rejected when ambiguous) and the 6-digit dashless recovery specifically addresses a chaos-monkey P1 concern.

### Broad vs detailed SOC handling

The one broad SOC observed in Anthropic source is `19-1020` (Biological Scientists, All Other — `XX-XXX0` pattern). The current Bronze ingestor **keeps it verbatim**; the spec's Silver layer is responsible for "Expand broad codes (XX-XXX0) where possible via SOC hierarchy" (Spec §Zone 2.1). That split of concerns is correct — Bronze preserves the source, Silver normalizes.

**No change recommended at the Raw zone.** Flag for @silver-transformer: when expanding `19-1020` against `SOC_Structure.csv`, the broad → detailed expansion is 1-to-many and will require the same N-way split (`observed_exposure_pct / n_detailed`) as the task-level fan-out to avoid inflating the global total. This is a Silver concern, not an entity-resolution concern.

### N-way fan-out defense

- Correct by math (verified in EDA): `sum(task_pct / N) = sum(task_pct) = 100 - 1.78`, preserving the global invariant.
- Max fan-out observed: 34 SOCs for one task. Split is mathematically principled (maximum entropy — no weighting data available) and documented.
- Alternative weighted split (by `Incumbents Responding`) rejected in EDA because 27% of that column is null. Sound decision.

**Verdict on fan-out: DEFENSIBLE.**

---

## 5. Cross-Release Identifier Drift

The spec ingests a **snapshot release** (currently `release_2025_03_27`). Newer HuggingFace releases (`release_2026_01_15`, `release_2026_03_24`) publish only raw conversation snapshots without `task_pct_v2.csv`. When Anthropic re-publishes task-level aggregates in a future release, the identifier space may shift:

| Risk | Severity | Handling |
|------|---------|---------|
| New task strings appear (O*NET taxonomy revision) | MEDIUM | Handled naturally — new rows join or become unmapped |
| Existing task strings re-worded (e.g. "troubleshoot" → "diagnose and troubleshoot") | LOW | Would miss the join; current recipe would not recover these |
| O*NET bridge itself changes Task IDs (O*NET re-numbers) | LOW | Bronze `task_id` shifts; Silver is unaffected (keyed on SOC, not task_id) |
| SOC 2018 → SOC 2028 revision | HIGH (future) | Entire occupation taxonomy re-codes; full re-resolution needed. Out of scope here — would require a new spec. |

**Advisory:** at the next release ingest, run a diff of `task_name` sets against this release's 3,365 and log adds/drops/re-wordings. No registry needed now — one release, one crosswalk, one snapshot.

---

## 6. Is an entity registry warranted?

**No.**

The entity-registry pattern (`governance/entity-registry.json`) is designed for cases where:
- entities have stable canonical IDs that need to be reconciled across heterogeneous sources,
- lifecycle events (mergers, renames, splits) need to be tracked over time,
- confidence scoring matters because match quality varies.

None of these apply here:
1. **Tasks are not canonical entities in FutureProof's domain.** FutureProof's canonical entity is the SOC occupation. Tasks are intermediate — used only to compute `observed_exposure_pct` per SOC, then discarded above Bronze.
2. **The task↔SOC relationship IS the O*NET bridge**, a government-authoritative crosswalk. There is no ambiguity to resolve — it is the ground truth for this pipeline.
3. **Match confidence is binary** — a task text either exactly matches O*NET after deterministic normalization (3,364/3,365) or it is the `none` placeholder (1/3,365). No fuzzy matching, no 0.7-confidence cases to triage.
4. **No lifecycle events.** A task doesn't "merge with" another task across releases — the release is a snapshot, the crosswalk is static.

The domain-context.md already treats SOC as the canonical occupation identifier, shared across BLS, O*NET, Karpathy, and now Anthropic ingestors. The existing `cde-registry` / data contracts cover SOC as a shared CDE — that is the correct locus for entity governance, not a per-source task-level registry.

---

## 7. Resolution Statistics

| Metric | Value |
|--------|------:|
| Total source tasks processed (`task_pct_v2`) | 3,365 |
| Resolved to ≥1 SOC (confidence 1.0, exact text after normalization) | 3,364 (99.97%) |
| Placeholder (expected unmapped, emits NULL-SOC Bronze row) | 1 (0.03%) — `task_name='none'` |
| Flagged for review | 0 |
| Bronze rows emitted (composite `(task_id, soc_code)` grain) | **4,082** (matches spec tolerance band 3,800–4,400) |
| Task↔SOC fan-out tasks (≥2 SOCs) | 82 (spec) / 272 (EDA full-file) |
| SOC coverage vs. `consumable.occupation_profiles` | 61.3% (510/832) — known dataset limitation (Claude skews knowledge-work), documented in EDA |

---

## 8. Recommendations

| # | Recommendation | Priority | Owner |
|---|----------------|---------:|:------|
| 1 | **Do not build a per-source entity registry.** Task-to-SOC is a deterministic text crosswalk against an authoritative bridge. | — | @entity-resolver (closed) |
| 2 | Document in the Bronze data dictionary that `task_id` for the 7 multi-task-id `(text, SOC)` cases is "first-seen from O*NET row order." Non-deterministic on re-publish. | P2 / informational | @doc-generator |
| 3 | Add a defensive Unicode/smart-quote fold (`NFKC` + curly → straight quote → ASCII) to `_normalize_task_text` before the case/whitespace pass, to harden against future source drift. **Zero rows affected today.** | P2 / future-proofing | Future chaos-monkey cycle |
| 4 | On each new release ingest, emit a `task_name` diff report against the previous release — counts of added, dropped, and re-worded tasks — to catch silent join regression early. | P2 / operational | @data-analyst at next release refresh |

---

## 9. Audit Trail

- **Files read:**
  - `docs/specs/raw-ingest-anthropic-economic-index.md`
  - `governance/eda/raw-anthropic-economic-index-eda.md`
  - `src/raw/anthropic_economic_index_ingestor.py`
  - `governance/domain-context.md` (SOC/CDE context)
  - `data/raw/anthropic_economic_index/release_2025_03_27/task_pct_v2.csv` (full scan: 3,365 rows, ASCII/Unicode/quote audit)
  - `data/raw/anthropic_economic_index/release_2025_03_27/onet_task_statements.csv` (full scan: 19,530 rows, case/period/Unicode audit; `(text_key, SOC)` multi-task-id analysis)
- **Empirical verifications:**
  - Zero Unicode characters across either source file
  - Zero smart-quote / em-dash / en-dash across either source file
  - Zero normalization collisions within `task_pct_v2` (3,365 distinct raw strings → 3,365 distinct norm keys)
  - 272 distinct O*NET text keys map to ≥2 `Task ID`s — 7 of those collapse within a single SOC (listed above)
  - Zero O*NET `Task ID`s equal the literal string `"none"` (no collision with placeholder)
- **Decisions logged:** Trivial verdict with 3 advisories. No registry created. No resolution data written beyond this report.
- **Timestamp:** 2026-04-16
