# Adversarial Audit: raw-ingest-anthropic-economic-index

- **Auditor:** adversarial-auditor (skeptical governance reviewer)
- **Date:** 2026-04-16
- **Spec:** `docs/specs/raw-ingest-anthropic-economic-index.md`
- **Verdict:** **CONCERNS_FOUND** — the data-analyst EDA numbers and the headline pipeline assertions (SUM(task_pct)=100, fan-out split, automation = directive + feedback_loop) are materially accurate. The critical governance gap is a set of **missing downstream artifacts** that the spec's §Governance Artifacts checklist explicitly requires and that the upstream agents have not produced.

---

## 1. EDA number spot-checks (against source CSVs)

The auditor ran pandas directly against
`data/raw/anthropic_economic_index/release_2025_03_27/` and compared 9 EDA
headline claims. **Every load-bearing claim verifies.**

| EDA claim | Source truth | Verdict |
|---|---|---|
| `task_pct_v2.csv`: 3,365 rows, 2 cols | 3,365 rows, 2 cols (`task_name`, `pct`) | PASS |
| `automation_vs_augmentation_by_task.csv`: 3,364 rows, 7 cols | 3,364 rows, 7 cols (exact column match) | PASS |
| `onet_task_statements.csv`: 19,530 rows, 8 cols | 19,530 rows, 8 cols | PASS |
| `SOC_Structure.csv`: 1,596 rows, 6 cols | 1,596 rows, 6 cols | PASS |
| `SUM(pct) = 100.0000` | 100.000000 (machine-verified) | PASS |
| `pct` range `[0.001541, 6.650740]`, median 0.005444 | exact match | PASS |
| `task_name='none'` placeholder with `pct=1.78` | found at row 1967, `pct=1.781672` | PASS |
| 6-axis row-sum = 1.0 on all rows (3,364/3,364) | 3,364/3,364 satisfy \|sum-1\|<1e-6 | PASS |
| 1,066 fully-filtered tasks (`filtered ≥ 0.999`); 4 with `filtered == 0` | 1,066 and 4 exact | PASS |
| Anthropic tasks with ≥2-SOC fan-out = 82; max 34 SOCs | 82 Anthropic tasks, max 34 SOCs | PASS |
| 588 source SOCs; 4,081 SOC-matched pairs + 1 NULL = 4,082 Bronze rows | 4,081 matched + 1 placeholder = 4,082 | PASS |
| Top task by pct: "modify existing software..." at 6.6507 | verbatim match | PASS |

**Minor inaccuracy flagged but not material:** the EDA's §Field
Profiles table for `onet_task_statements` claims "272 task strings appear
under ≥2 SOCs (...); 18,156 tasks at N=1; ≥11 = 31." The true numbers
under the EDA's stated normalization (lowercase + rstrip `.`) are 265,
18,163, and 25 respectively. The headline number that feeds Bronze
row-count prediction (82 Anthropic-side multi-SOC tasks) is correct;
the 272 figure is a whole-O*NET stat that does not flow into any
downstream rule or schema. I judge this a drafting error, not a
hallucination that affects the pipeline.

---

## 2. Does the DQ scorecard reflect rule execution or is it fabricated?

The DQ run is **real, executable, and reproducible.** I re-ran
`scripts/dq_execute_aei.py` and got identical row counts and pass/fail
ledger, with a fresh run_id.

What actually runs:
1. Instantiates `AnthropicEconomicIndexIngestor` and calls
   `fetch()` + `flatten()` in-process against the real source CSVs.
2. Loads `base.bls_ooh` from the real Iceberg catalog.
3. Runs the Silver transformer to materialize 587 SOC rows.
4. Loads the current `consumable.ai_exposure` from Iceberg (815 rows)
   and re-blends with the in-memory Anthropic Silver output.
5. Registers the three tables in an in-memory DuckDB.
6. Executes every rule's SQL literally from
   `governance/dq-rules/*.json`.
7. Writes timestamped per-zone results JSONs and regenerates scorecards.

**Evidence that the data exists where the scorecards say it does:**
the scorecards declare "Rows in Table: 4,082 / 587 / 815." I reproduced
those exact row counts on a fresh run.

**Legitimate concern about the scorecard format, not the results:**

- The scorecard "Actual" column is the violation count, not the measured
  metric. For RAW-AEI-003 (SUM(task_pct) ≈ 100 ±0.1), the scorecard
  shows `actual=0`, which means "0 violations," but a reader would
  reasonably expect to see the actual SUM value (≈100.00). This is a
  presentation issue — a regulator would insist the scorecard record
  the measured metric, not just PASS/FAIL — but it is not hallucination.
