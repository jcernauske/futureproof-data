# Adversarial Audit: raw-ingest-college-scorecard-institution

**Audit Date:** 2026-04-14
**Auditor:** @adversarial-auditor (independent)
**Spec:** `docs/specs/raw-ingest-college-scorecard-institution.md`
**Status:** READY-WITH-CAVEATS (no CRITICAL blockers, several MODERATE findings)

---

## TL;DR

The artifacts are substantially sound. The ingestor code is correct, the DQ SQL queries behave as advertised, and the 41 tests pass. The chaos-monkey's 4 coverage gaps (freshness, referential integrity, accuracy, consistency) are REAL, not hallucinated — I verified against the chaos runner source. However I found several **evidence-integrity issues** that would not satisfy a skeptical regulator:

1. Source URL provenance is split — the scorecard references a URL the ingestor does not use (`scorecard.network` ZIP vs `app.cloud.gov` CSV).
2. The DQ scorecard numbers for quintile inversions (private: 39) contradict the EDA (private: 34) by 5 — unexplained.
3. DQ rules were executed against in-memory reconstructed data, not a real Iceberg table; the Iceberg table does not exist yet.
4. Evidence for DQ thresholds cites a single EDA session file with no reproducible script.
5. Two untested code paths in the ingestor (ZIP extraction, BOM strip, HTTP download) mean 3 defensive branches have never fired.
6. Chaos manifest misstates two rule thresholds (says ">=80%" for rules that are >=75% and >=65%).

---

## 1. Risk Register

### HR-1 — CRITICAL None found
No CRITICAL blockers. The ingest code, DQ SQL, and test suite appear correct at the level of evidence available.

### HR-2 — MODERATE: Source URL provenance mismatch
The DQ scorecard declares the data source as:

> Download URL: `https://ed-public-download.scorecard.network/downloads/Most-Recent-Cohorts-Institution_04172025.zip`

But the ingestor downloads from:

```python
DOWNLOAD_URL = "https://ed-public-download.app.cloud.gov/downloads/Most-Recent-Cohorts-Institution.csv"
```

Two different hosts (`scorecard.network` vs `app.cloud.gov`), two different formats (`.zip` vs `.csv`), two different filenames (dated 04172025 vs undated "Most-Recent"). The EDA file date is 2026-04-15 and describes "as of March 2025 file date" — suggesting someone pulled a ZIP from `scorecard.network` for EDA but the ingestor will pull a different CSV from `app.cloud.gov` in production. **A regulator would ask: did we profile the data we are actually ingesting, or a different snapshot?**

**Severity:** MODERATE — not a code bug, but a documentation/evidence integrity gap. Both are official DoE hosts and likely serve identical data, but that has not been verified.

### HR-3 — MODERATE: DQ scorecard numbers contradict EDA
Quintile inversion counts diverge between the EDA (2026-04-15) and DQ scorecard (2026-04-16):

| Metric | EDA says | Scorecard says | Delta |
|--------|----------|----------------|-------|
| Q1 > Q5 inversions, private | 34 of 1,073 (3.2%) | 39 of ~1,073 (3.6%) | +5 |
| Q1 > Q5 inversions, total | 41 | 46 | +5 |

Both documents claim to be run against the same data. Either:
- The data changed between 2026-04-15 and 2026-04-16 (undocumented refresh), OR
- One of the counts is wrong, OR
- The filter criteria differ between EDA and DQ execution

RAW-CSI-013 threshold is `<= 50`. At 46 (per scorecard), the rule is passing by 4 violations — close to the threshold. If the true number is materially different, the threshold may be mis-sized. **No one noticed the 5-violation discrepancy.** This is exactly the kind of number that looks "close enough" and slips through.

### HR-4 — MODERATE: DQ was executed on in-memory filtered data, not the target Iceberg table
The scorecard states:

> The Iceberg table does not yet exist. DQ rules were executed against data processed through the ingestor's filter and coercion logic ... loaded into an in-memory DuckDB instance.

This means the "13/13 PASS" does not prove the rules work against the Iceberg table they are named for. In particular:

- Type-round-tripping through PyIceberg → Parquet → DuckDB has not been tested.
- Null handling after Iceberg write (e.g., how DuckDB reads `DoubleType` with nulls) has not been tested.
- `ingested_at`, `source_url`, `source_method`, `load_date` metadata fields are not populated in the in-memory table — they are framework-populated. No rule references them, but no rule can validate them either.

**A regulator would say:** "Show me a DQ run against the production table." Today, no such run exists. The rules and scorecard are predictive, not observational.

