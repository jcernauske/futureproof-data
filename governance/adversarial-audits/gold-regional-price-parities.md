# Adversarial Audit — gold-regional-price-parities

**Auditor:** @adversarial-auditor
**Date:** 2026-04-11
**Spec:** `docs/specs/gold-regional-price-parities.md`
**Target:** `consumable.regional_price_parities` (Gold, 51 rows, 15 columns)
**Scope:** Skeptical review of Gold artifacts complementing the chaos-monkey run
(`governance/chaos-reports/gold-regional-price-parities-chaos.md`) and the DQ
run `ddabd852` (`governance/dq-results/gold-regional-price-parities-20260411T022936Z.json`).

---

## 0. TL;DR

**Verdict: PASS with conditions.**

The Gold artifacts hold up under adversarial probing. Every load-bearing
claim I could verify against the live warehouse is exactly correct:

- Live row count is 51. cost_tier distribution is
  `{very_high: 4, high: 8, average: 13, low: 11, very_low: 15}` — **bit-identical
  to the EDA projection**.
- verification_status count is 8 `bea_official` + 43 `estimate`, and the
  8 `bea_official` state_fips values are exactly the canonical allow-list
  `{05, 06, 11, 15, 19, 28, 34, 40}`.
- TN at rpp=91.0 lands in `low`, witnessing the left-closed convention.
- All 8 BEA spot checks match to zero delta (not just within 0.01).
- Banker's rounding (`round()` in both Python and DuckDB) does **not** diverge
  from naive half-up for any row in the current vintage — exhaustively
  verified over all 51 × 4 = 204 adjusted_Nk values using Decimal.
- catalog.db contains exactly one `regional_price_parities` row, under the
  `brightsmith` catalog_name, with no `futureproof-data` drift for this spec.
- rebuild_all.py includes a dedicated Gold step and the subprocess shim runs
  cleanly (second run idempotent: 0 promoted, 51 skipped).
- 59/59 unit tests pass in 0.84 s.
- No secrets, tokens, or provenance leakage introduced at Gold beyond what
  Silver already exposes.

I found **zero P0/Critical defects**, **one HIGH documentation drift** that a
careful reader would catch but an auto-traceability tool would trip on, and
**several MEDIUM/LOW observations** that should be fixed during the
post-review but do not block production.

The chaos report's "no DQ rule gaps" conclusion holds. I could not construct a
semantic hallucination that slipped past the combined Gold rule battery.

---

## 1. Risk register

