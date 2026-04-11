# Spec: raw-ingest-karpathy-ai-exposure

**Status:** READY
**Zone:** Raw → Silver → Gold → MCP
**Primary Agent:** @primary-agent
**Created:** 2026-04-09

---

## Problem Statement

Ingest Andrej Karpathy's AI Exposure Scores for 342 BLS occupations into the FutureProof pipeline. This is the missing data source that fills the **RES (AI Resilience) stat** and the **Fight AI boss** — currently null placeholders in `consumable.program_career_paths` and `consumable.career_branches`. Without this data, the pentagon renders 4 of 5 stats and the boss gauntlet runs 4 of 5 fights.

This is a small, SOC-keyed dataset (342 rows) that joins directly to existing BLS OOH data via `soc_code`. The pipeline produces a new Gold consumable table (`consumable.ai_exposure`) and triggers a re-promotion of the FutureProof engine tables to backfill `stat_res` and `boss_ai_score`.

## Source Data

- **Source:** Karpathy's `karpathy/jobs` GitHub repository
- **Primary file:** `scores.json` — AI exposure scores with rationale for 342 occupations, keyed by occupation slug
- **Secondary file:** `occupations.csv` — structured BLS data including SOC codes, occupation titles, and slug identifiers
- **Join logic:** `scores.json` is keyed by slug → `occupations.csv` maps slug → SOC code → pipeline joins on SOC code
- **URL (scores):** `https://raw.githubusercontent.com/karpathy/jobs/master/scores.json`
- **URL (occupations):** `https://raw.githubusercontent.com/karpathy/jobs/master/occupations.csv`
- **Fallback:** Manual download to `data/raw/karpathy_cache/` if GitHub returns 403/429
- **License:** Repository is public. Scores are LLM-generated (Gemini Flash via OpenRouter). Not copyrighted data — LLM output scoring public BLS occupation descriptions.
- **Scoring methodology:** Each occupation's full BLS Markdown description was sent to an LLM with a structured rubric. Score 0-10 measuring "how much will AI reshape this occupation" considering both direct automation and indirect productivity effects. Key heuristic: if the job can be done entirely from a home office on a computer, exposure is 7+.
- **Known limitations (must carry forward as metadata):**
  - Scores are LLM estimates, not empirical measurements
  - Self-referential bias: LLM scoring jobs for LLM replaceability
  - Does not account for demand elasticity, regulatory barriers, or social preferences
  - A high score does not predict job disappearance — it predicts reshaping
  - Karpathy himself called this "a saturday morning 2 hour vibe coded project"

## Success Criteria

- [ ] Raw data lands in Iceberg table `raw.karpathy_ai_exposure`
- [ ] All 342 occupations ingested with exposure scores and rationales
- [ ] SOC codes resolved from slug-to-occupation mapping
- [ ] Silver base table `base.karpathy_ai_exposure` produced with normalized SOC codes
- [ ] Gold consumable table `consumable.ai_exposure` produced with 1-10 RES score derivation
- [ ] `consumable.program_career_paths` re-promoted with `stat_res` and `boss_ai_score` backfilled
- [ ] `consumable.career_branches` re-promoted with `stat_res` delta populated
- [ ] DQ rules written and passing at each zone
- [ ] Data contract produced for `consumable.ai_exposure`
- [ ] Business glossary terms defined

---

## Zone 1: Bronze (Raw Ingest)

### Iceberg Table: raw.karpathy_ai_exposure

- **Grain:** One row per occupation (slug)
- **Dedup grain:** [slug]
- **Expected rows:** 342

### Ingestor

- **Class:** `KarpathyAiExposureIngestor` (extends `BaseIngestor`)
- **Location:** `src/raw/karpathy_ai_exposure_ingestor.py`
- **Implementation notes:**
  - Fetch `scores.json` and `occupations.csv` from GitHub raw URLs
  - Set `User-Agent: FutureProof/0.1 (jeff@hyenastudios.com)` header
  - If HTTP fetch fails (403/429), fall back to `data/raw/karpathy_cache/scores.json` and `data/raw/karpathy_cache/occupations.csv`
  - Parse `scores.json` — expected structure: `{"slug_name": {"exposure": 7, "rationale": "..."}, ...}`
  - Parse `occupations.csv` — columns: `title, category, slug, soc_code, median_pay_annual, median_pay_hourly, entry_education, work_experience, training, num_jobs_2024, projected_employment_2034, outlook_pct, outlook_desc, employment_change, url`
  - Join on `slug` to resolve SOC codes
  - Some occupations in `occupations.csv` have empty SOC codes (e.g., "Advertising, promotions, and marketing managers"). These rows must be preserved with `soc_code = null` and flagged — they can be manually resolved in Silver or matched by title.
  - Carry forward: `median_pay_annual`, `num_jobs_2024`, `entry_education` from `occupations.csv` — useful for Silver EDA cross-validation against our existing BLS OOH data