### HR-5 — MODERATE: Chaos manifest misstates two rule thresholds
The chaos manifest (rule performance matrix) labels:
- RAW-CSI-011 as "control=1 pub price >=80%" — actual rule threshold is **75%**
- RAW-CSI-012 as "control=2 priv price >=80%" — actual rule threshold is **65%**

The author conflated the original spec thresholds with the final EDA-corrected thresholds. This is a documentation defect only — the chaos runner uses the rules themselves (which have the corrected thresholds) — but a human reading the matrix would misunderstand what the tests asserted.

### HR-6 — MODERATE: GAP-1 (RAW-CSI-012 never fires) — chaos-monkey finding confirmed
The chaos-monkey claims RAW-CSI-012 never fired across 5 cycles. I verified this against the chaos runner source (`raw_ingest_college_scorecard_institution_chaos_runner.py` lines 658-668):

```python
# Strategy 3: Remove net price for control-specific checks
# Null out npt4_pub for public schools to break the coverage rule
public_rows = [i for i in range(len(rows)) if rows[i].get("control") == 1]
n_null_pub = int(len(public_rows) * 0.30)
for i in rng.sample(public_rows, min(n_null_pub, len(public_rows))):
    ...
    rows[i]["npt4_pub"] = None
```

Confirmed: the coverage corruption nulls `npt4_pub` for `control=1` ONLY. There is no symmetric code path that nulls `npt4_priv` for `control=2`. So RAW-CSI-012 cannot fire in chaos. This is a REAL gap in the corruption strategy, not in the rule itself. The rule's SQL is correct and will fire against real coverage drops.

**Note:** The rule has been validated on real data (passing at 70.6% vs 65% threshold). But it has never been **adversarially tested**.

### HR-7 — MODERATE: EDA findings are not reproducible
The DQ rule evidence field repeatedly cites `docs/sessions/eda-college-scorecard-institution.md` as the source of every threshold. I read that file — it is a hand-written markdown report of a presumed pandas analysis run by `@data-analyst`. **There is no EDA script checked into the repo.** I cannot:
- Re-run the EDA against new data
- Verify the min/max/coverage numbers
- Validate the Q1 > Q5 inversion count

Every threshold ultimately traces to numbers that were produced once, in one session, and have only the EDA markdown as their witness. If a regulator asked "what SQL did you run to get 73.5% COA coverage?", we cannot produce it. The fact that the DQ scorecard stats (3,039 rows, 867 public, etc.) exactly match the EDA is circumstantial — we cannot independently verify either.

### HR-8 — LOW: Three defensive code paths are untested
The ingestor has three code paths that the test suite never exercises:

1. `_download_and_read()` — real HTTP fetch (no mocked tests).
2. `_is_zip()` / `_extract_csv_from_zip()` — never called in tests; sample CSV is plain.
3. BOM stripping (`content.startswith(b"\xef\xbb\xbf")`) — untested.

If the real source starts returning a ZIP (which happens — the DQ scorecard URL is a ZIP), or if the CSV acquires a BOM, the behavior is unverified. These are defensive paths; they will almost certainly work, but a regulator reviewing coverage would note the gap.

### HR-9 — LOW: 1 of 41 tests is near-trivial
`test_fetch_returns_same_data_for_all_entities` asserts that `result["a"] == result["b"]`. This is tautological given `fetch()` returns the same list by reference for every entity key — it tests the framework's keying, not the ingestor logic. Not a false test, but low value. Everything else is substantive.

### HR-10 — LOW: Schema field IDs are fresh and do not conflict
I verified via grep across all ingestors: field IDs 1-28 in the new `raw.college_scorecard_institution` are internal to that Iceberg schema and do not collide with sibling tables. Iceberg field IDs are table-scoped, so conflict would only matter within the same table. No issue.

### HR-11 — LOW: Rule `status` field is inconsistent
In `governance/dq-rules/raw-ingest-college-scorecard-institution.json`, 6 rules have `status: "approved"` and 7 have `status: "active"`. All have `approved_by: "human"` with timestamps. The dual nomenclature has no operational consequence but suggests a schema drift in how governance tooling tags rules. Cosmetic.

### HR-12 — LOW: EDA recommended tighter bound than rule uses for NPT4_PUB
EDA §"Spec DQ Rule Adjustments Recommended" #3 says:

> **npt4_pub range:** Change from "$0-$60,000" to "-$5,000-$35,000" (actual: -$1,180 to $32,598)

