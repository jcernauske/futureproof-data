# Staff Engineer Review: onet-experience-requirements (Bronze zone)

**Review Type:** Final quality gate (Bronze zone only)
**Reviewer:** @staff-engineer
**Date:** 2026-04-17
**Verdict:** APPROVED (Bronze zone) — with 2 nits to fix before Silver begins, neither blocking

---

## Executive Verdict

APPROVED. This is the cleanest Bronze zone I've reviewed in this project. The ingestor is a legitimate sixth sibling, not a copy-paste. The test file earns its 49 tests — assertions check specific values, counts, and invariants, not "did it not throw." Real data was observed, EDA numbers match DQ thresholds, and the four adversarial-audit-driven rules each close a probe-demonstrated gap rather than pad the count. The one P1 rule that originally fired on RL=100 rows was diagnosed and scoped correctly. The `_parse_tsv` empty-file guard is placed on the shared base class, and all 442 raw tests still pass, so siblings get the guard for free. The only things keeping this from being a gold-star review are two on-disk hygiene defects (stale DQ scorecard claiming 13/14, and a numerical inconsistency in the spec body about "6th vs 8th subclass") that the next agent should clean up in Silver kick-off. Neither affects the data or the code.

---

## 1. Production Readiness

Examined network behavior, file handling, partial ingest behavior, and O*NET version drift.

**What handles failure gracefully:**

- `_download_and_read` wraps `requests.get` in try/except that falls back to local cache on ANY exception (not just `RequestException`) — broad but defensible: a corrupt socket, a DNS timeout, and a TLS error all land the same place. The `logger.warning` logs the fallback.
- `timeout=300` on the download is appropriately long for a ~60MB ZIP on a cheap link but not infinite — good.
- `allow_redirects=True` — O*NET has historically 301'd from the apex URL, so this is correct.
- `_extract_and_parse` uses `zipfile.ZipFile` inside a context manager. No resource leak.
- `_parse_tsv` now raises `ValueError` on zero rows — closes the chaos-monkey S7 gap (truncated ZIP → silent 0-row success). This fix is on the shared base, so the other five subclasses benefit automatically.
- `flatten()` drops rows with null required fields rather than writing them as nulls. Counter is logged. The EDA-reported 1,127 skipped rows are accounted for.
- Coercion helpers (`_coerce_double`, `_coerce_int`) swallow `ValueError`/`TypeError` and return `None`, which is the right behavior for percent-frequency fields where empty string == missing.

**What could fail in production and isn't fully defended:**

- The User-Agent is hardcoded Chrome 120.0. O*NET does not require UA spoofing today, but if they ever start, this breaks silently (403 → exception → fallback to cache). The fallback at least keeps the pipeline running on stale data, but there is no alert surface; the `logger.warning` could bury it in noise. Recommend: surface "fallback-to-cache" events in the lineage facet or DQ run metadata so a stale-cache ingest is visible.
- `response.content` reads the entire ZIP into memory. At ~60MB this is fine, but if O*NET ever ships a 500MB ZIP the process will OOM on a 1GB container. Not a today-problem; note for future.
- If O*NET adds a 5th scale (e.g., a new training category), rule 003 catches it, but the ingestor will still import it and flatten it correctly. That's the right default: preserve on ingest, reject downstream via DQ.
- `_extract_and_parse` matches filenames with `.endswith(SOURCE_FILENAME)`. If O*NET ever ships a sibling file named `Updated Education, Training, and Experience.txt`, we silently pick the first match in `namelist()` order. Low probability, but the lookup could be tightened to exact match or `os.path.basename` equality.

**Overall:** production-ready. The fallback ladder (network → cache → exception) has no silent-success path post S7 fix.

---

## 2. Testing Depth

49 tests. I actually read the assertions. These are not test theater.

**Real coverage:**

- `test_scale_row_counts_match_fixture` asserts exact counts per scale (RL=4, PT=3, OJ=3, RW=16). Not `> 0` — specific numbers tied to the fixture.
- `test_required_field_flags` asserts the exact `set` of required fields (not a length check, not a substring search).
- `test_field_types` spot-checks concrete Iceberg types (`StringType`, `IntegerType`, `DoubleType`, `TimestampType`, `DateType`) — catches accidental `LongType` drift.
- `test_null_ci_bounds_coerced_to_none` asserts the `lower_ci_bound` and `upper_ci_bound` are `None` for a specific row (49-9071.00) AND that `standard_error == 0.0` is preserved for the same row — distinguishes "empty" from "zero," which is real correctness.
- `test_suppressed_row_retained_when_data_value_present` asserts a specific O*NET-SOC (29-1069.01) with `scale_id == "RW"`, `category == 7`, `data_value == 100.0`. Catches regressions where suppression semantics get reversed (drop vs. flag).
- `test_rw_percentages_sum_roughly_to_100_per_occupation` asserts `99.0 <= total <= 101.0` per SOC. Real-data tolerance (observed max |dev| 0.03) → 1.0 in the test is generous but allows small synthetic fixture variance.
- `test_skips_rows_with_null_required_fields` uses a hand-built 3-row input with two must-skip rows and one keeper, then asserts `len == 1` AND `flat[0]["onet_soc_code"] == "15-1252.00"`. Golden.