### Raw Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| slug | string | yes | Karpathy's occupation identifier (kebab-case, e.g., "financial-analysts") |
| occupation_title | string | yes | From occupations.csv `title` column |
| category | string | yes | Karpathy's BLS category grouping (e.g., "business-and-financial") |
| soc_code | string | no | SOC code from occupations.csv. Nullable — some occupations lack SOC. Format varies: may be XX-XXXX or empty. |
| exposure_score | int | yes | 0-10 AI exposure score from scores.json |
| rationale | string | yes | 2-3 sentence explanation from scores.json |
| median_pay_annual | double | no | From occupations.csv — for cross-validation only |
| num_jobs_2024 | long | no | From occupations.csv — for cross-validation only |
| entry_education | string | no | From occupations.csv — for cross-validation only |
| source_url | string | yes | GitHub raw URL for scores.json |
| ingested_at | timestamp | yes | Ingestion timestamp |
| source_method | string | yes | "github_download" or "local_cache" |
| load_date | date | yes | Date of load |

### DQ Rules (Bronze)

- Exposure score range: 0 ≤ exposure_score ≤ 10 (P0 — hard block)
- Exposure score non-null: 100% (P0)
- Rationale non-null: 100% (P0)
- Slug uniqueness: COUNT = COUNT(DISTINCT slug) (P0)
- Row count: 342 ± 5% (P0)
- SOC code format where present: matches `XX-XXXX` pattern (P1 — warn)
- SOC code coverage: expect ~95%+ non-null (P1 — warn, some occupations lack SOC)
- Occupation title non-null: 100% (P0)
- Cross-validation: compare median_pay_annual against our `raw.bls_ooh.median_annual_wage` for matching SOC codes. Flag rows where values differ by > 20% (P1 — warn, data may be from different BLS snapshots)

---

## Zone 2: Silver (Normalize + Model)

### Iceberg Table: base.karpathy_ai_exposure

- **Grain:** One row per occupation (soc_code)
- **Dedup grain:** [soc_code]
- **Promote pattern:** `brightsmith.infra.promote.promote()` with `compute_grain_id(row, ['soc_code'], prefix='kai')`

### Silver Transformations

1. **SOC code normalization:** Validate format as XX-XXXX. Strip any whitespace or trailing characters. Confirm hyphen in position 3.

2. **Null SOC resolution:** For rows where `soc_code` is null in Bronze, attempt title-based matching against `base.bls_ooh.occupation_title` using case-insensitive exact match first, then fuzzy match. If resolved, populate SOC and flag `soc_resolved_method = 'title_match'`. If unresolvable, mark `soc_resolved_method = 'unresolved'` and carry forward with null SOC (these rows will not join downstream but must be preserved for completeness).

3. **SOC cross-validation:** For every non-null SOC, verify it exists in `base.bls_ooh.soc_code`. Flag mismatches as `bls_match = false`. These would indicate SOC codes that Karpathy used but that don't appear in our BLS ingest (possible if he used a different BLS snapshot or SOC vintage).

4. **Broad SOC code expansion:** 46 occupations use broad SOC codes (XX-XXX0) that don't directly match BLS OOH detailed codes. For each broad code, find all detailed codes under the same prefix in `base.bls_ooh` (e.g., `15-1230` expands to `15-1231`, `15-1232`). Propagate the exposure score and rationale to each detailed code. Flag `soc_resolved_method = 'broad_expansion'`. This increases row count from ~342 to ~500+. If a broad code has zero detailed matches in BLS OOH, keep the broad code with `bls_match = false`.

5. **Duplicate SOC handling:** After broad expansion, if multiple rows map to the same detailed SOC code (from different slugs or expansion), take the row with the highest `num_jobs_2024` (largest employment) or if equal, first alphabetically by slug. Flag deduplicated rows.

6. **Exposure score passthrough:** `exposure_score` (0-10) carried verbatim. No rescaling at Silver — that's Gold's job.

7. **Rationale passthrough:** `rationale` carried verbatim. This is a display field for the frontend (shown when Fight AI boss results are presented).