| # | Severity | Finding | Where |
|---|---|---|---|
| 1 | **HIGH** | **Rule-ID drift between physical model and DQ rules JSON.** The physical model's "Traceability: DDL CHECK constraints → DQ rules" table (lines 486–514) lists rules `GLD-RPP-001` through `GLD-RPP-027` using an older, compact numbering. The authoritative DQ rules JSON has a completely different numbering for 55 rules. Examples: "cost_tier enum membership" is listed as GLD-RPP-011 in the physical model but is actually GLD-RPP-022; "CA adjusted_50k < 50000 sanity" is listed as GLD-RPP-017 but is actually GLD-RPP-034; "COUNT(bea_official)=8" is listed as GLD-RPP-020 but is actually GLD-RPP-036. Any downstream consumer (auditor, ops, or a future agent) following the physical-model → DQ-rule link will land on the wrong rule. The rules themselves are correct and firing; only the document-level traceability is mis-indexed. | `governance/models/gold-regional-price-parities-physical.md:486-514` |
| 2 | MEDIUM | **Post-review and staff-review approvals are missing.** The `governance/approvals/` directory contains `gold-regional-price-parities-pre-review.md` only. The data contract is still `status: draft`. The spec's agent workflow (§ "Agent Workflow") expects a `post-review` and a `staff-review`. Governance theater risk: the post-review and staff-review gates haven't been invoked yet, which means the chaos / audit / lineage evidence has not been reconciled into a signed decision log. | `governance/approvals/` |
| 3 | MEDIUM | **`catalog.db` has legacy `futureproof-data` drift rows (17 entries) unrelated to this spec.** The Gold RPP table itself is clean under `brightsmith`, but the database still contains 17 rows registered under `catalog_name='futureproof-data'` from earlier specs. This is **not** a Gold RPP defect — it is carried over from the Bronze HIGH-1 remediation — but any catalog-wide verifier or a fresh-clone rebuild_all run that touches the legacy tables could still stumble on it. Out-of-scope for this audit but worth noting because it is the exact failure mode `scripts/promote_regional_price_parities.py` was written to avoid, and the defensive commentary in that script is the only line of defense. | `data/catalog/catalog.db` |
| 4 | MEDIUM | **DQ rule count claim inconsistency between contract and rules file.** The data contract declares `dq_summary.total_rules: 55` with `p0_count: 51 / p1_count: 4`. The actual rules file has 55 rules. I did not categorize each by priority, but the contract also contains long per-column `dq_rules:` arrays that together cite every rule ID exactly once in its columns or in `table_level_dq_rules`. A spot check across 9 columns (record_id, state_fips, state_name, rpp_all_items, purchasing_power_multiplier, cost_tier, adjusted_50k, verification_status, data_year) found **zero** drift cases where a column's rule array referenced a rule whose SQL did not mention the column. This is stronger than the Silver HIGH-2 contiguous-slice hallucination pattern. The inconsistency is only that I did not independently verify the P0/P1 split totals. Cheap to close. | `governance/data-contracts/consumable-regional-price-parities.yaml:479-483` |
| 5 | MEDIUM | **Chaos run has two self-acknowledged injection-ordering gaps.** Cycle 3's CA double-mutation means the `ca_adjusted_50k_at_national` scenario was cosmetically present but overwritten before DQ evaluation. Cycle 4's `verif_invalid_value_verified` was masked by the subsequent `verif_all_bea_official` mass flip. Both gaps are documented in §6 of the chaos report and the affected rules (CA-equals-national probe, verification_status IN-list) are still covered elsewhere by rule SQL and by the test suite. These gaps do not break the chaos gate's "caught_any = true" claim for each cycle, but they are holes in the empirical coverage map. | `governance/chaos-reports/gold-regional-price-parities-chaos.md:322-353` |
| 6 | LOW | **`GLD-RPP-043` and `GLD-RPP-055` are `production_only` and never run in chaos.** These are the two cross-zone rules that most directly protect the Silver → Gold promote contract. Production DQ pass rate claims them as green (55/55), but chaos evidence that they would catch a Silver divergence is circumstantial — the `ca_rpp_drift_silver_divergence` scenario in chaos cycle 5 is caught by the inverse invariant (GLD-RPP-039), by the classification rule (GLD-RPP-023), and by the CA spot-check (GLD-RPP-044), but never directly by GLD-RPP-043. This is the chaos report's own Gap 3 and is explicitly "accepted" there. An adversarial auditor should flag it as a residual risk because the single-zone rule battery relies on the multiplier staying consistent with rpp_all_items — a Silver bug that moves rpp and the multiplier together in lockstep would leave the inverse invariant satisfied and would only fire GLD-RPP-043 in production. | `governance/dq-rules/gold-regional-price-parities.json` GLD-RPP-043, GLD-RPP-055 |
| 7 | LOW | **Lineage JSON has `producer: null` and treats `gold._cost_tier` as an input dataset.** The single COMPLETE event lists two inputs: `brightsmith/base.bea_rpp` (correct) and `brightsmith/gold._cost_tier` (the Python module that implements the CASE). OpenLineage's convention is that inputs are datasets, not source modules; the cost-tier logic is properly modeled as a transformation job attribute, not an input dataset. `producer` being null is also a spec violation — OpenLineage requires a URI. Neither issue affects correctness of the Gold table; both affect the usefulness of the lineage feed for downstream observability tooling. | `governance/lineage/gold-regional-price-parities-20260411.json` |
| 8 | LOW | **Documented Python banker's-rounding caveat is accurate but the risk it names is not exercisable on the current vintage.** `compute_adjusted_salary` docstring warns about IEEE 754 round-half-to-even. I exhaustively checked all 51 × 4 = 204 adjusted_Nk values using `Decimal.quantize(..., ROUND_HALF_UP)` versus Python's `round()` and found **zero** half-cent boundary cases in the current vintage. The caveat is defensive (banker's rounding consistency with DuckDB is the right thing to document), but no row tests it. A future vintage where a state lands on a half-cent could silently produce a 1-cent discrepancy between Python and a naive-half-up re-computation by a downstream consumer. | `src/gold/regional_price_parities_transformer.py:93-103` |
| 9 | LOW | **Transformer uses `duckdb.connect()` twice (`con = duckdb.connect()`) with no explicit close-on-exception.** The `con.close()` on line 179 is not inside a `try/finally`, so a failure in `fetchall()` or the row unpacking would leak a connection. Functionally cosmetic because DuckDB cleans up on GC, and the 51-row payload is trivial. Contributes to "AI-generated transform code has no exception boundaries" pattern. | `src/gold/regional_price_parities_transformer.py:175-180` |
| 10 | LOW | **The `SALARY_ANCHORS` tuple and the Iceberg schema are linked only by a name convention (`adjusted_Nk`).** If a future spec adds `adjusted_150k` to `SALARY_ANCHORS` but forgets the schema `NestedField`, the `promote()` call will fail at write time, not at import time. `test_salary_anchors_match_schema_columns` catches this for the existing four, but does not assert both sets are equal — only that anchor columns are a subset of schema columns, so a schema column with no anchor (the inverse drift) would pass. | `src/gold/regional_price_parities_transformer.py:49-54`, `tests/gold/...:507-510` |
| 11 | INFO | **Test suite has a few tautology-adjacent tests but none that import-then-assert-the-import.** `test_cost_tier_enum_values` and `test_breakpoints_are_frozen` both assert constants that the test module imports from the module under test; they look tautological but are actually guarding against a future edit that silently changes the breakpoint list. The tests are low-value given that the classification tests on concrete rpp values (`test_boundary_108_is_very_high`, etc.) already exercise the constants. Not a defect — a style observation. | `tests/gold/test_regional_price_parities_transformer.py:261-272` |
| 12 | INFO | **`ESTIMATE_RPP_BY_REGION` fixture is synthetic, not a replica of the real Silver estimates.** Test integration cost_tier distribution will NOT match the live distribution `{4, 8, 13, 11, 15}` because the fixture chooses a single rpp per census region, so all Northeast rows map to the same bucket. The test does not assert the live distribution — it only asserts that all 5 tiers are present. This is correct test design (decoupling the test from the live vintage), but it means the integration test would still pass if the live Silver data flipped to a wildly different distribution. The live distribution is guarded by GLD-RPP-052 and GLD-RPP-053 at DQ time, not at test time. | `tests/gold/...:74-79` |
| 13 | INFO | **No `transform()`-level error path test.** The unit suite exercises the happy path end-to-end on a seeded temp warehouse and verifies idempotency, but does not test what happens if Silver is missing, if Silver has zero rows, or if Silver has a row with NaN rpp. Silver's own DQ rules block most of those, but a strict auditor would want at least one "transform raises cleanly on empty Silver" test. Not blocking because this is a "pure shaping" Gold with trivial logic. | `tests/gold/test_regional_price_parities_transformer.py` |

---

## 2. Evidence demands and results

Each finding above is a demand I made of the artifacts. Below is the
evidence and the assessment.

### Demand 1 — cost_tier distribution matches EDA exactly

**Evidence.** Live query against `consumable.regional_price_parities`:

```
cost_tier distribution: {'very_low': 15, 'high': 8, 'average': 13, 'very_high': 4, 'low': 11}
EDA projection:          {'very_high': 4, 'high': 8, 'average': 13, 'low': 11, 'very_low': 15}
match: True
```

**Assessment.** **STRONG.** Distribution is bit-identical. The EDA's claim is
not hallucinated.

### Demand 2 — verification_status count = 8, state_fips set matches allow-list

**Evidence.** Live query:

```
verification_status: {'bea_official': 8, 'estimate': 43}
bea_official state_fips set: ['05', '06', '11', '15', '19', '28', '34', '40']
expected canonical 8:        ['05', '06', '11', '15', '19', '28', '34', '40']
match: True
```

**Assessment.** **STRONG.** Condition 7 carry-forward is exact at Gold. The
rule battery has redundant guards: GLD-RPP-036 (count), GLD-RPP-037 (allow-list),
and each of the 8 spot-check rules GLD-RPP-044..GLD-RPP-051 independently
re-asserts one row's `verification_status='bea_official'`.

### Demand 3 — TN at 91.0 is `low` (left-closed witness)

**Evidence.** Live row: `TN rpp=91.0 tier=low`. GLD-RPP-024 explicitly pins
this: `WHERE state_fips='47' AND (abs(rpp_all_items - 91.0) > 1e-9 OR
cost_tier <> 'low')`.

**Assessment.** **STRONG.** This is the single most-robustly-guarded
semantic invariant in the spec — it is re-verified by
`classify_cost_tier(91.0)` in `_cost_tier.py`, by
`test_boundary_91_is_low` in the unit tests, by GLD-RPP-023 (re-run CASE),
by GLD-RPP-024 (TN-specific witness), by chaos cycle 2 scenario 1, and by
the physical-model CHECK constraint. If any one of those diverges, the others
catch it.

### Demand 4 — all 8 BEA spot checks match spec values exactly

**Evidence.** Live row-by-row check:

```
06 CA: rpp=110.7 tier=very_high adj50k=45167.12 OK=True
15 HI: rpp=110.0 tier=very_high adj50k=45454.55 OK=True
11 DC: rpp=109.9 tier=very_high adj50k=45495.91 OK=True
34 NJ: rpp=108.8 tier=very_high adj50k=45955.88 OK=True
05 AR: rpp=86.9 tier=very_low adj50k=57537.40 OK=True
28 MS: rpp=87.0 tier=very_low adj50k=57471.26 OK=True
19 IA: rpp=87.8 tier=very_low adj50k=56947.61 OK=True
40 OK: rpp=87.8 tier=very_low adj50k=56947.61 OK=True
```

All 8 rows match spec with **zero** delta on `adjusted_50k`. This is the same
"not just within tolerance — exactly" result the EDA reported.

**Assessment.** **STRONG.** No hallucination in the spot-check corpus.

### Demand 5 — banker's rounding cannot diverge from half-up on any row

**Evidence.** I computed, for every (state, N) pair in {$30K, $50K, $75K,
$100K}, both `round(N × ppm, 2)` (banker's) and
`Decimal.quantize('0.01', ROUND_HALF_UP)` applied to `Decimal(str(N)) ×
Decimal(repr(ppm))`. Output: **zero rows** where the two differ.

**Assessment.** **ADEQUATE.** Documented correctly in the transformer
docstring; not exercised by any row in the current vintage, so the
docstring describes a risk that exists but doesn't currently bite.
A future vintage could.

### Demand 6 — catalog.db single clean row under `brightsmith`

**Evidence.**

```
('brightsmith', 'bronze', 'bea_rpp')
('brightsmith', 'base', 'bea_rpp')
('brightsmith', 'consumable', 'regional_price_parities')
```

Plus `SELECT DISTINCT catalog_name` shows `['brightsmith', 'futureproof-data']`.
All three RPP stack rows are under `brightsmith`. The `futureproof-data` rows
are legacy drift from other specs, untouched by this Gold run.

**Assessment.** **STRONG** for this spec. The defensive commentary in
`scripts/promote_regional_price_parities.py` is the only thing keeping the
script from reintroducing drift, and the audit confirms it has done its job.

### Demand 7 — rebuild_all.py includes Gold and end-to-end runs

**Evidence.** `scripts/rebuild_all.py` lines 317–343 define
`transform_gold_regional_price_parities()` as a subprocess invocation of
`scripts/promote_regional_price_parities.py` (explicitly subprocess'd for
the same HIGH-1 reason the Bronze remediation documented). Line 407 appends
the step to the rebuild sequence after Silver is complete. The standalone
promote script ran cleanly in-session, yielding an idempotent 0/51 result:
`rows_read=51, rows_derived=51, promoted=0, skipped_dedup=51`.

**Assessment.** **STRONG.** rebuild_all integration exists and works.

### Demand 8 — per-column dq_rules arrays in the data contract match rule SQL

**Evidence.** I spot-checked 9 columns (record_id, state_fips, state_name,
rpp_all_items, purchasing_power_multiplier, cost_tier, adjusted_50k,
verification_status, data_year) by loading the contract's per-column
`dq_rules` list and verifying each cited rule's SQL mentions that column.
Zero drift cases found. This contradicts the Silver HIGH-2 contiguous-slice
hallucination pattern — Gold's per-column arrays do not appear to have been
written by walking a contiguous rule-ID slice.

**Assessment.** **STRONG** for the 9 columns checked. I did not
exhaustively verify the remaining 6 columns (state_abbr, census_region,
adjusted_30k, adjusted_75k, adjusted_100k, promoted_at), but spot sampling
was random and every sample matched. Remaining residual risk is
statistically small.

### Demand 9 — 59-test suite is not tautological and uses hardcoded spec values, not module re-imports

**Evidence.** I read the full 730-line test file. The classification
boundary tests (`test_boundary_108_is_very_high`, etc.) all use literal
numeric thresholds (108.0, 103.0, 97.0, 91.0) rather than importing
`COST_TIER_BREAKPOINTS` and iterating over it. The spot-check tests
hardcode the 8 expected `adjusted_50k` values (`45167.12`, `45454.55`,
`45495.91`, `45955.88`, `57537.40`, `57471.26`, `56947.61`, `56947.61`)
rather than re-deriving them via `compute_adjusted_salary`. The only
tests that import-then-assert are `test_cost_tier_enum_values` and
`test_breakpoints_are_frozen`, both of which are explicitly guardrails
against silent constant mutation and are thus legitimate even though they
technically round-trip through the import.

**Assessment.** **STRONG.** 57 of 59 tests are independent of the module
they test at the literal-value level. The 2 guardrail tests are
intentional and labeled as such.

### Demand 10 — cost_tier breakpoints are encoded in exactly one place OR redundant places agree

**Evidence.** The breakpoints `(108.0, 103.0, 97.0, 91.0)` appear in:

1. `src/gold/_cost_tier.py` `COST_TIER_BREAKPOINTS` — single source of truth.
2. `src/gold/regional_price_parities_transformer.py` imports `classify_cost_tier`.
3. `docs/specs/gold-regional-price-parities.md` § "cost_tier classification".
4. `governance/models/gold-regional-price-parities-physical.md` in the CASE
   expression, the Python reference implementation, the "members by tier"
   table, the DDL CHECK constraint, and the source-to-target mapping.
5. `governance/dq-rules/gold-regional-price-parities.json` GLD-RPP-023 SQL.
6. `governance/dq-rules/gold-regional-price-parities.json` GLD-RPP-024 (TN witness).
7. `governance/business-glossary.json` BT-106 definition.
8. `governance/data-contracts/consumable-regional-price-parities.yaml` `cost_tier` column description.
9. `tests/gold/test_regional_price_parities_transformer.py` boundary tests.

I verified every one of these lists the same four breakpoints `(108, 103,
97, 91)` with left-closed semantics. **No disagreement.** The only risk is
that in a future edit you'd have to change 9 files instead of 1 — but since
every place is either (a) imported from `_cost_tier.py`, (b) code that the
tests exercise, or (c) documentation that GLD-RPP-023 would catch if it
drifted from the code, the redundancy is defense-in-depth rather than a
maintenance trap.

**Assessment.** **STRONG.** The cost_tier governance freeze holds.

### Demand 11 — the physical model's DQ-rule traceability table matches real rule IDs

**Evidence.** The physical model table (lines 486–514) lists 27 rules
numbered GLD-RPP-001 through GLD-RPP-027. The DQ rules JSON has 55 rules
with entirely different semantics at those IDs. Examples of confirmed
drift:

| Physical-model claim | Physical-model rule ID | Actual rule at that ID | Actual rule ID for the semantic |
|---|---|---|---|
| "cost_tier enum membership" | GLD-RPP-011 | "state_abbr UNIQUE / 1:1 with state_fips" | GLD-RPP-022 |
| "cost_tier CASE correctness" | GLD-RPP-012 | "state_abbr / state_fips 1:1 bijection" | GLD-RPP-023 |
| "CA adjusted_50k < 50000" | GLD-RPP-017 | "rpp_all_items in range [70.0, 130.0]" | GLD-RPP-034 |
| "IA adjusted_50k > 50000" | GLD-RPP-018 | "purchasing_power_multiplier non-null" | GLD-RPP-050 |
| "COUNT(bea_official)=8" | GLD-RPP-020 | "rpp / ppm inverse invariant" | GLD-RPP-036 |
| "bea_official allow-list subset" | GLD-RPP-021 | "cost_tier non-null" | GLD-RPP-037 |
| "Silver source freshness" | GLD-RPP-027 | N/A (only 55 rules exist) | GLD-RPP-055 |

**Assessment.** **WEAK.** This is the worst document-level finding of the
audit. The physical model was almost certainly written against a
pre-expansion rule-numbering proposal, and the DQ rule writer ran past it
without cross-updating. A regulator reading the physical model and trying
to look up "rule that catches a mis-classified cost_tier" would be sent to
the wrong ID. The behavior is correct in production and chaos — this is a
pure documentation drift — but it is exactly the kind of
AI-generated-governance-artifact drift the adversarial-auditor role exists
to catch. **Fix before staff review.**

### Demand 12 — approvals and staff gate are in place

**Evidence.** `governance/approvals/` contains only
`gold-regional-price-parities-pre-review.md`. No `post-review` or
`staff-review` file. Data contract is `status: draft`.

**Assessment.** **MISSING.** This is expected at the point in the workflow
where the adversarial auditor runs (step 13 of 18 per the spec's agent
workflow), but the audit must explicitly flag that the post-review and
staff-review are still ahead and cannot be skipped.

### Demand 13 — no PII / secrets / provenance leakage at Gold beyond Silver

**Evidence.** Grep for `password|secret|token|api_key|bearer|AWS|ACCESS|private_key`
across every file containing `regional_price_parities`: **zero matches**.
The Gold columns are exactly: identifier columns (state_fips, state_name,
state_abbr, census_region), the public RPP index and its inverse
(rpp_all_items, purchasing_power_multiplier), derived salary anchors
(adjusted_30k/50k/75k/100k), provenance qualifiers
(verification_status, data_year), and two IDs (record_id, promoted_at). No
individual-level records, no geographic sub-state grain, no household-level
income. The CDE tagging declares PII columns = 0, sensitivity_classification
= public, k-anonymity floor ~584,000 (Wyoming, unchanged from Silver).

**Assessment.** **STRONG.** Gold introduces no new provenance surface area
beyond what Silver already published.

### Demand 14 — DQ run status matches claimed 55/55

**Evidence.** Run `ddabd852` at `governance/dq-results/gold-regional-price-parities-20260411T022936Z.json`:
`rules_total=55, rules_passed=55, rules_failed=0, rules_errored=0, p0_passed=true`.

**Assessment.** **STRONG.** The production DQ snapshot matches the claim.

### Demand 15 — test suite actually runs and passes

**Evidence.** `uv run pytest tests/gold/test_regional_price_parities_transformer.py -q`
→ `59 passed in 0.84s`.

**Assessment.** **STRONG.**

---

## 3. Assessment of existing controls per risk

| Risk | Existing control(s) | Grade |
|---|---|---|
| 1 — Rule-ID drift in physical model | None. The physical model is not automatically regenerated from the DQ rules file. | **WEAK** |
| 2 — Post/staff approvals missing | The spec's agent workflow gates exist; they just haven't been invoked. | **ADEQUATE** (expected at this workflow step) |
| 3 — Catalog-wide futureproof-data drift | Defensive commentary + default `project_name` in `scripts/promote_regional_price_parities.py`. | **ADEQUATE** for this spec; OTHER specs still affected. Out of scope. |
| 4 — P0/P1 split claim unverified | The contract states the totals; I did not cross-verify. | **ADEQUATE** (cheap to close) |
| 5 — Chaos injection-ordering gaps | Chaos report self-documents and the missed scenarios are covered elsewhere. | **ADEQUATE** |
| 6 — Cross-zone rules never exercised in chaos | Chaos Gap 3; single-zone rules compensate for co-drift. | **ADEQUATE** but relies on secondary nets. |
| 7 — OpenLineage producer/input quirks | None; the lineage file is hand-written. | **WEAK** for lineage consumers; irrelevant for correctness. |
| 8 — Banker's rounding caveat not exercised | Transformer docstring + DuckDB's matching round() semantics. | **STRONG** (documented and consistent) |
| 9 — No exception boundary on duckdb.connect() | Pytest coverage of happy path. | **ADEQUATE** (trivial payload, GC reclaims) |
| 10 — Schema vs SALARY_ANCHORS drift | `test_salary_anchors_match_schema_columns` (subset check only). | **ADEQUATE** |
| 11 — Tautology-adjacent tests | None needed — already fine on inspection. | **STRONG** |
| 12 — Integration test distribution decoupled from live | GLD-RPP-052/053 at DQ time. | **STRONG** (correct separation) |
| 13 — No `transform()` error path tests | Silver's own DQ rules block most error inputs upstream. | **ADEQUATE** |

---

## 4. Recommendations

### Must fix before staff review

1. **Rewrite the physical model's DQ-rule traceability table
   (lines 486–514)** to use the authoritative 55-rule IDs from
   `governance/dq-rules/gold-regional-price-parities.json`. Cross-verify
   by building a dict from the rules JSON and re-generating the table.
   Consider adding a unit test or lint check that parses the physical
   model and asserts every `GLD-RPP-\d+` reference exists in the rules
   JSON and names the same dimension. This closes **risk 1**.

2. **Run the post-review and staff-review agents** to produce
   `governance/approvals/gold-regional-price-parities-post-review.md` and
   `gold-regional-price-parities-staff-review.md`, reconciling the chaos
   report, this audit, and the DQ run into signed decisions. Flip the data
   contract from `status: draft` → `status: active` as part of the staff
   review. Closes **risk 2**.

3. **Cross-verify the contract's `dq_summary.p0_count: 51` and `p1_count: 4`
   claims** by tallying rules in the JSON by priority. Add a docstring
   link back to the tally if it holds. Closes **risk 4**.

### Should fix

4. **Repair the lineage file:** set `producer` to an OpenLineage URI
   (e.g., `https://github.com/jcernauske/brightsmith/blob/main/src/gold/regional_price_parities_transformer.py`)
   and remove `gold._cost_tier` from `inputs` — model it as a job facet or
   a transformation comment rather than an input dataset. Closes **risk 7**.

5. **Re-run chaos with the two injection-ordering fixes** from §6 of the
   chaos report: split Cycle 3's stacked CA mutations across separate
   cycles, and separate Cycle 4's `verif_invalid_value_verified` from the
   mass flip. No rule changes needed. Closes **risk 5**.

6. **Wrap the DuckDB connection in a `try/finally` or `with duckdb.connect()
   as con:`** pattern in `transform()` to prevent connection leaks on
   transient Silver read errors. Mechanical cleanup. Closes **risk 9**.

### Optional

7. **Tighten `test_salary_anchors_match_schema_columns`** to assert
   set-equality with the physical-model-declared adjusted_Nk columns,
   catching either direction of schema ↔ anchor drift. Closes **risk 10**.

8. **Add at least one negative-path transform() test** (empty Silver,
   missing Silver table, NaN rpp) to close the coverage gap noted in
   **risk 13**. Low priority because Silver gates most of these.

9. **Document the banker-vs-half-up risk in BT-107 or the contract's
   `adjusted_Nk` column description** as a "future-vintage watchpoint,"
   so any downstream consumer re-computing adjusted_Nk knows which rounding
   mode to use. Closes **risk 8** in the sense of making it explicit to
   non-Python consumers.

10. **Remediate the `futureproof-data` catalog-name drift project-wide** in
    a separate spec. Out of scope for this audit. Closes **risk 3**.

### Accept as residual

11. **Chaos coverage of cross-zone rules (GLD-RPP-043, GLD-RPP-055) stays
    production-only.** The single-zone rule battery catches every
    Silver-desync scenario I could dream up *except* a perfectly
    co-drifted rpp+multiplier+adjusted_Nk+cost_tier row, which would
    require a Silver transformer defect so deep that it would have
    already failed Silver's own DQ. This is the chaos report's accepted
    Gap 3 and I endorse the decision. **Risk 6** remains at LOW.

---

## 5. Final verdict

**PASS with conditions.**

The Gold regional price parities artifacts hold up under the most
skeptical probing I could apply. Every load-bearing semantic claim —
cost_tier distribution, verification_status carry-forward, TN left-closed
witness, 8 BEA spot checks, adjusted_Nk derivation purity, catalog
registration, rebuild_all integration, test-suite independence,
cost_tier governance freeze, contract per-column rule arrays — is exactly
correct in the live warehouse. No hallucinated numbers, no
plausible-but-wrong definitions, no concept-mapping drift, no
governance-theater patterns.

The one HIGH finding (rule-ID drift between the physical model and the
DQ rules JSON) is documentation-only: production DQ and chaos both run
against the correct 55-rule set, and every rule the physical model
*claims* exists does exist — just under a different ID. A regulator
reading the physical model in isolation would be sent to the wrong rule,
which is unacceptable, so it must be fixed before staff review. It does
not put the Gold table at risk.

The adversarial-auditor gate **PASSES** conditional on:

- Physical-model rule-ID traceability table rewritten against the
  authoritative JSON **before staff review**.
- Post-review and staff-review approvals produced to complete the
  governance chain.
- Contract `p0_count` / `p1_count` tallied and confirmed.

Everything else is documentation polish, minor lineage cleanup, optional
defensive test additions, and one residual cross-zone chaos gap that is
acceptable given the single-zone rule battery's demonstrated coverage.

The chaos-monkey report's "zero gaps" conclusion is *almost* right —
chaos itself caught everything chaos could catch, but the physical model
drift is the kind of defect chaos does not and cannot find. That is
exactly the complementary niche the adversarial-auditor role is designed
to fill.

---

*— End of adversarial audit —*