**Weaker spots (non-blocking):**

- `test_ceo_rw_distribution_skews_senior` uses `high_exp_weight > 50.0`. That's a "greater than" — a more-nitpicky review would pin the exact fixture value. But given the EDA-documented 68.24% at cat 11 for CEOs, this threshold is defensible.
- `TestRegistration.test_registered_in_rebuild_all` uses a substring search for `"OnetExperienceIngestor"` and `"onet_experience"` in `scripts/rebuild_all.py`. Works today, but brittle — if the runner refactors to load classes dynamically from a manifest, this test would need updating. Acceptable for now.
- No test exercises the actual network `fetch()` path (the `_download_and_read` → ZIP → extract → parse flow). All tests go through the `cache_dir` parameter. Consequence: the extract-from-ZIP logic (`_extract_and_parse`) has no direct unit test in this file; it is tested implicitly by the sibling `test_onet_ingestor.py` via the same shared base. Fine.

**Fixture realism:** The 27-row sample TSV carries representative rows for 11-1011.00 (CEO, senior), 15-1252.00 (Software Dev, mid), 41-2031.00 (Retail, entry), 29-1069.01 (suppressed single-category 100% case), 49-9071.00 (null CI bounds). Covers all four scales and the spec's edge-case matrix. This fixture was clearly constructed, not scraped — good.

**Spot check: tests pass.** `uv run pytest tests/raw/test_onet_experience_ingestor.py -v` → 49/49 pass in 0.60s. `uv run pytest tests/raw/` → 442/442 pass in 3.05s. No deselection of new tests, no warnings.

---

## 3. Security / Correctness

Read the ingestor + the DQ SQL + the downloadable artifacts path. No red flags.

- **SQL injection:** DQ rules are written as static SQL in a JSON file, executed by a first-party script. No user input flows into any WHERE/GROUP BY. N/A.
- **Path traversal:** `_read_from_cache` takes `cache_dir: Path` from the caller (either the hardcoded `CACHE_DIR` class constant or a test-supplied path). `rglob(SOURCE_FILENAME)` would resolve symlinks, but this is our cache directory — not user-supplied. Tests pass `str(SAMPLES_DIR)` which is repo-local. Acceptable.
- **Zip slip:** `_extract_and_parse` does NOT extract to the filesystem; it calls `zf.read(target)` and parses in memory. Zip slip is impossible here.
- **TOCTOU:** `_read_from_cache` does `if not path.exists()` then reads. If the cache file disappears between the check and the read, `read_bytes()` raises `FileNotFoundError` which propagates — correct behavior. Not a race that needs defense.
- **Resource leaks:** `zipfile.ZipFile(io.BytesIO(...))` is in a `with` block. `response` from `requests.get` is not explicitly closed, but we're done with it after `.content` is read and it gets GC'd. Not a leak.
- **Error suppression:** The broad `except Exception` in `_download_and_read` is the one place I'd normally complain, but it's logged AND the fallback path raises `FileNotFoundError` cleanly if the cache is missing — so the "silent success" path that would be dangerous here is closed. The zero-row guard in `_parse_tsv` closes the other silent-success path.
- **Type safety:** `flatten()` uses `any(v is None for v in (...))` to reject incomplete rows. Short, correct, no clever abstractions.

**One nitpicky concern — not a blocker:** `_coerce_int("Y")` returns `None` via the `ValueError` path, but `_coerce_string("Y")` returns `"Y"`. If someone swaps the coercion helper on `recommend_suppress` (e.g., in a future refactor "make everything typed"), the "Y"/"N" flag gets silently null'd. The spec explicitly calls this out ("preserve `recommend_suppress` flag for DQ") and the test `test_recommend_suppress_preserved_verbatim` catches it, so we're defended. Good.

---

## 4. Architectural Consistency

Six subclasses. Real reuse, not copy-paste.