### Silver Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| record_id | string | yes | Deterministic grain hash (prefix: `kai`) |
| soc_code | string | no | Normalized XX-XXXX. Null for unresolved. |
| slug | string | yes | Original Karpathy slug (retained for provenance) |
| occupation_title | string | yes | Karpathy's title |
| category | string | yes | Karpathy's BLS category |
| exposure_score | int | yes | 0-10 AI exposure score (verbatim from source) |
| rationale | string | yes | LLM-generated explanation |
| bls_match | boolean | yes | True if soc_code found in base.bls_ooh |
| soc_resolved_method | string | yes | "direct" (had SOC in source), "title_match" (resolved from title), "broad_expansion" (propagated from broad code), "unresolved" (no SOC) |
| source_load_date | date | yes | |
| ingested_at | timestamp | yes | Silver promotion timestamp |

### DQ Rules (Silver)

- Grain uniqueness on soc_code where non-null (P0)
- bls_match = true for ≥ 90% of rows with non-null SOC (P0 — if < 90% match, the SOC vintage is wrong and needs investigation)
- exposure_score unchanged from Bronze (P0 — no data mutation in Silver)
- soc_resolved_method distribution: expect ~70% "direct", ~15% "broad_expansion", ~10% "title_match", ~5% "unresolved" (P1 — adjusted for broad code expansion)
- Zero rows with null slug (P0)
- Rationale minimum length >= 100 characters (P1 — shortest observed in Bronze is 297 chars)
- Post-expansion grain uniqueness on soc_code where non-null (P0)

### Business Glossary Terms

| Term ID | Name | Definition |
|---------|------|-----------|
| BT-080 | AI Exposure Score (Karpathy) | An LLM-generated estimate (0-10) of how much current AI will reshape a given occupation, from Andrej Karpathy's US Job Market Visualizer. Score considers both direct automation and indirect productivity effects. Higher = more exposed. Produced by Gemini Flash evaluating BLS occupation descriptions against a structured rubric. Not an empirical measurement. |
| BT-081 | AI Exposure Rationale | A 2-3 sentence LLM-generated explanation of the key factors driving an occupation's AI exposure score. Sourced from Karpathy's scoring pipeline. Display field for the FutureProof frontend — shown on Fight AI boss results. |

---

## Zone 3: Gold (Consumable Product)

### Iceberg Table: consumable.ai_exposure

- **Grain:** One row per SOC code
- **Dedup grain:** [soc_code]
- **Promote pattern:** `compute_grain_id(row, ['soc_code'], prefix='aie')`
- **Filter:** Only rows where `bls_match = true` (we only produce a consumable for occupations that exist in our BLS data)

### Gold Transformations

1. **RES Score Derivation (1-10):** The Karpathy exposure score measures how *exposed* a job is to AI (higher = more exposed). FutureProof's RES stat measures *resilience* — the inverse. A highly exposed job has low resilience.

```
stat_res = MIN(11 - exposure_score, 10)
```

| Karpathy exposure_score | stat_res | Meaning |
|------------------------|----------|---------|
| 0 (minimal exposure) | 10 | Highly resilient |
| 1 | 10 | (floor at 10 — 0 and 1 both map to max resilience) |
| 2 | 9 | |
| 5 (moderate) | 6 | |
| 7 (high) | 4 | |
| 9 (very high) | 2 | |
| 10 (maximum exposure) | 1 | Minimal resilience |

Edge case: `exposure_score = 0` → `stat_res = 11` → cap at 10. Apply `MIN(11 - exposure_score, 10)`.

2. **Boss AI Score Derivation (1-10):** The Fight AI boss strength is the *exposure* itself — higher exposure means a harder fight:

```
boss_ai_score = MAX(exposure_score, 1)
```

Floor at 1 (every boss has at least strength 1). Karpathy 0 → boss_ai_score 1. Karpathy 10 → boss_ai_score 10.

3. **Rationale carried forward** as a display field.

### Gold Schema

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| record_id | string | yes | Deterministic grain hash (prefix: `aie`) |
| soc_code | string | yes | Normalized XX-XXXX (non-null — filtered at Gold) |
| occupation_title | string | yes | |
| exposure_score | int | yes | Original 0-10 Karpathy score (preserved for transparency) |
| stat_res | int | yes | AI Resilience stat, 1-10 (derived: `MIN(11 - exposure_score, 10)`) |
| boss_ai_score | int | yes | Fight AI boss strength, 1-10 (derived: `MAX(exposure_score, 1)`) |
| rationale | string | yes | LLM explanation — display field for Fight AI narrative |
| category | string | yes | Karpathy's BLS category grouping |
| promoted_at | timestamp | yes | Gold promotion timestamp |