But RAW-CSI-006 uses `-5000 OR npt4_pub > 60000` — i.e., the upper bound stayed at $60,000, not $35,000 as the EDA recommended. The rule is more permissive than the EDA suggested, so it will not flag unusual public net prices in the $35K-$60K range. Given the observed max is $32,598, anything above $35K would be noteworthy. This is a defensible choice (more headroom for future drift) but the EDA's narrower recommendation was silently overridden with no justification in the evidence field. A regulator would ask: "Who decided to keep $60K?"

---

## 2. Independent Verification of Chaos-Monkey's 4 Coverage Gaps

The chaos-monkey identified 4 DQ dimensions not covered by any rule. I verified each claim:

| # | Claimed Gap | Independent Verification | Verdict |
|---|-------------|--------------------------|---------|
| 1 | No freshness rule on `load_date` / `ingested_at` | Grepped all 13 rules. No rule references `load_date`, `ingested_at`, or any date field. | CONFIRMED |
| 2 | No referential integrity rule on `unitid` | Grepped all 13 rules. No rule bounds `unitid` range or cross-checks against the FoS UNITID set. | CONFIRMED |
| 3 | No accuracy rule for swapped in/out-state tuition or pub/priv net price | Grepped. No rule compares `tuitionfee_in` vs `tuitionfee_out`. No rule enforces `npt4_pub IS NULL WHERE control != 1`. | CONFIRMED |
| 4 | No consistency rule for `costt4_a >= tuitionfee_in` | Grepped. No cross-field rule on COA components. | CONFIRMED |

**All 4 gaps are real. The chaos-monkey did not hallucinate.**

The recommended 5 new rules (RAW-CSI-014 through RAW-CSI-018) address these gaps sensibly. My only note: **RAW-CSI-018 (net_price <= cost_of_attendance)** partially overlaps with a Silver-zone rule already in the spec ("net_price_annual <= cost_of_attendance_annual" is a Silver DQ rule). Adding it at Bronze would be additional defense in depth and is fine.

---

## 3. Additional Governance Gaps I Found

### AGG-1: No EDA script in repo
All statistical claims trace to `docs/sessions/eda-college-scorecard-institution.md` with no accompanying Python script or notebook. The EDA output cannot be reproduced or audited. **Recommendation:** Check in an EDA script (even a simple pandas one-liner module) that produces the numbers the markdown cites.

### AGG-2: Sample CSV has edge cases but not ZIP/BOM cases
`tests/raw/college_scorecard_institution_sample.csv` covers PS, NULL, NA, empty UNITID, and PREDDEG/ICLEVEL filter. It does not cover a zipped CSV, a BOM-prefixed CSV, or a CSV with changed column order. **Recommendation:** Add 1-2 adversarial sample CSVs and a test that exercises the ZIP path.

### AGG-3: No test that the Iceberg schema round-trips via PyIceberg
The `get_schema()` test only asserts field presence. It does not write-then-read a real Iceberg table. **Recommendation:** Add a single integration test that creates the table via `BaseIngestor.ingest()` in a temp warehouse and reads back a row.

### AGG-4: Conditional agent decisions are documented but not machine-verifiable
PII scan, temporal model, entity resolution assessments all declare "SKIP" with markdown justification. There is no code enforcing that `raw.college_scorecard_institution` was classified Level 1, no automated test that the PII scanner actually saw all 24 fields. These are human-verified only. For Bronze public-data sources this is defensible; for future regulated sources a machine-checkable policy is warranted.

### AGG-5: Silver/Gold zone DQ rules do not yet exist
The spec defines 8 Silver DQ rules and 3 Gold DQ rules (lines 210-218, 252-255). None are written. The audit scope was Bronze, but a regulator reviewing the full pipeline would note this before approving the Gold join.

### AGG-6: `ICLEVEL` column is read for filter but not stored
The ingestor reads `ICLEVEL` to filter rows but does not persist it. This means downstream consumers cannot distinguish "passed filter because PREDDEG=3" from "passed filter because ICLEVEL=1 (4-year but not bachelor's-predominant)". The EDA shows these are materially different populations (PREDDEG=4 graduate-dominant institutions were captured via ICLEVEL=1 and have 26.5% missing COA — precisely the population dragging coverage below 90%). Consider persisting `iclevel` for downstream transparency.

---

## 4. Evidence Demands (What Would Satisfy Me)

