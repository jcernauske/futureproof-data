## DQ Scorecard: raw-ingest-bls-oews
**Spec:** raw-ingest-bls-oews
**Date:** 2026-05-07 (post-adversarial-auditor re-execution)
**Agent:** @dq-engineer
**Run ID:** f1800bc7 (latest); 646f3c24 (prior, post-chaos); 4edd3cea (original)
**Results File:** governance/dq-results/raw-ingest-bls-oews-20260507T033237Z.json (latest); governance/dq-results/raw-ingest-bls-oews-20260507T032019Z.json (prior post-chaos); governance/dq-results/raw-ingest-bls-oews-20260507T030558Z.json (original)
**Overall Score:** 15/15 Bronze rules passing (100%); Silver and Gold rules DEFERRED pending downstream tables
**Data Source:** FULL DATASET — `bronze.bls_oews` Iceberg table, 831 rows of real BLS OEWS May 2024 National Wage Percentiles
**Note:** Re-execution after @dq-rule-writer added three new P0 rules (RAW-OEWS-013, RAW-OEWS-014, RAW-OEWS-015) to close adversarial-auditor gaps G1, G2, and G3. Rule count grew from 12 to 15. All three new rules are P0; all pass on real data with the expected values. Silver (`base.bls_oews`) and Gold (`consumable.occupation_profiles` OEWS enrichment) tables still do not exist; their rules remain DEFERRED.

### Execution Results — Bronze (raw-ingest-bls-oews)

| Rule ID | Dimension | Priority | Description | Result | Evidence |
|---------|-----------|----------|-------------|--------|----------|
| RAW-OEWS-001 | Volume | P0 | Row count within expected range: 800-900 | PASS | count=831; range=[800,900]; matches EDA target ~830 detailed occupations |
| RAW-OEWS-002 | Validity | P0 | SOC code format: XX-XXXX | PASS | violations=0; all 831 SOC codes match `^\d{2}-\d{4}$` |
| RAW-OEWS-003 | Uniqueness | P0 | Grain uniqueness: soc_code | PASS | total=831, distinct=831, duplicates=0 |
| RAW-OEWS-004 | Completeness | P0 | wage_annual_median non-null rate >= 99% | PASS | non-null=826/831 = 99.398%; 5 expected suppressions (performance-arts SOCs 27-2011 Actors, 27-2031 Dancers, 27-2042 Musicians/Singers, 27-2091 DJs Except Radio, 27-2099 Entertainers All Other) |
| RAW-OEWS-005 | Consistency | P0 | Per-row monotonicity: p10 <= p25 <= median <= p75 <= p90 | PASS | violations=0; invariant holds on all 826 rows with full annual percentile data |
| RAW-OEWS-006 | Consistency | P0 | wage_capped=True implies at least one annual percentile = 239200 | PASS | violations=0; all 45 capped rows have at least one percentile at the BLS top-code floor |
| RAW-OEWS-007 | Consistency | P0 | wage_capped=False implies no annual percentile = 239200 (false-positive guard) | PASS | violations=0; no row has a 239200 annual percentile without the cap flag |
| RAW-OEWS-008 | Validity | P0 | Spot check: SOC 15-1252 (Software Developers) median in [$110K, $150K] | PASS | observed median=$133,080 (well within window) |
| RAW-OEWS-009 | Validity | P0 | Spot check: SOC 29-1141 (Registered Nurses) median in [$75K, $100K] | PASS | observed median=$93,600 (within window; May 2024 vintage drift accommodated) |
| RAW-OEWS-010 | Completeness | P0 | occupation_title not null: 100% | PASS | violations=0; all 831 rows have non-empty title (831 distinct titles, 100% unique) |
| RAW-OEWS-011 | Validity | P0 | All non-null annual wage values are >= 0 (non-negative wage guard) — post-chaos addition | PASS | violations=0; 100% of 831 rows have non-negative values across all six annual wage columns. Closes chaos scenario S10. |
| RAW-OEWS-012 | Volume | P1 | wage_capped=TRUE row count in [5, 80] (top-code-floor drift detector) — post-chaos addition | PASS | observed count=45; window=[5, 80]; matches EDA-expected value exactly. |
| RAW-OEWS-013 | Validity | P0 | total_employment non-negative AND non-null rate >= 99% — **POST-AUDITOR ADDITION (G1)** | PASS | total=831, non-null=831/831 = 100%, neg_count=0; min_emp=180 (51-7032 Patternmakers, Wood), max_emp=3,988,140 (31-1120 Home Health and Personal Care Aides). Closes adversarial-auditor gap G1 (structural mirror of negative-wage attack S10 re-pointed at total_employment). |
| RAW-OEWS-014 | Validity | P0 | Annual wage upper-bound sanity (percentiles <= 239200; mean <= 500000) — **POST-AUDITOR ADDITION (G2)** | PASS | violations=0; max p10=$189,720, max p25=$239,200 (cap), max median=$239,200 (cap), max p75=$239,200 (cap), max p90=$239,200 (cap), max non-cap percentile=$235,750; max mean=$450,810 (29-1243 Pediatric Surgeons), comfortably under $500K ceiling. Closes adversarial-auditor gap G2 (positive-direction twin of RAW-OEWS-011; catches x1000 parser bugs that preserve monotonicity). |
| RAW-OEWS-015 | Consistency | P0 | Detailed-only filter held: no summary-group SOC codes present — **POST-AUDITOR ADDITION (G3)** | PASS | violations=0; zero rows match `^\d{2}-(0000\|\d000\|\d{2}00)$` summary-group regex. First 5 SOC codes confirm detailed grain: 11-1011, 11-1021, 11-1031, 11-2011, 11-2021. Closes adversarial-auditor gap G3 (catches partial summary-group leakage that would land inside the [800, 900] row-count band). |