- `OnetBaseIngestor` owns ZIP download, cache fallback, TSV parsing, BOM stripping, and the four coercion helpers.
- Each subclass is 60-100 lines, just `SOURCE_FILENAME`, `flatten()`, and `get_schema()`.
- `OnetExperienceIngestor.flatten()` uses the inherited `_coerce_onet_soc`, `_coerce_string`, `_coerce_int`, `_coerce_double` consistently. No custom re-implementations.
- The empty-file guard in `_parse_tsv` is a base-class change that applies uniformly to all six subclasses. The adversarial auditor confirmed no sibling has a legitimate empty-file use case, and the full test suite still passes. This is the correct architectural choice — the alternative (adding a per-subclass guard five more times) would be the copy-paste smell.

**One architectural nit:** `OnetWorkActivitiesIngestor.flatten()` and `OnetWorkContextIngestor.flatten()` are nearly identical — same 13-field dict, same coercion logic, with only a `category` field added to Work Context. That's one level of duplication already present pre-Experience spec. Not a blocker for Bronze and not this spec's problem, but if a 7th sibling with the same shape ever shows up, a shared `_flatten_scale_row` helper in the base would earn its keep. Note for future.

---

## 5. Spec Fidelity (Spot-Check of 3 Sections)

### Raw Schema (17 fields): MATCH

Verified `OnetExperienceIngestor.get_schema()` field-by-field against the spec table (lines 91-110). 17 fields, correct names, correct types (StringType / IntegerType / DoubleType / TimestampType / DateType), correct required-ness. The `test_required_field_flags` test asserts the exact required set and passes.

### Test Matrix (Weighted Median Edge Cases): PARTIAL

The spec's §Test Matrix (lines 446-456) lists 7 cases. Let me walk through what Bronze actually defends:

| Case | Bronze Defense | Status |
|------|----------------|--------|
| Empty distribution | `_parse_tsv` raises on 0 rows + `flatten()` drops per-row null required fields | Defended at ingest, not at a "distribution" level — correct for Bronze (grain is row-level, not occupation-level) |
| Single category 100% | `test_suppressed_row_retained_when_data_value_present` asserts fixture row `(29-1069.01, RW, cat=7, data_value=100.0)` lands. | Defended |
| All suppressed | EDA confirms zero RW occupations have all rows suppressed, so this is synthetic-only. No Bronze test directly simulates it, but `test_recommend_suppress_preserved_verbatim` and the DQ rule 013 (Y rate < 5%) cover the field-level concern. | Deferred to Silver (correct — Bronze doesn't filter on `recommend_suppress`) |
| Tie at 50% | Silver concern — Bronze doesn't compute medians | N/A at Bronze |
| Multi-detail aggregation | Silver concern | N/A at Bronze |
| Missing source experience | Gold concern | N/A at Bronze |
| Known-value spot checks | `test_ceo_rw_distribution_skews_senior` + `test_retail_rw_distribution_skews_entry` | Defended at fixture level |

Spec fidelity: what Bronze is responsible for (rows land, fields coerce, grain is unique, suppress preserved verbatim) is defended. What the spec matrix defers to Silver/Gold is correctly deferred. No gaps.

### CDE & PII Assessment: MATCH

Walked the spec table (lines 419-438) against the data contract `governance/data-contracts/raw-onet-experience.yaml` (via the post-review's row-by-row verification). 3 CDE flags (`onet_soc_code`, `element_id`, `scale_id`), 0 PII flags across 17 columns. Matches spec exactly. PII scan independently verified NO PII — consistent.

---

## 6. Remaining Risk (Single Most Likely Production Failure)

**The single most likely way this breaks: O*NET version drift silently invalidating `element_id` → `scale_id` bindings.**

Today, `(RL, 2.D.1), (RW, 3.A.1), (PT, 3.A.2), (OJ, 3.A.3)` is a 1:1 invariant, and rule 011 (P0) enforces it. Silver's filter is `scale_id = 'RW' AND element_id = '3.A.1'`. If O*NET ever re-indexes their Content Model (they have done major re-indexings in the past — the 15.x → 20.x transition renumbered several element IDs), the Bronze ingest would land clean rows, DQ rule 011 would fire P0, and the Bronze gate would block — correct behavior. But the operator's response to "rule 011 failed with 9,658 violations" would have to be: update the rule OR update the Silver filter. That's a human decision that can't be automated.

**Why this is the top risk:**
- It's not defended by the ingestor (element_id is preserved verbatim).
- It's caught by rule 011, which is good, but the remediation requires understanding the O*NET Content Model, not just fixing the pipeline.
- The timeframe of concern is any O*NET major release — historically quarterly, irregularly including Content Model changes.
- If the ingestor is re-run in auto-pilot (e.g., quarterly cron) without human review of the DQ result, the pipeline correctly halts at the gate — but the cron operator needs to know what to do.

**Runners-up:**

1. **Fallback-to-cache masking a stale ingest.** If O*NET's download endpoint 403s for 6 months while the cache holds version 29.x data, the pipeline keeps producing Bronze rows with stale `ingested_at` timestamps but the same 35,998 rows. DQ doesn't catch this. Recommend: add a rule that `load_date` and `source_url`'s embedded version (`db_30_2`) must be consistent with a tracked "current O*NET version" value in a small config file, OR surface the fallback in the lineage run facet.

2. **A row with a valid `data_value` but a `category` outside the per-scale canonical range.** Rule 012 catches this (per-scale ENUM), added post-adversarial-audit. Before rule 012, this was undefended. Now defended.

3. **A complete-but-wrong occupation coverage shift.** If O*NET re-runs their survey and suddenly 400 occupations have ETE data instead of 878, rule 009 fires (800-1,100 bound), Bronze halts. Defended.

Document the top risk in the Silver spec so the transformer agent knows what to do when rule 011 trips.

---

## Issues Found

| # | Severity | File / Artifact | Issue | Required Fix |
|---|----------|-----------------|-------|--------------|
| 1 | ADVISORY (non-blocking) | `governance/dq-scorecards/bronze-onet-experience.md` | Scorecard reports 13/14 (run_id `9690335b`) from the pre-fix rule-014 run, but the latest DQ result file `raw-onet-experience-20260417-014651.json` shows 14/14 PASS after rule 014 was correctly scoped to `WHERE scale_id = 'RW'`. The scorecard was not regenerated. | Regenerate the scorecard against the 014651 run before Silver begins. P0 gate decision is unchanged (both runs pass all P0 rules). |
| 2 | ADVISORY (non-blocking) | `docs/specs/onet-experience-requirements.md` | Line 80 says "the 6th subclass (there are 5 existing concrete subclasses)", which matches reality. But lines 366, 600, 710, 759 (all in the Revision Response and Review appendices) say "8th subclass". The spec is internally inconsistent about the subclass count. Module docstring correctly says "Six thin subclasses." Code is correct. Just documentation drift from the pre-review blocker #8's original wording. | Normalize all spec references to "6th" in the next spec revision. Not blocking. |
| 3 | NOTE (non-action) | `OnetBaseIngestor._download_and_read` | Broad `except Exception` falls back to cache silently. Correct behavior but no alerting surface for "we're running on stale cache because the network failed." | Consider surfacing fallback-to-cache as a lineage run-facet event in a future enhancement. Not a blocker for Bronze. |

No blockers. No CHANGES REQUESTED. No REJECT.

---

## What's Acceptable

Fine. The 49 tests earn their keep — real assertions, real edge cases, real values. The `_parse_tsv` guard is correctly placed on the base. The four post-adversarial-audit DQ rules are well-reasoned and each trace to a probe ID, not CYA padding. NULL-propagating delta in the Gold spec (not this Bronze gate, but setup for it) is the right call. Rule 014's scope bug was caught and fixed within the DQ engineer's own scorecard observation section before Silver even started, which is how the tight feedback loop is supposed to work.

The one thing I'll grudgingly acknowledge is the adversarial auditor's work. The 10-rule baseline passed the chaos monkey cleanly, and a lesser review would have stopped there. The auditor ran 15 independent probes and surfaced five gaps — four of which became rules 011-014 with evidence-backed thresholds. That's the level of skepticism this pipeline actually needs.

---

## Blockers for Silver / Gold / MCP

None that block Silver from starting. The residual items from the governance post-review carry forward cleanly:

1. **Regenerate Bronze DQ scorecard** against the 14/14 run (Issue #1 above). Not a gate, but the on-disk artifact should reflect current state.
2. **PyIceberg catalog registration** for `bronze.onet_experience` — currently `catalog.load_table` does not resolve; DQ and tests read parquet directly. Silver transformers will need the catalog entry. Track in Silver kickoff.
3. **Document the O*NET-version-drift risk** (top risk above) in the Silver spec, specifically how to respond when rule 011 fires.
4. **Retail-salesperson weighted-median caveat** — EDA confirms `41-2031.00` has bimodal RW with weighted median at category 5 (0.75 yr), not cat 1-3. Spec §Zone 2 line 184 already documents this and warns against writing `median_category <= 3 for entry` rules. Silver DQ writer must honor that.

---

**Final verdict:** APPROVED (Bronze zone). Proceed to Silver.

*— @staff-engineer, 2026-04-17*
