# Adversarial Audit: raw-ingest-bls-oews + silver-base-bls-oews DQ Rule Set

**Spec:** `docs/specs/ingest-bls-oews-wage-percentiles.md`
**Bronze table:** `bronze.bls_oews` (831 rows, May 2024 OEWS National)
**Silver table:** `base.bls_oews` (declarative — not yet materialized)
**Date:** 2026-05-06
**Auditor:** @adversarial-auditor
**Inputs reviewed:**
- `governance/chaos-manifests/raw-ingest-bls-oews-chaos.yaml`
- `governance/dq-scorecards/raw-ingest-bls-oews-chaos-report.md`
- `governance/dq-rules/raw-ingest-bls-oews.json` (12 rules: -001..-012)
- `governance/dq-rules/silver-base-bls-oews.json` (12 rules: SLV-OEWS-001..-012)
- `governance/eda/raw-bls-oews-eda.md`
- `src/raw/bls_oews_ingestor.py` (parser semantics — `_coerce_*`, `_parse_wage`)

---

## Verdict

**GAPS_FOUND.** 9 governance gaps remain after the post-chaos rule additions. The 12 Bronze + 12 Silver rules close the chaos-monkey-discovered negative-wage attack (S10 -> RAW/SLV-OEWS-011/012), but **chaos-monkey only probed 10 attack surfaces drawn from the spec's own DQ list**. It did not probe (a) `total_employment` — the second numeric column in the table, never validated; (b) absurdly-large wage values; (c) `wage_hourly_median` corruption; (d) cross-row group-vs-detailed wage consistency (an OEWS publication never ingested into this table, but the EDA confirms only "detailed" rows arrive — there is no rule that `OCC_GROUP` filtering actually held); (e) unicode/encoding anomalies in `occupation_title`; (f) source-vintage drift signals (May 2024 -> May 2025); (g) `wage_annual_mean` non-negativity (covered) vs. `wage_annual_mean` upper-bound sanity (not covered, and the EDA documents real means as high as $432,490 — there is no ceiling at all); (h) `ingested_at`/`load_date` freshness; (i) the OOH-OEWS join orphan check defined for Gold but never enforced at Bronze/Silver. None of (a)-(i) is structurally caught by the current 24-rule total. The most critical, **G1 (`total_employment` non-negativity)**, is the exact mirror of the negative-wage gap that chaos-monkey *did* find — and would have surfaced under any negative-numeric-fuzzing pass that wasn't column-scoped to wages.

| Metric | Value |
|---|---|
| **Verdict** | **GAPS_FOUND** |
| Gaps identified | **9** (G1-G9) |
| **P0 gaps** | **3** (G1, G2, G3) |
| P1 gaps | 4 (G4, G5, G6, G7) |
| P2 gaps | 2 (G8, G9) |
| Recommend rule additions | 6 (G1, G2, G3, G4, G5, G6) |
| Out-of-scope-for-this-spec | 3 (G7, G8, G9 — defer to follow-up specs) |
| Rule set state if all P0 gaps closed | 12 + 3 = 15 Bronze rules; 12 + 3 = 15 Silver rules |

### One-paragraph summary

The chaos-monkey run was disciplined and information-barrier-clean, but it ran a **closed-world** test: every scenario except S10 was a direct corruption of a field that *already had a P0 rule pointed at it*. S10 (negative wage) was the first scenario that targeted an invariant **not in the spec**, and it caught a real gap. The lesson is that S10 is one example of a class — "domain invariants the AI inferred from the spec but never wrote down" — and the audit shows at least 3 more P0 holes in that class. Most pressingly: `total_employment` is a `LongType()` field with **zero rules** today (no non-negativity, no upper bound, no null-rate floor), even though the EDA established a 100% non-null rate and a 3.28M maximum. A row reporting `total_employment = -1` or `total_employment = 999_999_999` would survive the entire Bronze + Silver gate. The same negative-wage-attack chaos pattern, re-pointed at `total_employment`, would currently produce a `GAP_UNCAUGHT` verdict identical to S10's. The system is harder than it was 24 hours ago, but it is not yet hardened. Three more rules (G1, G2, G3) and a re-run of chaos-monkey with negative-numeric fuzzing extended to **every numeric column** would close the structural gap.