### Summary by Priority — Bronze

| Priority | Total | Executed | Pass | Fail | Deferred |
|----------|-------|----------|------|------|----------|
| P0 | 14 | 14 | 14 | 0 | 0 |
| P1 | 1 | 1 | 1 | 0 | 0 |
| **Total** | **15** | **15** | **15** | **0** | **0** |

### Deferred Rule Sets — Silver & Gold

The Silver and Gold rule sets are intentionally NOT executed in this run because their target tables do not yet exist. They will be executed in follow-up dq-engineer runs after the Silver and Gold dispatches complete.

| Rule File | Rule Count | Target Table | Status | Reason |
|-----------|-----------|--------------|--------|--------|
| `governance/dq-rules/silver-base-bls-oews.json` | 11 (SLV-OEWS-001 .. 011) | `base.bls_oews` | DEFERRED | Silver dispatch not yet run; `base.bls_oews` Iceberg table does not exist |
| `governance/dq-rules/gold-occupation-profiles-bls-oews.json` | 4 (GLD-OP-OEWS-001 .. 004) | `consumable.occupation_profiles` (OEWS-enriched columns) | DEFERRED | Gold dispatch has not yet enriched `consumable.occupation_profiles` with the OEWS percentile columns |

**Action for follow-up dq-engineer run:** After Silver dispatch lands `base.bls_oews`, run `uv run python -m brightsmith.infra.dq_runner run --spec silver-base-bls-oews`. After Gold dispatch enriches `consumable.occupation_profiles`, run `uv run python -m brightsmith.infra.dq_runner run --spec gold-occupation-profiles-bls-oews`. Update this scorecard (or produce zone-specific scorecards) once both have executed.

### Supporting Evidence (queried from `bronze.bls_oews`)

| Metric | Value | Notes |
|--------|-------|-------|
| Row count | 831 | Spec target ~830, range [800, 900] |
| Distinct soc_code | 831 | 100% unique, dedup grain holds |
| wage_annual_median non-null | 826 / 831 (99.398%) | 5 suppressed SOCs (all performance arts; documented in EDA) |
| wage_capped=True | 45 | Top-coded SOCs at BLS $239,200 floor (cardiologists, anesthesiologists, etc.); inside RAW-OEWS-012 window [5, 80] |
| wage_capped=False | 786 | All have no percentile equal to 239200 (false-positive guard clean) |
| occupation_title null | 0 | 100% complete; 831 distinct titles |
| SOC 15-1252 (Software Developers) median | $133,080 | Inside [$110K, $150K] window |
| SOC 29-1141 (Registered Nurses) median | $93,600 | Inside [$75K, $100K] window; near upper end (May 2024 vintage drift documented in EDA) |
| Negative wages (any of 6 annual columns) | 0 / 831 (0%) | 100% non-negative; smallest non-null p10 = $18,500. Confirms RAW-OEWS-011 invariant on real data. |
| total_employment non-null | 831 / 831 (100%) | Full coverage on May 2024 vintage; 99% floor (RAW-OEWS-013) leaves 1% buffer for future suppression |
| total_employment min / max | 180 / 3,988,140 | min: 51-7032 Patternmakers, Wood; max: 31-1120 Home Health and Personal Care Aides; zero negatives |
| Max non-cap annual percentile | $235,750 | Below $239,200 BLS floor; confirms RAW-OEWS-014 percentile ceiling holds with no margin issue |
| Max wage_annual_mean | $450,810 | 29-1243 Pediatric Surgeons; below $500K ceiling (RAW-OEWS-014); top-3: Pediatric Surgeons $450,810, Cardiologists $432,490, Surgeons All Other $371,280 |
| Summary-group SOC rows | 0 / 831 | Zero matches against `^\d{2}-(0000\|\d000\|\d{2}00)$`; confirms RAW-OEWS-015 detailed-only filter holds |