- The SLV-AOE-015 P3 "dropped_none_pct" rule returns `0.19`, not the
  expected `~1.78` from the EDA. This suggests the rule is measuring
  a *fraction* of Bronze rows dropped (1/587 ≈ 0.17%), not the
  *volume share* (1.78%) the EDA documented. The rule is P3/tracked
  so it always passes, but the semantics are misleading. Flag for
  @dq-rule-writer.
- The published Bronze scorecard (pre-audit) showed **16/16 rules**.
  The rules bundle actually contains **17 rules** (RAW-AEI-019 was
  added post-chaos as the SOC regex defense-in-depth). The scorecard
  was stale by one rule until I re-ran the script. Severity: low —
  the missing rule passed on the re-run — but it is evidence that
  scorecards are not guaranteed in sync with the rules JSON.

---

## 3. Does the chaos manifest describe real injected scenarios?

Yes. Three layers of evidence exist:
- `governance/chaos-manifests/raw-anthropic-economic-index-chaos.md`
  (the narrative)
- `governance/chaos-manifests/anthropic_economic_index_chaos_runner.py`
  (1,077 LOC of actual runner code that copies the real release,
  mutates the copy, reinvokes `fetch()` + `flatten()`, captures
  stdout/exception text, and emits a structured verdict dict)
