## Temporal Design: raw-ingest-anthropic-economic-index

**Date:** 2026-04-16
**Agent:** @temporal-modeler
**Domain:** Observed AI Exposure — Empirical Claude-Usage Signal at SOC Level
**Spec:** docs/specs/raw-ingest-anthropic-economic-index.md
**Bitemporal Required:** NO
**Verdict:** TRIVIAL (release-stamp sufficient)
**Decision:** Keep the existing release-stamp model (`source_release` column + Iceberg snapshots). Do NOT introduce SCD-2 columns. Add two small guard rails described in §Schema Changes.

---

### Temporal Characteristics

| Characteristic | Assessment |
|---------------|-----------|
| Data shape | Periodic full-file release published by Anthropic. Each release is a self-contained global snapshot of Claude usage over some prior observation window. |
| Source-side valid time | Partially implicit. Each release covers a window of Claude conversations (e.g. `release_2025_03_27` reflects traffic observed up to March 2025). Anthropic does NOT surface per-row `observed_from` / `observed_to` columns — the entire release is a single-window aggregate. |
| Grain | Bronze: `(task_name, soc_code)` composite (4,082 rows at `release_2025_03_27`). Silver: `soc_code` (≈588 rows). |
| Refresh cadence | Irregular. Releases appear when Anthropic publishes them (~ quarterly). Spec currently pins to `release_2025_03_27` because `release_2026_01_15/` and `release_2026_03_24/` lack the `task_pct_v2.csv` task-level aggregate. |
| Amendment mechanism | Whole-release replacement. Anthropic does not issue row-level corrections to a prior release; they publish a new release. A release, once published, is immutable upstream. |
| Supersession semantics | Release-level only. `release_2026_03_24` (when/if it gains task-level aggregates) would logically supersede `release_2025_03_27` in full. No within-release row supersession. |
| Valid-time granularity needed downstream | Release-level. Consumers ask "what did Anthropic report as of release X" — never "what did Anthropic report as of 2026-02-14 specifically." |

The data is a sequence of **immutable, versioned, full-table snapshots** published at a coarse cadence. This is a textbook "release-stamped" dataset, not an effective-dated time series.

---

### Valid Time Design

**No explicit `valid_from` / `valid_to` columns required.**

The appropriate valid-time proxy is `source_release`, which is already in the Bronze, Silver, and Gold schemas:

- Bronze: `source_release` (per-row, required) + `ingested_at` (per-row, required)
- Silver: `source_release` (carried through the aggregation)
- Gold: `anthropic_source_release` (new, nullable — rows with no Anthropic match stay NULL)

`source_release` is the semantic validity token. It tells the consumer which empirical window Anthropic was measuring. That is the only valid-time question this dataset can honestly answer.

Manufacturing `valid_from` = release date and `valid_to` = next release date would be defensible, but:

1. It duplicates information already encoded in `source_release`.
2. It lies about precision — Anthropic's measurement window and their publication date are not the same thing, and neither is reliably documented.
3. The only consumer (`consumable.ai_exposure`, Gold) and the downstream S4 composite read a single-current-release view. They never filter by "what did Anthropic think on date X."

Skipping synthetic valid-time columns is the honest call.

---

### Transaction Time Strategy

**Iceberg snapshot history + `(source_release, ingested_at)` is sufficient.**

The transaction-time story has two layers, which together cover every question downstream actually asks:

| Question | Answered By |
|----------|-------------|
| "When did we first record this row in our system?" | `ingested_at` (per-row) |
| "Which Anthropic publication does this row come from?" | `source_release` (per-row) |
| "What did our Gold table look like on date X?" | Iceberg time travel: `AT (TIMESTAMP => 'X')` on `consumable.ai_exposure` |
| "What changed between our last ingest and this one?" | Diff two Iceberg snapshots of `raw.anthropic_economic_index` |
| "Roll back a bad ingest." | Iceberg snapshot rewind on the Bronze table |

`(source_release, ingested_at)` jointly act as a **release-effective + system-effective** pair:

- `source_release` = **business-effective date proxy** (which Anthropic world-view)
- `ingested_at` = **system-effective timestamp** (when we wrote that world-view into our lake)

That is functionally the same information SCD-2 would encode, without the row-explosion cost of maintaining per-row `valid_from` / `valid_to` / `is_current` flags.

#### Iceberg snapshot strategy