### Suppressed Wage Rows (RAW-OEWS-004 — expected, not violations)

| SOC Code | Title |
|----------|-------|
| 27-2011 | Actors |
| 27-2031 | Dancers |
| 27-2042 | Musicians and Singers |
| 27-2091 | Disc Jockeys, Except Radio |
| 27-2099 | Entertainers and Performers, Sports and Related Workers, All Other |

These five SOCs are intrinsically suppressed by BLS because gig compensation is not meaningfully measurable as an annual/hourly wage. Threshold tightened from spec's 95% to 99% per EDA evidence — current 99.398% leaves a one-extra-suppression buffer next refresh while still detecting regression.

### Comparison to Previous Run

| Metric | Prior run (646f3c24, 2026-05-07T03:20:19Z) | Latest run (f1800bc7, 2026-05-07T03:32:37Z) | Delta |
|--------|--------------------------------------------|--------------------------------------------|-------|
| Rules executed | 12 | 15 | +3 (RAW-OEWS-013, 014, 015 — all P0, post-adversarial-auditor additions) |
| Rules passed | 12 | 15 | +3 (all three new rules pass) |
| Rules failed | 0 | 0 | unchanged |
| P0 gate | PASS | PASS | unchanged |
| P0 rule count | 11 | 14 | +3 |
| P1 rule count | 1 | 1 | unchanged |
| Row count | 831 | 831 | unchanged (same Iceberg snapshot) |
| wage_capped=TRUE | 45 | 45 | unchanged |

No regressions. Three rules added, all pass. The 12 previously-active rules executed identically to the prior run on the same underlying snapshot. No rule calibration changes requested.

### Post-Chaos Additions — RAW-OEWS-011 and RAW-OEWS-012

These two rules were added by @dq-rule-writer after the chaos-monkey post-mortem to close a structural gap. The original 10 rules let chaos scenario S10 (negative wage injection that preserved monotonicity) slip through.

| Rule | Priority | Why it was added | Real-data result |
|------|----------|------------------|------------------|
| RAW-OEWS-011 | P0 | Structural domain guard: a negative annual wage is impossible in BLS OEWS. RAW-OEWS-005 (monotonicity) is satisfied by any uniformly-shifted-down chain, so a single negative p25 with p10 also driven negative or null can slip through. RAW-OEWS-008/009 only spot-check two SOCs. RAW-OEWS-011 closes the gap for all 6 annual wage columns and all 831 rows. | PASS — 0/831 rows have any negative annual wage. Smallest non-null p10 = $18,500. |
| RAW-OEWS-012 | P1 | Top-code-floor drift detector: monitors the wage_capped=TRUE population. Lower bound 5 catches catastrophic ingestor regression on the `#` sentinel; upper bound 80 catches a doubling of capped-SOC population (BLS methodology shift or parser bug). P1 because the boundary is empirical and reasonable drift is allowed. | PASS — observed count = 45, comfortably inside [5, 80]. Matches EDA-stated value exactly. |

### Post-Adversarial-Auditor Additions — RAW-OEWS-013, RAW-OEWS-014, RAW-OEWS-015

These three rules were added by @dq-rule-writer after the adversarial-auditor identified three structural gaps (G1, G2, G3) in the post-chaos rule set. All three are P0 — same severity class as the negative-wage gap they parallel. All entered as PROPOSED on 2026-05-06T23:30:00Z and were approved (`dq_runner approve RAW-OEWS-013 RAW-OEWS-014 RAW-OEWS-015`) by this agent immediately prior to execution. All three auto-advanced from APPROVED to ACTIVE on this successful run against real data.