- `governance/chaos-manifests/raw-ingest-anthropic-economic-index-manifest.json`
  (executed artifact: 2 full cycles, 16 scenarios each, both with 2
  consecutive clean verdicts, concrete `injected`/`actual` strings
  showing the ingestor's real error messages — including LFS pointer
  stubs resolving to "CSV task_pct_v2.csv is missing required columns:
  ['pct', 'task_name']")

Scenarios cover the real risk surface: network failure, LFS pointer
stubs, malformed headers, missing columns, SOC format variations
(dash-less, overlay suffix, garbled), empty source file, duplicate
task_ids, filter-boundary rows, extreme fan-out, and the `none`
placeholder. The P1 chaos gap that was "hardened after 1 fix" is
traceable in the rules JSON: RAW-AEI-019 was explicitly added to enforce
the canonical `^\d{2}-\d{4}$` regex after the runner found
`_normalize_onet_soc` was accepting dash-less inputs — this is a
real, investigated, and closed loop.

I do not consider this fabricated.

---

## 4. Code matches spec on the critical assertions

Verified by reading `src/raw/anthropic_economic_index_ingestor.py`:

| Spec assertion | Code location | Verdict |
|---|---|---|
| Bronze SUM(task_pct) = 100 (global-share invariant, preserved across fan-out by pct/N split) | `flatten()` line ~538: `split_pct = raw_pct / n_soc` | CORRECT |
| Fan-out emits N rows per task for N distinct SOCs | `flatten()` line ~542 loops `for stmt in stmts` | CORRECT |
| Automation = directive + feedback_loop (NOT + learning) | `_collapse_automation()` line 804: `automation = (directive + feedback_loop) * 100.0`; line 805: `augmentation = (task_iteration + validation + learning) * 100.0` | CORRECT — this directly matches Anthropic's v2 methodology (learning = user-learns-from-Claude → augmentation) |
| `task_name='none'` row kept with soc_code=NULL and pct unchanged; Silver filters it | `flatten()` line ~518-532 emits NULL-SOC row with raw_pct; Silver drops rows where `_normalize_soc_code` returns None | CORRECT |
| `task_pct_v2.pct` already in 0-100 percent (not multiplied by 100) | `flatten()` line ~488: `raw_pct = self._coerce_double(row.get("pct"))` with no scaling | CORRECT |
| Composite grain `[task_id, soc_code]` with soc_code nullable | `get_schema()` lines 859-875 declare `soc_code` required=False | CORRECT |
| Chunked CSV read (50k rows) | `CSV_CHUNK_SIZE = 50_000`, `_read_csv_chunked()` | CORRECT |
| SOC normalization rejects malformed after RAW-AEI-019 fix | `_normalize_onet_soc()` lines 694-761 | CORRECT |

The 57 unit tests in `tests/raw/test_anthropic_economic_index_ingestor.py`
and `tests/silver/test_anthropic_observed_exposure_transformer.py`
all pass. Tests cover the `none` placeholder, fan-out split,
automation axis collapse (including the explicit assertion that
`learning` is NOT added to automation), schema drift, LFS pointer stubs,
and SOC recovery/rejection.

---

## 5. Governance completeness — MATERIAL GAPS

Comparing spec §Governance Artifacts (lines 406-423) to files on disk:

| Required artifact | On disk? | Severity |
|---|---|---|
| EDA report `governance/eda/raw-anthropic-economic-index-eda.md` | YES | — |
| Domain context updated (Anthropic section in `domain-context.md`) | YES (line 1627, "Anthropic Economic Index") | — |
| Bronze data contract `governance/data-contracts/raw-anthropic-economic-index.yaml` | **NO** | HIGH — CC-BY license block is spec-mandated to live here |
| Silver data contract `governance/data-contracts/base-anthropic-observed-exposure.yaml` | **NO** | HIGH |
| Gold data contract update `governance/data-contracts/consumable-ai-exposure.yaml` | **NO** (spec says "Modify"; file not present) | HIGH |
| Bronze DQ rules JSON | YES (17 rules) | — |
| Silver DQ rules JSON | YES | — |
| DQ scorecards (Bronze/Silver/Gold) | YES but one scorecard was stale until my re-run | MEDIUM |
| Chaos manifest `raw-anthropic-economic-index-chaos.md` | YES + runner .py + manifest.json | — |
| Lineage Bronze `governance/lineage/raw-anthropic-economic-index-{ts}.json` | **NO** | HIGH — spec §Agent Workflow step 8 `@lineage-tracker` has not run |
| Lineage Silver | **NO** | HIGH |
| Lineage Gold | **NO** | HIGH |
| Attribution entry in `LICENSE_SOURCES.md` at project root | **NO — file does not exist** | HIGH — the governance pre-review already flagged this (advisory 2: "action verb should be 'Create', not 'Modify'"), and it is still not created. **This is a CC-BY 4.0 compliance defect the spec calls out explicitly in §Attribution Requirements.** |
| Data dictionary entries for new fields | **NO** (no anthropic entries in `governance/data-dictionaries/`) | HIGH — spec requires it; @doc-generator has not run |
| Staff review `governance/reviews/raw-anthropic-economic-index-staff-review.md` | **NO** (only the governance-*pre* review is present) | HIGH — blocking per spec's §Agent Workflow step 12 |
| PII scan (should exist at `governance/pii-scans/`) | **NO** | MEDIUM — likely "no PII found" but must be documented |
| CDE tagging | **NO** | MEDIUM |

**Net:** 10 of the 15 required governance artifacts are missing. The
user task tracker confirms this: @lineage-tracker, @cde-tagger,
@doc-generator, @governance-reviewer-post, @staff-engineer,
@entity-resolver, and @pii-scanner are all listed as
`pending`/`in_progress`. So the pipeline is structurally incomplete
even though the technical core (Bronze, Silver, Gold, DQ, chaos) is
sound.

---

## Risk Register

| # | Risk | Severity | Where it could hide |
|---|---|----|---|
| R1 | EDA numbers fabricated | Critical if true | Ruled out — 11 of 12 headline claims reproduce exactly; one minor fan-out distribution figure (272 vs 265) is off by <3% but does not feed any threshold |
| R2 | DQ scorecard fabricated | Critical if true | Ruled out — the runner is a real 833-line script that materializes actual data, runs actual SQL, and the numbers reproduce under reinvocation |
| R3 | Scorecard stale vs rules JSON | Medium | Found — Bronze scorecard showed 16 rules while rules JSON has 17. My re-run fixed it. Indicates no CI check binds scorecard to rules |
| R4 | "Actual" column in scorecard is violation count, not measured metric | Medium | Confirmed — RAW-AEI-003's "actual=0" gives no insight into the measured SUM(task_pct). A regulator would want the actual SUM recorded |
| R5 | Automation axis miscategorization (learning on wrong side) | Critical if hallucinated | Ruled out — code lines 802-805 align with Anthropic's published v2 methodology; verified by reading the domain-context v2 taxonomy section (lines 1671) and the ingestor's 57 passing tests explicitly assert this split |
| R6 | Global-share invariant not actually preserved under fan-out | Critical if broken | Ruled out — the `pct / n_soc_per_task` split produces SUM≈100 on the Bronze output, verified both by reasoning and by RAW-AEI-003 execution |
| R7 | Silver `observed_exposure_pct` unit confusion (0-1 vs 0-100) | High | EDA flags this explicitly; code keeps observed_exposure_pct in 0-100; automation_pct in 0-100 (multiplied by 100 in Bronze collapse, carried through Silver weighted mean). Spec §Silver schema says `automation_pct` is 0-100; code matches. Verdict: risk surfaced, handled |
| R8 | Chaos manifest fabricated | Critical if true | Ruled out — runner is real, manifest.json contains real error messages from actual exceptions |
| R9 | Missing Bronze/Silver/Gold data contracts (CC-BY license block) | HIGH | Real gap. Spec §Attribution Requirements §"Data Contract License Block" explicitly requires this. Not done |
| R10 | Missing `LICENSE_SOURCES.md` at project root | HIGH | Real gap. This is a CC-BY 4.0 compliance obligation. The governance pre-review flagged it (advisory 2); it is still absent |
| R11 | Missing lineage (Bronze, Silver, Gold) | HIGH | Real gap. Blocks downstream traceability |
| R12 | Missing data dictionary entries for new fields | HIGH | Real gap. Downstream consumers (S4 three-signal composite) will have no canonical definition for `observed_exposure_pct` / `automation_pct` / `anthropic_task_count` / `anthropic_source_release` |
| R13 | Missing PII scan and CDE tagging | MEDIUM | Almost certainly empty, but must be recorded for regulator trail |
| R14 | Missing staff review | HIGH | Blocking per §Agent Workflow |
| R15 | SLV-AOE-015 semantic: reports 0.19% not 1.78% for dropped-none | Low | The rule is tracked, so no gate impact. But its emitted value doesn't mean what the EDA said it would — a governance reviewer would flag the mismatch |
| R16 | SOC coverage target silently lowered from 80% (spec) to 60% (EDA-proposed) | Medium | The EDA recommends revising the Silver P0 threshold, but I could not find a data contract or updated spec capturing the threshold change. If the data contract is never written, this 80%→60% decision is only documented in the EDA and the DQ rule — a regulator would call this out as an undocumented governance decision |

---

## Evidence Demands

| Risk | What I would need to close it |
|---|---|
| R3 | CI check that fails if `governance/dq-scorecards/*.md` rule count differs from the corresponding rules JSON length. |
| R4 | Augment the DQ runner to capture the *measured metric* (e.g. the literal SUM, the literal row count, the literal match %) in the `actual_value` JSON field for SUM/consistency rules, not just the violation count. Publish scorecards with metric values visible. |
| R9 | Create the three data contracts listed in spec §File Changes. The Bronze contract must include the `license: CC-BY-4.0` block shown in the spec. |
| R10 | Create `LICENSE_SOURCES.md` at project root with the spec's verbatim Anthropic block. |
| R11 | Run `@lineage-tracker` and emit three OpenLineage JSONs. |
| R12 | Add entries to `governance/data-dictionary.json` for the 4 new Gold fields and the 10 new Silver fields. |
| R14 | Run `@staff-engineer` and write `governance/reviews/raw-anthropic-economic-index-staff-review.md`. |
| R15 | Either fix SLV-AOE-015's SQL to match the EDA's "volume share dropped" (expected ~1.78), or update the rule description to match its computed semantics (fraction-of-rows, expected ~0.17). |
| R16 | Update the spec §Success Criteria to reflect the approved 60% threshold (currently still says "≥ 80%"), and document the decision in `governance/approvals/`. |

---

## Assessment of Existing Controls

| Control | Grade | Reasoning |
|---|---|---|
| EDA numerical verification (data-analyst) | Strong | 100% of spot-checked headline claims reproduce. Methodology is documented; numbers came from running pandas on the real CSVs |
| DQ rule execution | Strong | Real SQL, real tables, real DuckDB, reproducible runs |
| DQ rule *coverage* | Adequate | 17 Bronze rules cover grain, volume, range, sum invariant, null placeholder, SOC format, provenance. Missing: a rule on the weighted-automation + augmentation + filtered = 1.0 per-SOC post-aggregation invariant (the EDA proves it holds but DQ doesn't re-assert it in Silver) |
| Chaos hardening | Strong | 16 scenarios, real injected corruptions, real captured outputs, verified close of 1 P1 gap (RAW-AEI-019) |
| Code correctness on critical assertions | Strong | Global-share preservation, fan-out, automation split, placeholder handling all correct and tested |
| Governance artifact completeness | **Weak** | 10 of 15 spec-mandated artifacts are missing — data contracts, lineage, data dictionary, LICENSE_SOURCES.md, staff review, PII scan, CDE tags |
| CC-BY 4.0 attribution plumbing | Missing | Spec mandates two places (data contract + LICENSE_SOURCES.md); neither exists |
| Scorecard fidelity | Weak | "Actual" column conflates violation count with measured metric; scorecard drifts from rules JSON without CI guard |

---

## Smoking Guns

1. **`LICENSE_SOURCES.md` does not exist at project root.** The spec
   requires it for CC-BY 4.0 compliance, the pre-implementation
   governance review flagged it as advisory 2, and it is still absent.
   File path (absolute): would be `/Users/jcernauske/code/bright/futureproof-data/LICENSE_SOURCES.md`.
2. **No data contracts for this spec.** `governance/data-contracts/`
   contains no `raw-anthropic-economic-index.yaml`,
   `base-anthropic-observed-exposure.yaml`, or updated
   `consumable-ai-exposure.yaml`. Spec §File Changes lists all three
   as "Create" or "Modify." Absolute check path: `/Users/jcernauske/code/bright/futureproof-data/governance/data-contracts/`.
3. **Published Bronze DQ scorecard was stale** (16/16 vs. 17 rules
   actually defined) until my re-run overwrote it. Absolute paths:
   - Rules JSON (17 rules): `/Users/jcernauske/code/bright/futureproof-data/governance/dq-rules/raw-anthropic-economic-index.json`
   - Scorecard (now 17/17, was 16/16): `/Users/jcernauske/code/bright/futureproof-data/governance/dq-scorecards/raw-anthropic-economic-index-scorecard.md`
4. **Minor EDA inaccuracy** in the §Field Profiles §"Task → SOC
   multiplicity" distribution table: claims 272 tasks with ≥2 SOCs
   and 18,156 with N=1; truth is 265 and 18,163 (and N≥11 is 25 not 31).
   Does not feed any threshold. Absolute path:
   `/Users/jcernauske/code/bright/futureproof-data/governance/eda/raw-anthropic-economic-index-eda.md`
   §Field Profiles §`onet_task_statements`.
5. **SLV-AOE-015 semantic mismatch** — measures 0.19 (fraction of rows
   dropped) but rule description and EDA reference 1.78 (volume share
   dropped). Absolute path: `/Users/jcernauske/code/bright/futureproof-data/governance/dq-rules/silver-anthropic-observed-exposure.json`.
6. **"Actual" column in scorecards reports violation counts, not
   measured metrics.** Makes a regulator unable to eyeball whether the
   computed SUM is near 100 or the actual row count is near 4,082.
   Absolute path: `/Users/jcernauske/code/bright/futureproof-data/governance/dq-scorecards/*-scorecard.md`.

---

## Could Not Verify

- **Iceberg table persistence.** The DQ runner materializes Bronze
  and Silver **in-memory only** — there are no parquet files on disk
  under `data/bronze/iceberg_warehouse/raw/anthropic_economic_index/`
  or `data/silver/iceberg_warehouse/base/anthropic_observed_exposure/`.
  The spec §Zone 1 and §Zone 2 both declare Iceberg tables and
  `@primary-agent` was supposed to materialize them. Open question:
  is the data expected to only live in memory at DQ time and only
  be written to Iceberg by a separate production ingest job, or was
  the persistence step skipped? If the latter, the spec's §Success
  Criteria check "Raw data lands in Iceberg table" is unmet. Needs
  clarification before staff-engineer sign-off.
- **`release_2025_09_15` and newer releases**: the EDA asserts these
  "contain only raw conversation snapshots and lack task_pct_v2.csv."
  I did not exhaustively grep the release directories to confirm. The
  ingestor's release-preference fallback logic suggests the claim is
  accurate, but a human should spot-check before the next Anthropic
  release is auto-adopted.

---

## Verdict

**CONCERNS_FOUND.** The numerical EDA is sound, the pipeline code is
correct on every critical assertion (global-share invariant, fan-out,
automation axis split, placeholder handling), the DQ run is real and
reproducible, and chaos hardening is substantive. **BUT** the spec
lists 15 governance artifacts; only 5 are present. The missing 10
(data contracts, LICENSE_SOURCES.md, lineage, data dictionary entries,
PII scan, CDE tags, staff review) are not optional — they are the
audit trail a regulator would demand before approving a CC-BY-4.0
external-data ingest. Additionally, 3 secondary concerns (stale
scorecard, misleading "actual" column, SLV-AOE-015 semantic mismatch)
should be fixed before the spec is marked complete.

The pipeline is technically trustworthy. The governance wrapper is
not yet complete.

*— End of Audit —*
