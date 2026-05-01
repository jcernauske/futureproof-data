# Adversarial Audit — bronze.eada (raw zone)

**Auditor:** adversarial-auditor (Opus 4.7)
**Date:** 2026-04-30
**Spec under audit:** `docs/specs/full-pipeline-eada.md` §3 + §4
**Artifacts in scope:**
- `governance/eda/full-pipeline-eada-raw-eda.md`
- `src/raw/eada_ingestor.py`
- `governance/dq-rules/raw-eada.json`
- `governance/dq-scorecards/raw-eada-20260501T040238Z.md`
- `governance/chaos-reports/raw-eada-chaos.md`
- `governance/domain-context.md` §EADA
- `/tmp/chaos-eada/chaos_harness.py` + `/tmp/chaos-eada/results.json`

**Verdict for orchestrator:** **CLEAR for governance review.** No blocking findings; one P2 disclosure recommendation and two non-blocking chaos-flagged gaps that are honestly out of spec scope.

---

## Section 1 — Did the chaos campaign hold up?

**Yes — every load-bearing claim is independently verifiable.**

### 1.1 Restoration claim — VERIFIED

- The harness at `/tmp/chaos-eada/chaos_harness.py` is **proved read-only against disk** by inspection: it `pq.read_table(PARQUET).to_pandas()` once per run, mutates pandas copies in-memory, registers them into a fresh `duckdb.connect()` (no path), and never calls any write API on the parquet path. There are no `pq.write_*`, `pyarrow.write_table`, `df.to_parquet`, or shell-out paths.
- I re-computed `md5(parquet)` independently → `16948b7cd2801f9ac3513415416e64b7`. Matches the chaos report's pre- and post-campaign hash exactly. Disk untouched.

### 1.2 Per-cycle rule-result dump — VERIFIED

- `/tmp/chaos-eada/results.json` exists, is 2,113 lines, contains `baseline_pre`, `baseline_post`, and 11 cycle blocks with full `rule_results`. I spot-read the pre-flight dump: every one of the 12 rules returns `passed: true` with `violation=0` / `violation_rows=0`. Post-flight is identical. The harness is not silently mis-loading the corrupted data — `caught_map` is computed by checking `passed=False` per expected rule id, which is the correct semantics.

### 1.3 "All 6 targeted attacks caught" — VERIFIED INDEPENDENTLY

I re-built each attack from scratch (not invoking the harness) and re-ran the rule SQL from `governance/dq-rules/raw-eada.json` against a fresh DuckDB. Results:

| Attack | Expected fires | Observed fires (independent run) | Verdict |
|---|---|---|---|
| 1 — per-team leak (+600 rows, fan-out 150×4) | RAW-EAD-001, -003, -012 | 001 FAIL (row count 2640 > 2300), 003 FAIL (150 dup keys), 012 FAIL | MATCH |
| 2 — sentinel leak (25 NULLs + 5 `-1` per money col) | -004/-005/-006 + -007/-008/-009 | All six FAIL (5 violator rows on validity; non-null=2010/2040=98.5% on completeness) | MATCH |
| 3 — 10 plain negatives per money col | -004, -005, -006 | All three FAIL (10 violator rows each) | MATCH |
| 4 — 5 NULL UNITIDs + 9 collisions | -002, -003 | 002 FAIL (5 nulls), 003 FAIL (1 collision unitid w/ count=10 → 2 group rows) | MATCH |
| 5 — multi-year leak (8×2021 + 8×2023) | -010 | 010 FAIL (3 distinct years) | MATCH |
| 6 — anchor failure (drop all 60 rows >$100M) | -011 fires; -001 stays inside [1800,2300] | 011 FAIL; 001 PASS at 1980 rows | MATCH (the chaos report's nuance about RAW-EAD-001 not firing is correct) |

**Targeted score 6/6 confirmed. No claim I tested was false.**

### 1.4 Gap probes — VERIFIED

I re-ran each broad-cycle's two "out-of-rule-set" probes independently:

- `total_athletic_expenses = $9.99T` on 8 rows → **zero rules fire**. Confirmed gap: no upper-bound validity rule exists.
- `ingested_at = 1999-01-01` on 8 rows → **zero rules fire**. Confirmed gap: no freshness rule exists.

The 10/69 = 14.5% miss rate is real, and is exactly the two dimensions the chaos report claims it is.

---

## Section 2 — Hallucinated artifacts?

**None found. Every artifact threads back to either real-data inspection or an explicit spec citation.**

### 2.1 Column names — GROUNDED

Spec §3 originally proposed `EXP_TOTAL_TOTAL` / `REV_TOTAL_TOTAL` / `RECRUITEXP_TOTAL_TOTAL`. The EDA called this out as **WRONG** ("BLOCKING: Spec column names are wrong"), inspected the live `InstLevel.xlsx` extracted from the cached `EADA_2022-2023.zip`, and corrected to `GRND_TOTAL_EXPENSE` / `GRND_TOTAL_REVENUE` / `RECRUITEXP_TOTAL`. The xlsx is on disk at `data/raw/eada_cache/eada_2022_instlevel.xlsx` (1.5 MB) and the converted CSV at `data/raw/eada_cache/eada_2022.csv` (1.3 MB) — both real, not synthesized. I confirmed the parquet has exactly these columns under their target names. **Not hallucinated; corrected from a hallucinated baseline.**

### 2.2 Identity columns — GROUNDED

Lowercase `unitid` / `institution_name` (vs the spec's `UNITID` / `INSTNM` assumption) is also documented as a BLOCKING anomaly in the EDA and pinned in the ingestor with a quoted EDA citation. **Not hallucinated.**

### 2.3 Row count, distribution stats, zero-recruiting rate — GROUNDED

I re-queried the parquet directly:

| Claim in EDA / chaos report | Independent re-query | Match? |
|---|---|---|
| 2,040 rows | 2,040 | YES |
| 2,040 distinct UNITIDs | 2,040 | YES |
| Single `reporting_year=2022` | min=max=2022, 1 distinct | YES |
| 60 institutions > $100M expense | 60 | YES |
| Top expense = Ohio State $234,409,941 | $234,409,941 (Ohio State) | YES |
| 17.8% recruiting=$0 (363 rows) | 17.79%, 363 rows | YES |
| All three monetary fields 100% non-null | 0 nulls in each | YES |
| Max revenue $261M | $261,353,404 | YES |

**Three spot-checks the prompt asked for (2,040 rows; 60-institution >$100M tail; 17.8% zero-recruiting) all pass exactly.**

### 2.4 Threshold tightening (95→99% on -007/-008, 80→99% on -009) — JUSTIFIED

The DQ-rule file's `notes` block cites the EDA's exact recommendation text. EDA observed 100% non-null; 99% leaves 1% (~20-row) headroom for codebook drift. This is not "AI invented a stricter number" — the EDA explicitly recommended tightening because the spec-as-written threshold was below observed reality. Reasoning is sound and traceable. **Not hallucinated.**

### 2.5 RAW-EAD-012 reformulation — TRACEABLE

The spec's original RAW-EAD-012 ("post-filter row count within 1% of distinct UNITIDs") presupposed an in-pipeline filter. EDA discovered no filter is needed (separate file model). The DQ-rule writer kept the rule with revised SQL (`|count - distinct_unitids| <= max(1, 1% × distinct_unitids)`) as a regression tripwire. Both the spec §4 EDA-correction note and the DQ rule's `rationale` block cite each other. **Not hallucinated; traceable evolution under human-visible review.**

### 2.6 Schema fields — GROUNDED

Every field in `EadaIngestor.get_schema()` (unitid, institution_name, reporting_year, three monetary fields, four framework metadata fields) is also in the spec §4 raw schema table and present in the parquet (I listed columns: 10 columns, exact match). No invented columns.

---

## Section 3 — Are the chaos-flagged gaps real risks or over-reach?

**Honest call: the freshness gap is a real residual risk; the upper-bound gap is over-reach but cheap to add.**

### 3.1 RAW-EAD-013/-014 (upper-bound at $1B) — over-reach for the spec scope

- The hypothesis "total_athletic_expenses > $1B is implausible" is correct (max observed $234M, P99 $120M; $1B is ~4× the largest legitimate reporter). A $10T row would be ~42,000× the legit max — clearly garbage.
- BUT: the gap probe injected a contrived $10T value. The *realistic* failure modes for monetary-field corruption (unit error of cents-as-dollars: 100×; thousands-as-actual: 1000×) **would not be caught** by a $1B threshold either if the source institution is small ($1M cents-as-dollars = $10K, well under $1B). So the proposed rule catches only adversarial probes and 4-orders-of-magnitude unit errors, not the more plausible 100×/1000× unit-error case.
- A more useful rule would be a **distribution-shape regression** (e.g., P99 of expenses must remain in [$50M, $500M]) — but that requires multi-cycle baselining the chaos report did not do.
- **Verdict:** The $1B rule is harmless to add and the chaos report grades it correctly as P2 / non-blocking. It is a useful 4-OOM tripwire but not the bound on the more interesting failure modes. I would not block on it.

### 3.2 RAW-EAD-015 (freshness on `ingested_at`) — real residual risk

- `ingested_at` is the framework write timestamp. A stale value here means the ingestor is reading from a stale cache (`data/raw/eada_cache/eada_2022.csv`) without realizing it. Given this ingestor is **cache-first by default** (line 109-114 of `eada_ingestor.py`: "The ingestor reads `data/raw/eada_cache/eada_<year>.csv` by default and reports `source_method = 'csv_cache'`"), the failure mode "we re-ran the pipeline but silently re-emitted last cycle's data" is genuinely possible. The current parquet's `ingested_at` is `2026-05-01 03:55:34` — fresh today, but a regression that pinned it to an old date would be invisible to every existing rule.
- **Verdict:** This is a real gap, not over-reach. P2 is appropriately conservative; I would graduate it to P1 once a base zone exists, because the freshness check is the only defense against a stale-cache regression in cache-first ingest.

### 3.3 Net call

Both proposed rules are non-blocking for governance review of the bronze zone as currently scoped. The chaos report's GO verdict is supported.

---

## Section 4 — Cross-artifact consistency: PASS

Spot-checked the seven listed artifacts against each other and against the parquet. Findings:

- **Spec §3/§4 (post EDA-correction notes) ↔ EDA report ↔ ingestor constants ↔ DQ rules ↔ chaos report ↔ domain-context §EADA**: all converge on the same column names (`GRND_TOTAL_EXPENSE` / `GRND_TOTAL_REVENUE` / `RECRUITEXP_TOTAL` / lowercase `unitid` / `institution_name`), the same row count (2,040), the same single `reporting_year=2022`, the same 17.8% real-zero recruiting figure, the same 74.5% UNITID overlap with `bronze.college_scorecard_institution`, and the same separate-file model (no in-pipeline filter).
- **Scorecard ↔ rules**: scorecard at `governance/dq-scorecards/raw-eada-20260501T040238Z.md` shows 12/12 PASS with row count 2,040; rules JSON enumerates exactly the same 12 rules with matching priorities. Note the priority for RAW-EAD-009 is documented as P1 in both rules JSON and scorecard, and as P1 in chaos §5 — consistent. (The earlier scorecard summary line "P0 gate: PASS (10/10 passed)" plus "P1: 2/2 passed" sums to 12 — internally consistent.)
- **Spec §4 RAW-EAD-007/-008 priority** is P0 in spec and rules JSON. Spec table shows RAW-EAD-009 as P1; rules JSON has it as P1. Chaos report also shows it as P1. Consistent.
- **Domain-context ↔ EDA**: domain-context's $234M Ohio State anchor, 17.8% real-zero recruiting, and 74.5% UNITID overlap all match the EDA's measurements. Domain-context flags the FTE-source open question and the "revenue ≈ expense at grand total" structural identity — both legitimate flags surfaced in the EDA.
- **Ingestor docstring ↔ EDA "Configuration Pin"**: every constant called out in the EDA's "EadaIngestor Configuration Pin" block (`INSTITUTION_TOTAL_FILTER_COLUMN = None`, `DEFAULT_EXP_COLUMN = "GRND_TOTAL_EXPENSE"`, lowercase identity columns, 2022 reporting year) is mirrored in the ingestor's class-level constants at lines 141-154 of `eada_ingestor.py`, with a comment block citing the EDA report by path.

**One minor note (informational, not a finding):** the spec §4 DQ Rules table at lines 206-217 still shows the **pre-tightening** thresholds for RAW-EAD-007/-008 (≥ 95%) and RAW-EAD-009 (≥ 80%). The DQ-rules JSON reflects the tightened ≥ 99% thresholds with EDA-cited rationale. The spec is the source-of-truth document, but in this case the rules JSON's `notes` field correctly documents the divergence and rationale, and the EDA report (which the spec itself defers to) recommended the tightening. Either:
- (a) leave as-is and treat the rules JSON's note + EDA recommendation as the live truth, or
- (b) edit spec §4 to cite the EDA-tightened thresholds.

I would do (b) as a 30-second housekeeping step, but it is not a blocker. The audit-trail provenance is intact either way.

---

## Section 5 — Risk register (compact)

| # | Risk | Severity | Existing control | Verdict |
|--:|------|---------|------------------|---------|
| 1 | Chaos harness silently mis-loads corrupted data and reports false PASS | High | Per-cycle rule-result dump exists; harness is read-only by inspection; I independently re-ran 6 attacks and got matching results | **Strong**. Verified. |
| 2 | Disk parquet was mutated by chaos | Critical | MD5 pre/post identical; harness has no write paths | **Strong**. Verified. |
| 3 | Hallucinated column names | Critical | EDA caught spec's hallucinated `*_TOTAL_TOTAL` names against live data; ingestor pins corrected names with EDA citation | **Strong**. The hallucination was IN the spec — and was caught. |
| 4 | Hallucinated DQ thresholds | High | Every rule's `rationale` cites EDA observation text; tightened 95→99% / 80→99% is explicitly documented as EDA-recommended | **Strong**. Traceable. |
| 5 | Hallucinated EDA stats (row count, distributions, overlap %) | High | I re-queried the parquet for 2040 rows / 60 >$100M / 17.8% zero-recruit / Ohio State $234M — all match exactly | **Strong**. Verified. |
| 6 | Chaos coverage gap (no upper-bound rule) | Low | Identified, documented, P2 follow-up filed | **Adequate**. Add the rule when convenient; not blocking. |
| 7 | Chaos coverage gap (no freshness rule) on cache-first ingestor | Medium | Identified, documented, P2 follow-up filed | **Adequate today, but graduate to P1 with base zone**. The cache-first design makes stale-cache failure mode invisible without this rule. |
| 8 | Spec §4 DQ-rules table still shows pre-tightening thresholds | Low | Rules JSON `notes` documents the divergence + EDA citation | **Adequate**. Cosmetic spec-housekeeping, not blocking. |
| 9 | "Revenue ≈ expense" structural identity invalidates BSE-EAD-010 | (Out of scope for bronze) | Flagged in EDA + domain-context for base/consumable | **Strong** at this layer (deferred correctly). |

---

## Section 6 — Recommendations

1. **Non-blocking:** add RAW-EAD-013 (upper-bound on `total_athletic_expenses` at $1B) and RAW-EAD-014 (same for `total_athletic_revenue`) as the chaos report proposes. P2.
2. **Non-blocking but advisable:** add RAW-EAD-015 (freshness on `ingested_at` — within last 18 months). The cache-first ingest path makes this a real residual risk despite the contrived chaos probe. Consider P1 once base zone exists.
3. **Cosmetic:** edit spec §4 DQ Rules table to reflect the EDA-tightened thresholds for RAW-EAD-007/-008/-009, with a citation to the EDA report. Keeps the spec the unambiguous single source of truth.
4. **Future audit:** when the base zone ships, re-run this audit against `base.eada` with particular attention to the FTE-source decision (the spec, EDA, and domain-context disagree on Option A vs B vs C — Option C with explicit `fte_source` provenance was the domain-context recommendation; the spec still says Option A in §5 Decision 3). That divergence is the next likely place for a quiet hallucination to creep in.

---

## Final verdict

**bronze.eada is CLEAR for governance review.**

The chaos campaign holds up under independent verification. No hallucinated artifacts. The two flagged dimension gaps are honest disclosures of out-of-scope coverage holes, not over-reach — one (upper-bound) is cosmetic, one (freshness) is a real cache-first-ingest residual risk. Cross-artifact consistency is PASS modulo a 30-second cosmetic edit to the spec's DQ table to mirror the EDA-tightened thresholds.

The single most important finding of this audit: **the most dangerous hallucination in this pipeline was IN the spec** (the wrong `*_TOTAL_TOTAL` column names, the wrong "filter on `SPORT_CODE IS NULL`" mental model). The EDA agent caught it against live data. That is the system working as designed — the EDA gate is the layer where unverified spec assumptions get reality-checked, and it functioned correctly here.