| Rule | Priority | Auditor gap | Why it was added | Real-data result |
|------|----------|-------------|------------------|------------------|
| RAW-OEWS-013 | P0 | G1 — total_employment had zero rules of any kind | Structural mirror of the negative-wage gap (S10/RAW-OEWS-011) re-pointed at the second numeric payload column. The ingestor's `_coerce_employment()` (`src/raw/bls_oews_ingestor.py` line 401-424) accepts negative integers and absurdly large values without sign or magnitude checks. Combined non-negativity + 99% non-null floor in a single rule. | PASS — 831/831 non-null (100%); 0 negative values; min=180 (51-7032 Patternmakers, Wood); max=3,988,140 (31-1120 Home Health and Personal Care Aides). 99% threshold leaves a 1% (~8 row) buffer for future suppression while detecting catastrophic regression. |
| RAW-OEWS-014 | P0 | G2 — no upper bound on wage values | Positive-direction twin of RAW-OEWS-011. The BLS top-code floor of $239,200 is a published methodology constant — every percentile field is bounded above by it. A x1000 parser bug would preserve monotonicity (RAW-OEWS-005) and would survive the spot checks (RAW-OEWS-008/009 cover only 2 of 831 SOCs). Mean field bounded empirically at $500K (16% headroom above observed max). | PASS — 0/831 rows violate either ceiling. Max non-cap percentile = $235,750 (below $239,200 floor with $3,450 headroom); max mean = $450,810 for 29-1243 Pediatric Surgeons (below $500K ceiling with $49,190 headroom). Top-3 means: Pediatric Surgeons $450,810, Cardiologists $432,490, Surgeons All Other $371,280. |
| RAW-OEWS-015 | P0 | G3 — partial summary-group leakage would slip through the row-count band | Detailed-only filter regression detector. The ingestor filters on `OCC_GROUP == 'detailed'` (`src/raw/bls_oews_ingestor.py` line 226). If that filter regresses (case-sensitivity, encoding, column rename), summary-group rows could leak into Bronze with populated wage fields and would silently join to nothing in OOH/O*NET. RAW-OEWS-001's [800, 900] band only catches catastrophic filter failure; partial leakage that lands inside the band would pass undetected. SOC 2018 reserves `XX-0000`, `XX-X000`, `XX-XX00` for major/minor/broad rollups respectively. | PASS — 0/831 rows match the summary-group regex. First 5 SOC codes confirm detailed grain: 11-1011, 11-1021, 11-1031, 11-2011, 11-2021 (all have non-zero last two digits). |

### Gate Status

- **P0 Gate: PASS** — All 14 Bronze P0 rules (10 original + 1 post-chaos + 3 post-auditor) passed with zero violations against the full 831-row real Iceberg dataset.
- **P1 Rules:** 1/1 passed (RAW-OEWS-012, capped-population drift detector — observed 45, window [5, 80]).
- **Silver / Gold gates:** DEFERRED — cannot be evaluated until Silver and Gold dispatches run.

### Verdict

**ALL_PASSED (Bronze)** — `bronze.bls_oews` is clean and ready to promote to Silver. No P0 failures, no P1 failures, no rule calibration issues, no escalation needed. The post-adversarial-auditor rule additions (RAW-OEWS-013, 014, 015 — all P0) are green on first execution, confirming auditor gaps G1, G2, and G3 are now structurally closed without false positives on real data. Bronze rule coverage now spans:
- **Volume:** row count band (RAW-OEWS-001), capped-population drift (RAW-OEWS-012)
- **Validity:** SOC format (RAW-OEWS-002), spot checks (RAW-OEWS-008, 009), wage non-negativity (RAW-OEWS-011), wage upper bounds (RAW-OEWS-014), employment non-negativity + completeness (RAW-OEWS-013)
- **Uniqueness:** SOC dedup grain (RAW-OEWS-003)
- **Completeness:** wage median non-null (RAW-OEWS-004), occupation title non-null (RAW-OEWS-010)
- **Consistency:** percentile monotonicity (RAW-OEWS-005), wage_capped biconditional (RAW-OEWS-006, 007), detailed-only filter (RAW-OEWS-015)

Spec workflow may proceed to the Silver dispatch.

### Operational Notes

- The `dq_runner run` command continued to emit the non-fatal warning: `Failed to sync DQ results to governance DB ... pyarrow.lib.ArrowInvalid: Column 'category' is declared non-nullable but contains nulls`. This is the same known issue in the governance metadata write path observed on prior runs (rule definitions in this file have no `category` populated). It does NOT affect rule execution, the JSON results file, or the P0 gate verdict — all 15 rules executed successfully against the live Iceberg table and the results were written to `governance/dq-results/raw-ingest-bls-oews-20260507T033237Z.json`. Flagged for the framework maintainer; safe to ignore for this scorecard.