| Event | Snapshot action | Rationale |
|-------|-----------------|-----------|
| Initial ingest of `release_2025_03_27` | One new snapshot on Bronze → Silver → Gold | Baseline |
| Re-ingest same release (bug fix, new DQ rule) | New snapshot on each affected table | Previous state recoverable via time travel; no row-level supersession needed |
| Ingest a newer release (e.g. a future `release_2026_XX_XX` that ships task-level aggregates) | **Full overwrite** of Bronze + Silver; Gold re-derives. New Iceberg snapshot on each table. | Anthropic's release model is whole-table. Matching it with whole-table replacement keeps semantics honest. |
| Downstream needs historical release | Query Iceberg snapshot at the `ingested_at` of the prior release | No extra machinery required |

Keeping multiple releases co-resident as rows (e.g. a `release_2025_03_27` row AND a `release_2026_03_24` row for the same SOC) is **rejected**:

- Gold `consumable.ai_exposure` has grain `soc_code`. Two Anthropic releases per SOC violates that grain.
- The S4 composite and the MCP `get_ai_exposure` tool want "the current observed exposure for this SOC," not a history. They would have to always filter `WHERE source_release = (latest)` — which is exactly what a full-overwrite strategy gives them for free.
- If someone ever needs the old release, Iceberg time travel to the pre-replacement snapshot is the correct mechanism.

---

### Correction / Amendment Handling

**Release-level, handled via Iceberg snapshots.**

1. Anthropic does not amend a published release. Corrections arrive as a new release.
2. Our own corrections (DQ fix, normalization bug, re-derivation) produce a new Iceberg snapshot on the affected Brightsmith table(s). `ingested_at` captures the recording time; `source_release` stays the same.
3. The prior (buggy) state is always recoverable via Iceberg time travel.
4. No per-row `is_correction`, `corrects_record`, or `superseded_by` columns needed — there is no row-level correction pattern in this data.