### DQ Rules (Gold)

- stat_res range: 1 ≤ stat_res ≤ 10 (P0)
- boss_ai_score range: 1 ≤ boss_ai_score ≤ 10 (P0)
- Inverse invariant: stat_res + boss_ai_score = 11 for all rows where exposure_score ≥ 1 (P0)
- Row count: matches Silver filtered count (P0)
- soc_code uniqueness (P0)
- rationale non-null (P0)
- Cross-validation with occupation_profiles: every soc_code in ai_exposure must exist in consumable.occupation_profiles (P0 — these tables must be joinable)

### Data Contract: consumable.ai_exposure

| Property | Value |
|----------|-------|
| Owner | @data-steward |
| SLA | Updated when Karpathy source updates (event-driven, not scheduled) |
| Freshness | Static — single load for hackathon MVP. Post-hackathon: re-score quarterly using Gemma. |
| Quality tier | Medium (LLM-generated scores, not empirical data) |
| Consumers | consumable.program_career_paths (backfill), consumable.career_branches (backfill), Gemma MCP agent, frontend stat display |
| Row count guarantee | 300-350 rows (342 expected, minus any unresolved SOC) |
| Null guarantee | stat_res: 0% null. boss_ai_score: 0% null. rationale: 0% null. |

---

## Zone 4: Backfill Existing Gold Tables

After `consumable.ai_exposure` is promoted, the FutureProof engine tables must be re-promoted to fill the placeholder nulls.

### consumable.program_career_paths — Backfill

Add a LEFT JOIN to the existing join chain:

```sql
LEFT JOIN consumable.ai_exposure aie ON pcp.soc_code = aie.soc_code
```

Update:
- `stat_res = aie.stat_res` (was null placeholder)
- `boss_ai_score = aie.boss_ai_score` (was null placeholder)
- `stats_available_count` — recompute (will increase by 1 for matched rows)
- `bosses_available_count` — recompute (will increase by 1 for matched rows)
- `overall_confidence` — recompute (may improve tiers)

This is a re-run of the Gold FutureProof engine spec with one additional source. The existing join chain, stat derivations, and DQ rules are unchanged — only the two null fields get filled.

**Expected coverage:** The BLS OOH has 832 occupations; Karpathy scored 342 of them (the OOH subset). The crosswalk maps Scorecard programs to SOC codes that may or may not be in Karpathy's 342. Expected coverage: ~80-90% of `program_career_paths` rows where the SOC code is one of the 342 scored occupations. Remaining rows keep null RES/AI.

### consumable.career_branches — Backfill

Add LEFT JOINs for both source and target occupations:

```sql
LEFT JOIN consumable.ai_exposure aie_src ON cb.soc_code = aie_src.soc_code
LEFT JOIN consumable.ai_exposure aie_tgt ON cb.related_soc_code = aie_tgt.soc_code
```

Populate `stat_res` and `boss_ai_score` for both source and target nodes. Compute `stat_res_delta` = `target.stat_res - source.stat_res` (showing how AI resilience shifts along a career branch).

---

## Zone 5: MCP (Tool Interface)

### New MCP Tool: `get_ai_exposure(soc_code)`

Exposes `consumable.ai_exposure` to the Gemma agent via function calling.

**Input:** `soc_code` (string, XX-XXXX format)

**Returns:**
```json
{
  "soc_code": "13-2051",
  "occupation_title": "Financial analysts",
  "exposure_score": 8,
  "stat_res": 3,
  "boss_ai_score": 8,
  "rationale": "Financial analysts work almost entirely on computers, processing data, building models, and generating reports. AI tools are already handling data aggregation and basic forecasting, making the core analytical tasks highly automatable.",
  "category": "business-and-financial"
}
```

**Null case:** If soc_code not found, returns `null` with a message indicating no AI exposure data is available for this occupation. Gemma should handle this gracefully in guidance generation.

### Updated MCP Tool: `get_career_path_stats(unitid, cipcode)`

The existing MCP query against `consumable.program_career_paths` now returns non-null `stat_res` and `boss_ai_score` for matched occupations. No tool signature change needed — the fields were already in the schema, just null. This is a data-level fix, not an interface change.

---

## Agent Workflow