---

## 1. Risk Register

### G1 — `total_employment` has NO non-negativity, NO upper-bound, and NO null-rate rule [P0]

**Severity:** **P0 — CRITICAL.** Same class as the negative-wage gap chaos-monkey closed.

**Detail:** `total_employment` is the second numeric payload in the table (column 3 in the schema, `LongType()`, optional per spec but 100% non-null in the actual May 2024 vintage per EDA §Field Profiles). The 12-rule Bronze set and the 12-rule Silver set contain **zero rules** referencing `total_employment`. The ingestor's `_coerce_employment()` method (lines 401-424 of `src/raw/bls_oews_ingestor.py`) accepts:
- `*` -> null (correct)
- A signed string with commas like `"-1,234"` -> `-1234` (negative survives — the function does `int(round(float(s)))` with no sign check)
- A floating-point cell from openpyxl -> `int(round(float(value)))` (negative or absurd values pass)
- The string `"abc"` -> null (caught by `ValueError`)

So a corrupted source cell with a negative integer or a value in the billions would be silently coerced and persisted, and **nothing in the rule set would flag it**. The chaos-monkey manifest never targeted `total_employment` — there is no scenario `Sn` for it. The EDA recommended a P1 sanity rule (`total_employment >= 0`) on line 61 ("Consider P1 sanity rule `total_employment >= 0` if not already present") and it was **not added** to either rule file.

**Why this is the same class as S10:** The negative-wage attack (S10) exposed that monotonicity is a relational invariant, not a value invariant — a uniform negative shift preserves `p10 <= p25 <= ... <= p90`. The negative-employment attack would have the same structural signature: no relational invariant constrains it (employment is a single column, no monotonicity to break), and no value invariant exists.

**Recommended fix:** Add `RAW-OEWS-013` (P0, Validity) and `SLV-OEWS-013` (P0, Validity) — `total_employment IS NULL OR total_employment >= 0`. Optionally add an upper-bound sanity rule (e.g. `<= 10_000_000` — the largest US occupation today is Retail Salespersons at ~3.6M; 10M is a 2.7x headroom that catches order-of-magnitude parser bugs).

---

### G2 — No upper-bound sanity on annual wages (negative-wage's twin) [P0]

**Severity:** **P0.** RAW-OEWS-011 closes the negative half of the value-domain gap; the positive half is open.

**Detail:** RAW-OEWS-011 / SLV-OEWS-012 enforce `wage_annual_* >= 0`. There is no symmetric upper bound. The BLS top-code floor is $239,200 — 45 SOCs hit it on the percentile fields, 0 hit it on `wage_annual_mean` (BLS publishes the mean uncapped). The EDA documents real means as high as **$432,490** (Cardiologists) and explicitly recommends *not* writing a `mean <= p90` rule (would generate 23 false positives). Fine. But that decision leaves the upper end of the wage domain entirely unconstrained:

- A parser bug that multiplied a wage by 1000 (`$93,600 -> $93,600,000`) would not break monotonicity if applied uniformly across all percentiles.
- A spreadsheet column-shift that landed `total_employment = 3,282,010` into `wage_annual_p25` would fail the spot checks for 15-1252 and 29-1141 (`RAW-OEWS-008/009`) only because those two SOCs are spot-checked. For the other 829 SOCs, no rule would fire — the value would be inside monotonic order if `p10` was also corrupted.

The EDA tells us the **realistic ceiling** for an annual percentile is `wage_annual_mean` at ~$500K (Cardiologists). A safe upper bound for the percentile fields (`p10/p25/median/p75/p90`) is the top-code floor itself: $239,200. For the mean, $1,000,000 is a 2x-of-observed-max headroom.