| Risk | Evidence I'd Accept |
|------|---------------------|
| HR-2 (URL split) | Single line in domain context or scorecard confirming that `scorecard.network/...04172025.zip` and `app.cloud.gov/.../Institution.csv` serve byte-identical CSV payloads. Ideally a checksum. |
| HR-3 (39 vs 34 inversions) | Rerun the Q1>Q5 count with the current data and reconcile. Update either EDA or scorecard with a note. |
| HR-4 (no Iceberg run) | Create the Iceberg table, re-run the 13 rules against it, re-publish the scorecard. |
| HR-5 (chaos threshold mislabel) | Fix the two matrix labels to say >=75% and >=65%. One edit. |
| HR-6 (RAW-CSI-012 never fires) | Add a private-coverage null-out to the chaos runner; rerun; verify RAW-CSI-012 fires >=3/5 cycles. |
| HR-7 (EDA not reproducible) | Check in `scripts/eda_college_scorecard_institution.py` that regenerates the numbers in the EDA markdown. |
| HR-8 (untested paths) | Three tests: mocked HTTP, ZIP input, BOM input. ~30 lines. |
| HR-12 (NPT4_PUB upper) | One sentence in the rule evidence explaining why $60K was kept rather than $35K (answer is likely "headroom" — just say so). |

---

## 5. Assessment of Existing Controls

| Risk | Existing Control | Grade |
|------|------------------|-------|
| Schema correctness | 7 schema tests + 1 field-count assertion | **Strong** |
| PrivacySuppressed handling | 3 tests (PS, NA, NULL) + explicit sentinel test | **Strong** |
| Null grain rejection | Dedicated test + logged warning | **Adequate** |
| Dedup correctness | Dedicated test + framework-level enforcement | **Strong** |
| Filter logic (PREDDEG/ICLEVEL) | 3 positive + 1 negative test | **Adequate** |
| Type coercion | 5 tests (int, float, invalid) | **Adequate** |
| DQ rule SQL correctness | Rules executed against real filtered data, PASS verified | **Adequate** (but see HR-4) |
| Chaos-monkey adversarial testing | 5 cycles, 10/13 rules confirmed firing | **Adequate** (with HR-6 caveat) |
| URL / provenance | Declared but not verified | **Weak** (see HR-2) |
| HTTP download path | Implemented, untested | **Weak** (see HR-8) |
| ZIP/BOM handling | Implemented, untested | **Weak** (see HR-8) |
| Iceberg round-trip | Schema declared, not integration-tested | **Weak** (see AGG-3) |
| EDA reproducibility | Markdown only, no script | **Missing** (see HR-7) |
| PII / entity-res / temporal assessments | Thorough markdown reports | **Adequate** |

---

## 6. Recommendations (Priority-Ordered)

### MUST-FIX before staff-engineer sign-off
None. No CRITICAL risks.

### SHOULD-FIX before staff-engineer sign-off
1. **Reconcile source URL** (HR-2): add one paragraph to the scorecard or domain context stating that the two URLs serve the same payload, ideally with a checksum.
2. **Reconcile Q1>Q5 count** (HR-3): rerun the count and pick one number. A 5-unit drift in a rule that passes by a margin of 4 is a yellow flag.
3. **Fix chaos manifest rule labels** (HR-5): trivial text edit.
4. **Fix chaos corruption to target private coverage** (HR-6): 10 lines of additions to `corrupt_coverage()`.
5. **Add EDA script to repo** (HR-7): the single biggest regulator-facing improvement.
6. **Implement the 5 chaos-monkey-recommended rules** (RAW-CSI-014 through RAW-CSI-018): they address real coverage gaps.

### NICE-TO-HAVE
7. Add tests for ZIP / BOM / HTTP paths (HR-8).
8. Add `iclevel` column to the Bronze schema for provenance (AGG-6).
9. Document the NPT4_PUB $60K upper-bound rationale in the rule evidence (HR-12).
10. Add an Iceberg round-trip integration test (AGG-3).

---

## 7. Final Verdict

The chaos-monkey's 4 coverage gaps and 5 rule recommendations are all legitimate and should be implemented. The ingestor code is sound. The DQ SQL is correct. The 41 tests pass and are mostly substantive.

However, **the evidence chain has small cracks** — a URL mismatch, a 5-unit numeric discrepancy, a missing EDA script, two untested code paths, one mis-labeled chaos matrix row. No single crack is fatal, but a regulator reviewing the full chain of custody would find reasons to push back. The recommendations above close all of them with a few hours of work.

**Would a regulator accept this as-is?** Probably not — they would ask for the URL reconciliation, the EDA script, and the chaos gap closure before signing. **Would a regulator accept this after the SHOULD-FIX items?** Yes.

**Recommendation:** APPROVE with the SHOULD-FIX items scheduled before staff-engineer final review.

---

*— End of Adversarial Audit —*