If in future a release ships with a `release_notes_amend` file describing row-level retractions (unlikely based on Anthropic's publication pattern), revisit this decision.

---

### Point-in-Time Query Support

**All downstream point-in-time queries are release-scoped or "latest."**

Supported patterns:

```sql
-- "What did Anthropic's release_2025_03_27 report for Computer Programmers?"
SELECT observed_exposure_pct, automation_pct
FROM base.anthropic_observed_exposure
WHERE soc_code = '15-1251'
  AND source_release = 'release_2025_03_27';

-- "What does our Gold table currently think?"
SELECT observed_exposure_pct, automation_pct, anthropic_source_release
FROM consumable.ai_exposure
WHERE soc_code = '15-1251';

-- "What did our Gold table look like on 2026-03-15?" (Iceberg time travel)
SELECT observed_exposure_pct, anthropic_source_release
FROM consumable.ai_exposure AT (TIMESTAMP => '2026-03-15 00:00:00')
WHERE soc_code = '15-1251';

-- "Diff two releases" (compare Iceberg snapshots of Silver)
-- snapshot N (release_2025_03_27) vs snapshot N+1 (release_2026_XX_XX)
```

No query pattern currently planned or foreseeable within the hackathon MVP requires per-row bitemporal reconstruction.

---

### Downstream Impact When a New Release Lands

This is the key governance question. When a future release adds task-level aggregates and we swap:

| Consumer | Impact | Mitigation |
|----------|--------|------------|
| `consumable.ai_exposure.observed_exposure_pct` | Values change for every SOC with Anthropic coverage. | Required P2 regression test: snapshot the Gold table before swap, diff after. Alert on deltas >N% per SOC. |
| `consumable.ai_exposure.automation_pct` | Values change. | Same regression gate. |
| `consumable.ai_exposure.anthropic_source_release` | Column updates to new release string. | Acts as the **detectable signal** for consumers that the release swapped. MCP server and S4 should log this. |
| S4 three-signal composite (`res_composite`) | Velocity signal (observed/theoretical) shifts. | S4 DQ rule: fail if composite swings >N std-dev without explicit operator override (mirrors the existing `AI_EXPOSURE_AB_OVERRIDE` gate in `src/gold/ai_exposure_transformer.py`). |
| `stat_res` (5-stat pentagon) in `program_career_paths` | Fed by `consumable.ai_exposure`, so shifts with it. Frontend will show different pentagon values for the same SOC. | Frontend has no release awareness. Acceptable — students always see the latest view. |
| `boss_ai_score` / "Fight AI" boss tuning | Derived from RES. Shifts when release swaps. | Existing `ai_exposure_ab_override` A/B framework already guards this. |
| MCP `get_ai_exposure` tool | Returns new values. Gemma prompt context unchanged. | Consider surfacing `anthropic_source_release` in the tool response so the model can self-cite. |

**Recommendation:** Surface `anthropic_source_release` through the MCP `get_ai_exposure` response payload so Gemma-generated career guidance can cite the empirical source window. This is a one-line addition in `src/mcp_server/futureproof_server.py` when S4 goes live, not a pipeline concern.

---

### Schema Changes

**None to the core bitemporal model.** Two small additions strengthen release governance without changing the shape:

1. **Silver table: add `ingested_at`** (timestamp, required). The spec's Silver schema currently has `promoted_at` but not `ingested_at`. For release governance and time-travel join parity with Bronze, propagate `ingested_at` from Bronze to Silver so consumers can reason about system-effective time without joining back to Bronze.
2. **Gold table: add `anthropic_ingested_at`** (timestamp, nullable). Companion to the already-planned `anthropic_source_release`. Together they answer "which release, ingested when" without a round-trip to Silver. Trivial in the existing `ai_exposure_transformer.py` JOIN.

Both are additive, nullable-safe, and do not require bitemporal columns, supersession flags, or SCD-2 row explosion.

---

### Trade-offs Considered

| Trade-off | Resolution |
|-----------|------------|
| Adopt SCD-2 on `base.anthropic_observed_exposure` (`valid_from`, `valid_to`, `is_current` per (SOC, release))? | **Rejected.** Row-level validity is finer than the data supports. Iceberg snapshot history already gives full release history for free. SCD-2 would triple the row count across three releases for zero query benefit given current access patterns. |
| Keep multiple releases co-resident in Silver (one row per (SOC, release))? | **Rejected.** Breaks the `soc_code` Silver grain and forces every downstream consumer to carry a "latest release" filter. Iceberg snapshots store this history without contaminating live grain. |
| Treat `source_release` as the valid-from and compute valid-to from release ordering? | **Rejected.** The publication schedule is irregular and not tracked in-band. A synthetic valid-to would be wrong as often as it's right. |
| Omit `source_release` entirely and lean only on Iceberg snapshots? | **Rejected.** Release provenance is a business fact (attribution, CC-BY citation), not a system fact. It belongs in the row. |
| Branch the Iceberg table per release (Iceberg branches/tags)? | **Rejected for now.** Iceberg branching is appropriate if we need to query multiple releases concurrently as first-class views. We don't. Tag the snapshot after each release swap (e.g. `tag: release_2025_03_27`) — that is cheap and provides a named pointer for time travel without branching complexity. |
| Keep overwrite-on-release vs. append-on-release? | **Overwrite.** Matches Anthropic's own publication semantics and preserves Silver/Gold grain. Prior state stays recoverable via Iceberg. |

---

### Recommendation (3–5 bullets)

- **Keep the current design.** `source_release` (per-row) + `ingested_at` (per-row) + Iceberg snapshots jointly satisfy every temporal requirement this dataset has. SCD-2 is over-engineering for a release-stamped, whole-file-replacement source.
- **Release-swap strategy is full overwrite of Bronze → Silver → Gold** with a new Iceberg snapshot on each table. Tag each post-swap snapshot with the release name (e.g. Iceberg tag `release_2025_03_27`) so operators have a named handle for time travel.
- **Add `ingested_at` to the Silver schema and `anthropic_ingested_at` to the Gold schema.** Additive, nullable, no grain impact — gives consumers a `(release, recorded-at)` pair without a Bronze round-trip.
- **Gate future release swaps with a regression check** on `consumable.ai_exposure.observed_exposure_pct` / `automation_pct` drift and on the S4 `res_composite` distribution. Reuse the existing `AI_EXPOSURE_AB_OVERRIDE` operator override pattern. A silent release swap that shifts RES scores would be a serious user-facing regression.
- **Surface `anthropic_source_release` in the MCP `get_ai_exposure` tool response** when S4 ships so Gemma can cite which empirical window informed its guidance. No pipeline change — backend/MCP concern only.

---

*— End of Temporal Assessment —*