1. @governance-reviewer — Pre-implementation review
2. @primary-agent — Implement ingestor (`fetch`, `flatten`, `get_schema`)
3. @data-analyst — EDA + domain discovery (focus on: SOC coverage vs. our BLS data, score distribution, null SOC resolution)
4. @domain-context — Synthesize domain knowledge (Karpathy methodology, limitations, how FutureProof uses it)
5. @dq-rule-writer — Write DQ rules for Bronze + Silver + Gold
6. @dq-engineer — Execute rules, produce scorecards
7. @semantic-modeler — Conceptual → logical → physical models (Silver + Gold)
8. @primary-agent — Build Silver transformer + Gold transformer
9. @primary-agent — Re-promote FutureProof engine tables (backfill stat_res + boss_ai_score)
10. @data-contract-author — Data contract for consumable.ai_exposure
11. @lineage-tracker — OpenLineage capture
12. @cde-tagger — CDE mapping
13. @doc-generator — Data dictionary entries for all new fields
14. @governance-reviewer — Post-implementation check
15. @staff-engineer — Final review

## Governance Artifacts

- [ ] EDA report: `governance/eda/raw-karpathy-ai-exposure-eda.md`
- [ ] Domain context: `governance/domain-context.md` (append Karpathy section)
- [ ] DQ rules: `governance/dq-rules/raw-ingest-karpathy-ai-exposure.json`, `governance/dq-rules/silver-base-karpathy-ai-exposure.json`, `governance/dq-rules/gold-ai-exposure.json`
- [ ] DQ scorecards: `governance/dq-scorecards/raw-ingest-karpathy-ai-exposure-scorecard.md`, etc.
- [ ] Models: `governance/models/silver-base-karpathy-ai-exposure-{conceptual,logical,physical}.md`, `governance/models/gold-ai-exposure-{conceptual,logical,physical}.md`
- [ ] Data contract: `governance/data-contracts/consumable-ai-exposure.md`
- [ ] Lineage: `governance/lineage/raw-ingest-karpathy-ai-exposure-{timestamp}.json`
- [ ] Business glossary updates: BT-080, BT-081 added
- [ ] Data dictionary entries for all raw, Silver, and Gold table fields

## Cross-Source Integration Notes

This is the fourth data source in the FutureProof pipeline:

1. **College Scorecard** (COMPLETE) — program-level outcomes, CIP codes
2. **BLS OOH** (COMPLETE) — occupation projections and requirements, SOC codes
3. **O*NET** (COMPLETE) — task-level occupation data, SOC codes
4. **Karpathy AI Exposure** (this spec) — AI exposure scores, SOC codes

Join topology:
```
Karpathy (soc_code)
  → consumable.ai_exposure
    → LEFT JOIN into consumable.program_career_paths (via soc_code)
    → LEFT JOIN into consumable.career_branches (via soc_code + related_soc_code)
  → MCP tool: get_ai_exposure(soc_code)
```

This completes the five-stat pentagon and the full boss gauntlet. After this pipeline runs:
- **stat_res:** populated (was null) ✅
- **boss_ai_score:** populated (was null) ✅
- **stat_ern, stat_roi, stat_grw, stat_hmn:** unchanged ✅
- **boss_loans, boss_market, boss_burnout, boss_ceiling:** unchanged ✅
- **Pentagon:** 5/5 stats available for Karpathy-covered occupations ✅
- **Gauntlet:** 5/5 bosses + Final Boss fully functional ✅

## Estimated Effort

This is a small, clean dataset. SOC-keyed, 342 rows, one score per occupation.

| Step | Estimate |
|------|----------|
| Bronze ingest + EDA | 1-2 hours |
| Silver transform + models | 1-2 hours |
| Gold transform + contract | 1-2 hours |
| FutureProof engine re-promote (backfill) | 1 hour |
| MCP tool addition | 30 minutes |
| DQ rules + governance artifacts | 1-2 hours |
| **Total** | **~6-10 hours** |

---

## Post-Hackathon: Re-Scoring with Gemma

For the hackathon, we use Karpathy's scores as-is. Post-hackathon, FutureProof should re-generate AI exposure scores using Gemma 4, incorporating:

- O*NET task-level data (more granular than BLS job descriptions)
- Anthropic's Labor Market Research (actual vs. theoretical AI adoption)
- Updated BLS data as it refreshes
- Our own scoring rubric tuned for the FutureProof empowerment framing

This would replace Karpathy's Gemini Flash scores with Gemma-generated scores, published with methodology and benchmarks. The pipeline architecture (Bronze → Silver → Gold → MCP) stays identical — only the source data changes. That's the beauty of the governed pipeline: swap the source, re-run, same DQ gates validate the output.

---

*— End of Spec —*