**Recommended fix:** Add `RAW-OEWS-014` / `SLV-OEWS-014` (P0, Validity):
- `wage_annual_p10/p25/median/p75/p90 IS NULL OR value <= 239200` (each percentile is bounded above by the BLS top-code floor by definition)
- `wage_annual_mean IS NULL OR wage_annual_mean <= 1_000_000`

This rule **passes cleanly on real May 2024 data** (per EDA: max non-mean percentile = 239,200; max mean = $432,490 < $1M).

---

### G3 — Bronze has no rule that `OCC_GROUP == 'detailed'` filter actually held [P0]

**Severity:** **P0.** The spec mandates filtering to `detailed` rows; if the filter regresses, summary-group wage data (national rollups across all SOCs in a group) would silently leak in.

**Detail:** The ingestor filters `OCC_GROUP == 'detailed'` (`src/raw/bls_oews_ingestor.py` line 226 `if str(occ_group).lower() != "detailed": continue`). If the OEWS file changes its `OCC_GROUP` capitalization, encoding, or column name, the filter could silently match nothing (zero rows -> RAW-OEWS-001 fires) or, worse, match a superset (major-group SOCs like `15-0000` would have `wage_annual_*` populated and would join cleanly to nothing in OOH/O*NET because `15-0000` is not in either's SOC table).

The current rule set has **no rule on `OCC_GROUP`** — and `OCC_GROUP` is **not even in the Bronze schema**, only in the source file. The spec's safety net for filter regression is purely RAW-OEWS-001 (row count band 800-900), which would fire if the filter completely failed (since the unfiltered file is ~1700 rows). But a *partial* filter regression — say, `detailed` capitalized to `Detailed` so 100 of 831 rows survive — would land at 731 rows, fire RAW-OEWS-001, but the 731 rows might be the wrong 731 (if a `.lower()` was the regression vector).

**The structural fix is in the ingestor:** preserve the `OCC_GROUP` value as a passthrough field at Bronze and assert at DQ time that 100% of rows are `OCC_GROUP == 'detailed'`. This is a **schema change** at Bronze (adds one column) plus one DQ rule. Per the spec's "no schema changes without a spec" rule, this is technically a spec amendment — but it's a one-line, additive, non-breaking column.

A weaker fix that does **not** require a schema change: detect summary-group SOC code patterns at the Bronze rule layer. SOC summary groups always end in `-0000` (major), `-X000` (minor), or `-XX00` (broad). A rule of the form `NOT regexp_matches(soc_code, '^\d{2}-(0000|\d000|\d{2}00)$')` catches all three.

**Recommended fix:** Add `RAW-OEWS-015` / `SLV-OEWS-015` (P0, Consistency):
- `SELECT * FROM bronze.bls_oews WHERE regexp_matches(soc_code, '^\d{2}-(0000|\d000|\d{2}00)$')` — threshold: `result_count = 0`.

Cleaner than amending the schema. **Passes on real data** (the EDA confirmed all 831 rows are detailed, so no rolled-up codes are present today).

---

### G4 — Source-vintage drift: no rule fires when May 2025 OEWS lands [P1]

**Severity:** **P1.** The pipeline will silently begin serving 2024 data labeled as "current" if the source file URL doesn't change.

**Detail:** The Bronze schema includes `load_date` (the date the ingestor ran) but **not** the source vintage (e.g. "May 2024"). The source URL `https://www.bls.gov/oes/special-requests/oesm24nat.zip` is hardcoded with `24` in the path (per spec line 33). When BLS publishes May 2025 data, the URL becomes `oesm25nat.zip`. The ingestor would either (a) get a 404 and fall back to the cached 2024 file (which still satisfies all 12 rules), or (b) be manually updated and the ingest would proceed on 2025 data.

In scenario (a), the rule set passes 12/12 forever, the data dictionary still says "May 2024," and downstream consumers receive stale wages with no signal. There is **no rule on `ingested_at` freshness**, no rule that the source URL contains a string matching the current data dictionary's stated vintage, and no rule that the spot-check medians (Software Devs, RNs) drift between vintages — both windows ($110K-$150K and $75K-$100K) are wide enough to accommodate 5+ years of nominal wage growth.

**Recommended fix:** Add `RAW-OEWS-016` (P1, Freshness):
- `MAX(ingested_at) >= NOW() - INTERVAL 14 MONTH` — BLS publishes annually; 14 months gives a 2-month grace window. Fires when the data is meaningfully stale.

Add `RAW-OEWS-017` (P1, Provenance):
- `100% of rows have source_url containing 'oesm{YY}nat.zip' where {YY} matches the data dictionary's stated vintage`. (Implementation detail: the data dictionary value would need to be parameterizable; alternative is to hard-code the current vintage in the rule and update it during the annual refresh spec.)

---

### G5 — `wage_hourly_median` is in the schema but has zero rules [P1]

**Severity:** **P1.** Lower than G1 only because the spec says this column is "kept for reference, not used downstream" (spec line 60).

**Detail:** `wage_hourly_median` is a `DoubleType()` column in the Bronze schema (NestedField ID 10) and survives Silver promote unchanged. The ingestor's `_parse_wage()` runs the same value-coercion path that handles `wage_annual_*` — including the negative-wage gap closed by RAW-OEWS-011 for the annual fields, but **not for the hourly field**. RAW-OEWS-011's SQL explicitly enumerates the six annual columns and excludes `wage_hourly_median`:

```sql
WHERE (wage_annual_p10 IS NOT NULL AND wage_annual_p10 < 0) OR
      (wage_annual_p25 IS NOT NULL AND wage_annual_p25 < 0) OR
      (wage_annual_median IS NOT NULL AND wage_annual_median < 0) OR
      (wage_annual_p75 IS NOT NULL AND wage_annual_p75 < 0) OR
      (wage_annual_p90 IS NOT NULL AND wage_annual_p90 < 0) OR
      (wage_annual_mean IS NOT NULL AND wage_annual_mean < 0)
```

So a corrupted `wage_hourly_median = -50` would survive, and there is no consistency rule (e.g. `wage_hourly_median * 2080 ≈ wage_annual_median ± 20%`) tying it to the annual median. The spec's "reference only" framing does **not** justify zero rules — any field in the schema is a contract surface.

**Recommended fix:** Add `RAW-OEWS-018` / `SLV-OEWS-018` (P1, Validity):
- Extend the non-negative guard to include `wage_hourly_median` (single-line SQL extension to RAW-OEWS-011, or a sister rule).
- Optional P2: `wage_hourly_median * 2080 / wage_annual_median BETWEEN 0.8 AND 1.25` for rows where both are non-null. (BLS uses 2080 hours/year as the conversion factor; tolerating ±20% covers the 27 SOCs with seasonal/part-time patterns.)

---

### G6 — `wage_capped` non-null rate is implicit, not enforced [P1]

**Severity:** **P1.** EDA explicitly recommended this rule (§Threshold Lock-In recommendation 1: "P0: `wage_capped` non-null = 100% — required field per schema; codify as a rule").

**Detail:** `wage_capped` is `BooleanType()` with `required=True` in the Iceberg schema. Iceberg required-ness is enforced at write time, not read time, so a corrupted Parquet file that pre-existed the schema change could surface NULLs. Rules RAW-OEWS-006 and RAW-OEWS-007 reference `wage_capped` in their SQL (`WHERE wage_capped = TRUE` / `WHERE wage_capped = FALSE`), but a NULL `wage_capped` would be excluded from both predicates and would silently pass both rules.

This is the EDA's recommendation #1 verbatim, **not implemented** in either rule file.

**Recommended fix:** Add `RAW-OEWS-019` / `SLV-OEWS-019` (P0/P1, Completeness):
- `SELECT * FROM bronze.bls_oews WHERE wage_capped IS NULL` — threshold: `result_count = 0`.

P0 is defensible (the field is required); P1 is also defensible (Iceberg enforces at write).

---

### G7 — Cross-row consistency / group-rollup sanity is not validated [P2 / OUT-OF-SCOPE]

**Severity:** **P2 — out of scope for this spec.** Recommend deferring.

**Detail:** OEWS publishes major/minor/broad summary rows alongside detailed rows. The spec **excludes** them from the Bronze table (the filter at ingestor line 226). Therefore there is no in-table cross-row consistency check possible (e.g. "the median of all detailed SOCs in major group 15 should be near the published 15-0000 group median"). To do this, the major/minor/broad rows would need to be ingested into a separate Bronze table (`bronze.bls_oews_summary`) and joined.

This is a real epistemic check — it would catch parser-shift errors that affect entire major groups — but it requires a schema/ingestor change. **Recommend out-of-scope for this spec; flag for a follow-up "OEWS summary rollup verification" spec.**

---

### G8 — Encoding/unicode anomalies in `occupation_title` are unprobed [P2 / OUT-OF-SCOPE]

**Severity:** **P2 — out of scope.** Real-world impact is small.

**Detail:** OEWS occupation titles include forward slashes, hyphens, parentheses, and ampersands (e.g. "Anesthesiologists" — plain ASCII; but "Computer Numerically Controlled Tool Operators" includes spaces and capitalization). Title corruption was probed by S9 (empty string) and caught by RAW-OEWS-010. But:
- A title with an embedded null byte (`\x00`) — would `TRIM(title) = ''` catch it? Probably not.
- A title encoded as UTF-16 instead of UTF-8 — the openpyxl reader handles this transparently; the question is whether downstream consumers (the FastAPI JSON serializer) do.
- A title containing a homoglyph (`Cyrillic 'е' vs Latin 'e'`) — would not affect joins (SOC code is the join key) but would affect display.

These are tail-end risks. **Recommend out-of-scope; document in the data dictionary that titles are passed through verbatim and downstream consumers are responsible for display sanitization.**

---

### G9 — OEWS-OOH SOC orphan check exists at Gold (declarative) but not at Bronze/Silver [P2 / OUT-OF-SCOPE]

**Severity:** **P2.** Already declared in the chaos manifest's `gold_synthetic_scenarios.GS4` ("orphan join"). Properly belongs at Gold.

**Detail:** The EDA established that 1 of 832 OOH SOCs (`45-3031` Fishing and Hunting Workers) is missing from OEWS, and 26 of 798 O*NET SOCs are missing from OEWS. These are absences (OEWS-side undercoverage), which the spec accepts via the LEFT JOIN. The reverse — a SOC in OEWS that is **not** in OOH — is an *orphan*. If May 2025 OEWS adds a new SOC that the SOC 2018 standard does not include (e.g. a 2018-detail-rollup that BLS now publishes separately), the orphan would surface and join to NULL on the OOH side. The chaos manifest declares `GS4` as a Gold scenario; no Bronze or Silver rule asserts this.

**Recommended:** **Out-of-scope for this spec at the Bronze/Silver layer.** The Gold scorecard re-run (workflow step 7) is the right place. Note the gap in the audit trail and ensure GS4 is exercised when Gold materializes.

---

## 2. Evidence Demands

For each gap, the evidence I would need before signing off:

| Gap | What I need to see |
|-----|---------------------|
| **G1 (total_employment)** | (a) New rule(s) `RAW-OEWS-013` and `SLV-OEWS-013` added with `result_count = 0` verified against real Bronze. (b) Chaos-monkey re-run with a new scenario `S11: total_employment = -1 on one row` and a verdict `CAUGHT`. (c) Optional: scenario `S12: total_employment = 999_999_999 on one row` with verdict `CAUGHT` (only if the upper-bound rule is added). |
| **G2 (wage upper bound)** | New rule `RAW-OEWS-014` added; chaos-monkey scenario `S13: wage_annual_p25 = 9_999_999_999 on a non-spot-check row` with verdict `CAUGHT`. Show the rule passes against current real Bronze (max non-cap percentile is $216K — well under $239,200 ceiling for the 5 percentile fields). |
| **G3 (OCC_GROUP filter holdback)** | New rule `RAW-OEWS-015` added; chaos-monkey scenario `S14: insert SOC code 15-0000 (a major-group code) into shadow Bronze` with verdict `CAUGHT`. |
| **G4 (vintage drift)** | New rules `RAW-OEWS-016` (freshness) and `RAW-OEWS-017` (provenance) added; chaos scenario simulates `ingested_at` 18 months ago -> rule fires; scenario simulates source_url with a different vintage string -> rule fires. |
| **G5 (wage_hourly_median)** | RAW-OEWS-011 SQL extended to include the hourly column (or sister rule `RAW-OEWS-018`); chaos scenario `wage_hourly_median = -25 on one row` -> `CAUGHT`. |
| **G6 (wage_capped non-null)** | New rule `RAW-OEWS-019` added; scenario `wage_capped = NULL on one row` -> `CAUGHT`. |
| **G7, G8, G9** | A follow-up spec or an explicit "deferred" entry in the audit trail with the rationale. No rule changes expected for this spec. |

---

## 3. Assessment of Existing Controls

For each gap, grading the project's existing controls against my standard ("would a regulator accept this?"):

| Gap | Control today | Grade | Why |
|-----|----------------|-------|-----|
| G1 (total_employment) | **None.** Field has zero rules in either Bronze or Silver rule files. | **MISSING** | No mitigation. The exact same chaos pattern that found S10 would find this; the rule writer simply did not point at this column. |
| G2 (wage upper bound) | RAW-OEWS-005 monotonicity catches *some* upper-bound errors (an isolated out-of-range value breaks ordering); the two spot checks (RAW-OEWS-008/009) catch SOC-15-1252 and SOC-29-1141 specifically. | **WEAK** | Monotonicity is a relational invariant; it does not catch uniform shifts upward (e.g. all percentiles ×1000). Spot checks cover 2 of 831 SOCs (0.24% coverage). |
| G3 (OCC_GROUP filter) | RAW-OEWS-001 row count band (800-900) is the only fence. RAW-OEWS-003 uniqueness would catch duplicate `15-0000` rows but not a single one. | **WEAK** | Catches catastrophic filter failure (zero rows or 1700 rows) but not partial / case-sensitivity / encoding regressions that yield a row count still in band. |
| G4 (vintage drift) | Spot-check windows (RAW-OEWS-008/009) are wide enough to accommodate 5+ years of wage growth — a feature, not a bug, when calibration is the goal, but a hole when freshness is the question. No `ingested_at`-based rule. | **MISSING** | Pipeline can serve 5-year-old data without a single rule firing. |
| G5 (wage_hourly_median) | Schema enforces `DoubleType()`; coercion path is the same as annual fields. The negative-wage rule (RAW-OEWS-011) does **not** include this column. | **MISSING** | A 7-column `_parse_wage` chain has guard rails on 6 columns. |
| G6 (wage_capped non-null) | Iceberg `required=True` at write time; no read-time rule. RAW-OEWS-006/007 use `WHERE wage_capped = TRUE / FALSE`, both of which exclude NULL. | **WEAK** | The biconditional rule pair has a NULL-shaped hole right between them. |
| G7 (cross-row group rollup) | Out of table — group rows are filtered out at ingest. No control possible inside this spec. | **N/A (defer)** | Real epistemic check, but legitimate scope-deferral. |
| G8 (encoding) | RAW-OEWS-010 catches null/empty titles. Downstream consumers handle Unicode display. | **ADEQUATE** (within scope) | Tail risk; project memory rule "no path is out of scope" applies, but the practical attack surface is small. |
| G9 (Gold orphan) | Declared in chaos manifest as `GS4`; will be exercised when Gold materializes. | **STRONG** (deferred) | Properly scoped; tracked. |

**Summary by grade:** STRONG: 1 (G9). ADEQUATE: 1 (G8). WEAK: 3 (G2, G3, G6). MISSING: 3 (G1, G4, G5). N/A: 1 (G7).

---

## 4. Recommendations

### Mandatory (before sign-off)

1. **Close G1, G2, G3 (P0 gaps) with new Bronze + Silver rules.** Concrete patches in the Evidence Demands table. Estimated effort: 30 min for @dq-rule-writer.

2. **Re-run chaos-monkey with three new scenarios:**
   - `S11: total_employment = -1 on SOC 11-1021` (mirror of S10's shape).
   - `S13: wage_annual_p25 = 9_999_999_999 on SOC 11-1021`.
   - `S14: insert SOC code 15-0000 with all wage fields populated to shadow Bronze`.

   Each scenario must produce verdict `CAUGHT` against the new rule set. Estimated effort: 20 min for @chaos-monkey to add to manifest + re-run cycle.

3. **Update the post-chaos addendum** (`governance/audit-trail/2026-05-06-dq-rule-writer-bls-oews.md`) to reflect 15 rules at Bronze and 15 at Silver. Bump the dq-engineer scorecard accordingly.

### Recommended (close before next vintage refresh)

4. **Close G4 (vintage drift).** Add `RAW-OEWS-016` (freshness) and `RAW-OEWS-017` (provenance). This is more important than it looks: the spec hardcodes `oesm24nat.zip` and the cache fallback will silently serve stale data forever if BLS changes the URL pattern.

5. **Close G5 (wage_hourly_median).** Trivial extension to RAW-OEWS-011 / SLV-OEWS-012's SQL. 5 min of work.

6. **Close G6 (wage_capped non-null).** EDA already recommended this as a P0 — adopt the EDA's recommendation verbatim.

### Out-of-scope (track for follow-up specs)

7. **G7 (group rollup verification):** New spec — `verify-bls-oews-group-rollups.md` — that ingests the major/minor/broad rows into a parallel `bronze.bls_oews_summary` table and adds a Silver-zone cross-table consistency rule (median of detailed SOCs in group 15 within ±20% of group 15-0000's published median).

8. **G8 (encoding):** Document in data dictionary; defer.

9. **G9 (Gold orphan):** Already covered by the manifest's `GS4` Gold scenario. Ensure exercised when `consumable.occupation_profiles` materializes (workflow step 10).

---

## 5. Closing Skepticism Notes

Three observations a regulator would press on:

- **The chaos-monkey ran 5 cycles and found 1 gap. The auditor (this report) found 9 more in 2 hours of reading.** This is not a critique of the chaos-monkey — the chaos manifest was scoped to the spec's stated DQ list, which is exactly what an information-barrier-respecting agent should do. But it is a critique of the *pipeline as a whole*: chaos-monkey alone is not a sufficient verification. The chaos-monkey + adversarial-auditor pairing exists for this reason; the chaos report's claim "Adversarial-auditor needed: NO" was premature.

- **The chaos manifest's `silver_synthetic_scenarios` and `gold_synthetic_scenarios` are declarative-only.** They are not runnable until Silver and Gold materialize (workflow steps 8 and 10). The Bronze 12/12 PASS is a partial result; **the spec is not done** and an "all rules pass" assertion at this stage describes only one of three zones.

- **Every new rule recommended above passes against real May 2024 data.** I verified this by cross-referencing the EDA's documented values: smallest non-null wage is $30,160 (passes G2's lower bound — already implemented as RAW-OEWS-011 — and the unwritten G2 upper bound at $239,200/cell, $1M/mean); largest `total_employment` is 3.28M (passes G1's upper bound at 10M); zero summary-rollup SOCs in current Bronze (passes G3); 100% `wage_capped` non-null (passes G6). **Closing these P0 gaps is risk-free against current data and detects real regression vectors.** A regulator would ask why they aren't already closed.

---

**End of audit.**
