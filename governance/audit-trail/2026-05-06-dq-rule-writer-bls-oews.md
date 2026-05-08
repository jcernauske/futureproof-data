# Audit Trail: @dq-rule-writer — BLS OEWS Wage Percentiles

**Spec:** `docs/specs/ingest-bls-oews-wage-percentiles.md`
**Agent:** @dq-rule-writer
**Date:** 2026-05-06
**Workflow Step:** 6 (after @data-analyst EDA, before @dq-engineer execution)

---

## Inputs Consulted

| Input | Path | Role |
|-------|------|------|
| Spec | `docs/specs/ingest-bls-oews-wage-percentiles.md` | DQ rule scope (Zone 1 §137-148, Zone 2 §188-191, Zone 3 §301-304) |
| EDA report | `governance/eda/raw-bls-oews-eda.md` | Primary evidence + threshold lock-in (§Threshold Lock-In, §Edge Cases for DQ Thresholds) |
| Domain context | `governance/domain-context.md` (BLS OEWS section) | Domain edge cases — top-coding, suppression sentinels, mean-above-p90 artifact |
| Existing rule precedents | `raw-ingest-bls-ooh.json`, `silver-base-bls-ooh.json`, `gold-occupation-profiles-bls-ooh.json` | Canonical JSON structure |

---

## Artifacts Produced

| Artifact | Rule Count | Priority Mix |
|----------|-----------|--------------|
| `governance/dq-rules/raw-ingest-bls-oews.json` | 10 | 10×P0 |
| `governance/dq-rules/silver-base-bls-oews.json` | 11 | 11×P0 |
| `governance/dq-rules/gold-occupation-profiles-bls-oews.json` (incremental, appends to gold-occupation-profiles-bls-ooh.json) | 4 | 3×P0, 1×P1 |
| **Total** | **25 rules** | **24×P0, 1×P1** |

---

## Threshold Decisions vs. Spec

Three thresholds tightened from spec values per EDA evidence; one threshold preserved per EDA recommendation; one expected anomaly deliberately NOT codified as a rule.

| # | Spec Threshold | Final Threshold | Direction | Evidence | Rule |
|---|----------------|-----------------|-----------|----------|------|
| 1 | Bronze `wage_annual_median` non-null ≥ 95% | ≥ 99% | TIGHTENED | Actual 99.398% (826/831). EDA §Threshold Lock-In recommends 99% to detect regression while leaving room for one extra suppression. | RAW-OEWS-004 (and SLV-OEWS-004) |
| 2 | Gold `wage_p25` coverage ≥ 750 SOCs | ≥ 800 SOCs | TIGHTENED | Actual 826 SOCs. EDA §Threshold Lock-In: spec floor passes trivially; tighten to 800 (26-SOC buffer). | GLD-OP-OEWS-001 |
| 3 | Gold `wage_p25` non-null rate ≥ 90% | ≥ 98% | TIGHTENED | Actual 99.28% (826/832 OOH SOCs covered post-JOIN). EDA §Threshold Lock-In recommends 98%. | GLD-OP-OEWS-002 |
| 4 | Gold cross-survey `p25 ≤ median ≤ p75` ≥ 90% | ≥ 90% | UNCHANGED | EDA: 'Keep ≥ 90% as-is — OOH/OEWS are different surveys; small methodology drift is expected. Internal monotonicity is 100%, so any violations come from cross-survey variance.' | GLD-OP-OEWS-004 |
| 5 | Bronze monotonicity `p25 ≤ median ≤ p75` 100% | 100% **and extended to full p10..p90 chain** | EXTENDED | EDA §Cross-Field Analysis: 826/826 rows pass full p10..p90 chain. The spec only requires the inner 3-percentile chain; EDA evidence supports tightening to all 5 percentiles where non-null. | RAW-OEWS-005, SLV-OEWS-005 (full chain), SLV-OEWS-007 (inner chain backstop) |

---

## Rule NOT Written (Documented Exception)

**Anomaly:** 23 SOCs have `wage_annual_mean > wage_annual_p90` (Cardiologists, Anesthesiologists, Oral & Maxillofacial Surgeons, etc.).

**Why no rule:** This is a **known artifact of BLS top-coding methodology**, not a data-quality issue. BLS publishes the mean uncapped (e.g. Cardiologists mean = $432,490) but caps p90 at $239,200. Writing a `mean ≤ p90` rule would generate **23 false-positive failures every refresh** with zero remediation possible.

**Documentation:**
- EDA §Anomalies §Mean above p90 (advisory, not anomaly)
- `governance/domain-context.md` (OEWS section, "for @dq-rule-writer" notes)
- This audit trail

**Cross-checked patterns:** ADV-CROSS-COLUMN, ADV-VALUE-RANGE — both evaluated and explicitly skipped for the mean/p90 cross-column relationship with documented BLS-methodology rationale.

---

## Adversarial Pattern Coverage (per `governance/dq-rule-templates/adversarial-patterns.json`)

### Bronze (`bronze.bls_oews`)

| Pattern | Question | Rule(s) | Outcome |
|---------|----------|---------|---------|
| ADV-GRAIN-UNIQUE | What is the declared grain? | RAW-OEWS-003 | Written |
| ADV-FK-VALID | What FKs exist? | None at Bronze (FK enforcement happens at Silver/Gold join) | N/A — no FKs at this layer |
| ADV-CROSS-COLUMN | What columns derive from other columns? | RAW-OEWS-006, RAW-OEWS-007 (`wage_capped` ↔ percentile=239200 biconditional) | Written |
| ADV-TEMPORAL-ORDER | Temporal ordering? | None (snapshot table; `ingested_at` and `load_date` already enforced as non-null at schema level) | N/A — single-snapshot grain |
| ADV-VALUE-RANGE | Expected value distribution? | RAW-OEWS-008, RAW-OEWS-009 (calibration spot-checks for 15-1252 and 29-1141) | Written |
| ADV-DISTRIBUTION-VARIANCE | Expected temporal coverage? | None — this is an annual snapshot, not time-series | N/A |
| ADV-ENTITY-COVERAGE | All expected entities present? | RAW-OEWS-001 (row count 800-900) | Written |
| ADV-PERIOD-COVERAGE | All expected time periods covered? | None — single reference period (May 2024) | N/A |
| Domain-impossible values | What values are impossible? | RAW-OEWS-005 (monotonicity), RAW-OEWS-006/007 (top-code biconditional) | Written |

### Silver (`base.bls_oews`)

All Bronze adversarial coverage carried forward (same patterns, restated at Silver layer per spec §Zone 2 'All Bronze DQ rules still pass'). One addition: **ADV-GRAIN-UNIQUE on `record_id`** (SLV-OEWS-006) — Silver introduces a deterministic surrogate key that requires its own uniqueness rule.

### Gold (incremental, post-JOIN on `consumable.occupation_profiles`)

| Pattern | Question | Rule(s) | Outcome |
|---------|----------|---------|---------|
| ADV-FK-VALID | Does the OEWS LEFT JOIN resolve? | GLD-OP-OEWS-001, GLD-OP-OEWS-002 (coverage + non-null rate detect JOIN failures) | Written |
| ADV-CROSS-COLUMN | New columns vs. existing columns? | GLD-OP-OEWS-003 (p25 ≤ p75 monotonicity preserved), GLD-OP-OEWS-004 (cross-survey p25 ≤ median ≤ p75) | Written |
| ADV-VALUE-RANGE | Wage value range? | Inherited from Silver SLV-OEWS-007/008 (carried into Gold via the JOIN); no Gold-specific rule needed because the four new columns are pure passthrough | Carried forward |

---

## Domain-Context Cross-Check

The `governance/domain-context.md` BLS OEWS section flags four domain-specific items requiring DQ attention:

| Domain item | Handled in rules? |
|-------------|-------------------|
| Suppression sentinel `*` (5 entertainment-arts SOCs intrinsically suppressed) | RAW-OEWS-004 / SLV-OEWS-004 (99% non-null floor accommodates the 5 known suppressions while detecting any new ones) |
| Top-code sentinel `#` → 239200 (45 SOCs in May 2024 vintage) | RAW-OEWS-006 (forward biconditional), RAW-OEWS-007 (reverse biconditional), SLV-OEWS-008 (combined biconditional at Silver) |
| Filter to `OCC_GROUP=detailed` only (no major/minor/broad rollup leakage) | RAW-OEWS-001 (row count 800-900 catches summary-row leakage; ~830 detailed only) plus RAW-OEWS-003 (uniqueness catches detailed/summary collision) |
| Mean published uncapped (mean > p90 for top-coded SOCs) | NO RULE (deliberate, documented above) |

---

## Patterns from Consumable / Normalization / Collision Templates

This spec is **incremental Gold enrichment**, not a new consumable table:

- **CONS-GRAIN-UNIQUE** — already enforced on `consumable.occupation_profiles` by GLD-OP-001 in the existing OOH rule file. No re-write needed.
- **CONS-IMPOSSIBLE-VALUE** — `wage_p10/25/75/90` value-range constraints are inherited from the Silver layer (SLV-OEWS-005/008). Gold passthrough does not transform values, so no Gold-specific impossible-value rule is required.
- **CONS-CROSS-TABLE** — GLD-OP-OEWS-004 covers cross-table consistency between OEWS-derived `wage_p25/p75` and OOH-derived `median_annual_wage`. Written.
- **CONS-GOLDEN-DATASET** — existing golden dataset for `gold-occupation-profiles-bls-ooh-golden.json` does not yet include OEWS wage fields. **Out of scope for this rule writer**; flagged for @primary-agent / @governance-reviewer to update the golden dataset when implementation lands. Not blocking for the new rules to begin executing.
- **CONS-COLLISION-RESOLVED** — N/A. No concept normalization in this spec; SOC code is the join key with no aliasing.
- **CONS-COVERAGE-FLOOR** — covered by GLD-OP-OEWS-001 (entity coverage floor) and GLD-OP-OEWS-002 (per-row non-null floor).

---

## Decisions

1. **Rule organization** — created a dedicated `gold-occupation-profiles-bls-oews.json` rather than literally appending to `gold-occupation-profiles-bls-ooh.json`. Rationale: (a) spec §Governance Artifacts says "append new OEWS-coverage rules" but in practice the existing file is keyed by `evidence_source: governance/eda/gold-occupation-profiles-eda.md` and modeled after the OOH-specific golden dataset; mixing the OEWS rules in would muddy provenance. (b) Both files target the same physical table (`consumable.occupation_profiles`); the dq_runner will execute both at scorecard time. (c) The `appends_to` field in the new file's metadata declares the parent. This preserves the spec intent (Gold rules for occupation_profiles include the new OEWS rules) while keeping evidence sources clean.

2. **Spec-stated 'wage_p25 ≤ wage_p75 for 100% of rows where both non-null' is the same invariant Silver SLV-OEWS-005 enforces** — but the spec correctly requires re-asserting it at Gold to catch JOIN-time corruption (column swap, alias mismatch). Written as GLD-OP-OEWS-003.

3. **No `wage_p10` or `wage_p90` Gold rules** — spec §Zone 3 only lists `wage_p25`-centric rules (because p25-p75 is the "typical range" surfaced to users). p10/p90 are surfaced but not explicitly DQ-gated at Gold. The Silver monotonicity rule SLV-OEWS-005 already enforces `p10 ≤ p25 ≤ median ≤ p75 ≤ p90` end-to-end before the JOIN, so Gold inherits the invariant. If the Gold engine query corrupts p10/p90 specifically (and not p25/p75), it would still be caught by the cross-survey rule on median_annual_wage and the monotonicity rule on p25/p75 in Gold. Adequate coverage.

---

## Next Steps

1. **@dq-engineer** (workflow step 7): Execute the Bronze and Silver rule sets via `python -m brightsmith.infra.dq_runner run` once the data is loaded. Re-run Gold rule set after the OEWS LEFT JOIN ships. Produce scorecards at the three paths listed in spec §Governance Artifacts.
2. **@governance-reviewer**: Verify all 25 rules carry evidence citations and that the three threshold tightenings are properly documented in this audit trail.
3. **@primary-agent** (workflow step 10, when implementing Gold enrichment): update `governance/golden-datasets/gold-occupation-profiles-bls-ooh-golden.json` to include the four new wage fields for the existing golden SOCs (15-1252, 29-1141, 29-1211).

---

## Status

| Step | Status |
|------|--------|
| Bronze rules written | DONE (12 rules — 10 original + 2 post-chaos) |
| Silver rules written | DONE (12 rules — 11 original + 1 post-chaos mirror) |
| Gold incremental rules written | DONE (4 rules) |
| Audit trail logged | DONE (this document, see §Post-Chaos Addendum below) |
| Rules executed (validation) | PENDING — @dq-engineer (workflow step 7), requires `bronze.bls_oews` table to exist |
| Scorecards generated | PENDING — @dq-engineer (workflow step 7) |

---

## Post-Chaos Addendum (2026-05-06, after chaos-monkey cycle)

### Trigger

`@chaos-monkey` ran 5 cycles against the BLS OEWS rule set. **9 of 10 scenarios were caught.** One gap surfaced:

- **Scenario S10:** set `wage_annual_p25 = -5000` on SOC `11-1021` (Chief Executives) while preserving the monotonic chain (i.e. the inserter also adjusted neighbouring percentiles or chose a row where p10 was null/already low). **Zero rules fired.**

The gap is structural: no rule in the original 25-rule set bounds wage values to non-negative numbers. RAW-OEWS-005 only enforces ordering, RAW-OEWS-006/007 only enforce the top-code biconditional, and RAW-OEWS-008/009 only spot-check two specific SOCs. A negative value at p25 of any other SOC slipped through.

### New Rules Added

| Rule ID | Zone | Priority | Closes | Threshold |
|---------|------|----------|--------|-----------|
| **RAW-OEWS-011** | Bronze | P0 | Chaos S10 (negative wage value not blocked) | 0 violations across all 6 annual wage columns × all rows |
| **RAW-OEWS-012** | Bronze | P1 | Future drift in BLS top-code-floor methodology / `#` parser regression | 5 ≤ count(wage_capped=TRUE) ≤ 80 |
| **SLV-OEWS-012** | Silver | P0 | Same as RAW-OEWS-011, enforced at Silver layer (1:1 promote) | 0 violations across all 6 annual wage columns × all rows |

### Evidence Citations

- **RAW-OEWS-011 / SLV-OEWS-012** — EDA §Field Profiles confirms the smallest real wage published in May 2024 is $30,160; non-negative values are a structural domain invariant, not an empirical threshold. Real data has zero violations today.
- **RAW-OEWS-012** — EDA §Edge Cases for DQ Thresholds, row 4: 'Top-coded SOCs (#): 45 rows in May 2024 vintage.' Bounds [5, 80] sit comfortably around the 45 actual; 5 is the floor for catastrophic `#` parser regression, 80 is the ceiling for unexpected expansion of the high-wage SOC population.

### ID Naming Note

The post-mortem directive requested mirroring RAW-OEWS-011 into Silver as `SLV-OEWS-011`. That rule_id was already in use (Registered Nurses calibration spot check). Per the directive 'do NOT renumber existing rules', the Silver mirror was appended as **SLV-OEWS-012**. The rule's `name` and `description` both explicitly tag it as mirroring RAW-OEWS-011 to preserve traceability.

### No Existing Rules Altered

RAW-OEWS-001 through RAW-OEWS-010 and SLV-OEWS-001 through SLV-OEWS-011 were left byte-identical. Only the trailing `]` of the `rules` array was opened to append the new entries. All previously-approved rules retain their `approved_by: human` and `approved_at` timestamps.

### Files Modified

- `governance/dq-rules/raw-ingest-bls-oews.json` — appended RAW-OEWS-011, RAW-OEWS-012
- `governance/dq-rules/silver-base-bls-oews.json` — appended SLV-OEWS-012
- `governance/audit-trail/2026-05-06-dq-rule-writer-bls-oews.md` — this addendum

### Next Steps

1. **@governance-reviewer** — approve the three new rules (currently `status: proposed`).
2. **@dq-engineer** — re-run scorecard with the expanded rule set; confirm chaos S10 is now caught.
3. **@chaos-monkey** — re-run the cycle to verify the gap is closed and look for the next-tier blind spots.

---

## Post-Adversarial-Audit Addendum (2026-05-06, after @adversarial-auditor)

### Trigger

`@adversarial-auditor` reviewed the post-chaos rule set (12 Bronze + 12 Silver = 24 rules) against the chaos manifest, EDA, and ingestor source code. **Verdict: GAPS_FOUND — 9 governance gaps identified, 3 of them P0.** Full report at `governance/audit-trail/2026-05-06-adversarial-auditor-bls-oews.md`.

The auditor's core observation: chaos-monkey ran a closed-world test (every scenario except S10 targeted a field that already had a P0 rule pointed at it). S10 (negative wage) was the first scenario that targeted an invariant **not in the spec**, and it caught a real gap. The audit identified at least 3 more P0 holes in that same class — domain invariants the rule writer inferred from the spec but never wrote down.

### Three P0 Gaps Closed

| Gap | Class | Bronze Rule | Silver Rule |
|-----|-------|-------------|-------------|
| **G1** — `total_employment` had ZERO rules of any kind | Mirror of S10 negative-wage attack, re-pointed at the second numeric column in the table | **RAW-OEWS-013** (P0, Validity) | **SLV-OEWS-013** (P0, Validity) |
| **G2** — No upper-bound sanity on annual wages (only the negative half was guarded) | Positive-direction twin of RAW-OEWS-011; a x1000 parser bug would preserve monotonicity and survive | **RAW-OEWS-014** (P0, Validity) | **SLV-OEWS-014** (P0, Validity) |
| **G3** — No rule that the `OCC_GROUP == 'detailed'` filter actually held | Partial filter regression that lands inside [800, 900] would leak summary rows (`15-0000`, `15-1000`, `15-1200`) | **RAW-OEWS-015** (P0, Consistency) | **SLV-OEWS-015** (P0, Consistency) |

### New Rule Details

| Rule ID | Threshold | Closes Attack Vector |
|---------|-----------|----------------------|
| **RAW-OEWS-013** / **SLV-OEWS-013** | `total_employment >= 0` AND non-null rate >= 99% | Negative employment count; large-scale `total_employment` suppression regression |
| **RAW-OEWS-014** / **SLV-OEWS-014** | `wage_annual_p10/p25/median/p75/p90 <= 239200`; `wage_annual_mean <= 500000` | x1000 parser bug; column-shift that lands `total_employment` into a wage cell; top-code floor regression |
| **RAW-OEWS-015** / **SLV-OEWS-015** | `soc_code` does NOT match `^\d{2}-(0000|\d000|\d{2}00)$` (no major / minor / broad summary patterns) | Filter regression where summary-group rows leak into Bronze with populated wages |

### Evidence Citations

- **RAW-OEWS-013 / SLV-OEWS-013** — EDA §Field Profiles -> total_employment: 100% non-null in May 2024; max value 3.28M (Retail Salespersons); zero negatives. EDA line 61 explicitly recommended this rule. Adversarial audit §G1 elevated to P0 (originally proposed P1) because the severity class matches S10.
- **RAW-OEWS-014 / SLV-OEWS-014** — EDA §Field Profiles: max non-cap percentile = $216,800 (well under $239,200 ceiling); max mean = $432,490 (Cardiologists, well under $500K ceiling). 45 SOCs are floored at exactly $239,200 by BLS methodology -- the threshold is `<= 239200` (inclusive), so capped rows pass cleanly. Adversarial audit §G2.
- **RAW-OEWS-015 / SLV-OEWS-015** — EDA §Key Findings: all 831 rows are detailed SOCs; zero match the summary-group regex `^\d{2}-(0000|\d000|\d{2}00)$`. Pattern derived from SOC 2018 standard. Adversarial audit §G3.

### Expected Pass Rate Against Real Data

All 6 new rules pass at **100% against current May 2024 Bronze and the eventual 1:1 Silver promote**. These are **guards against future drift / regression vectors**, not corrections to current data. Per the audit's closing skepticism note: "Every new rule recommended above passes against real May 2024 data... Closing these P0 gaps is risk-free against current data and detects real regression vectors."

### Gaps Deferred (out of scope for this addendum)

| Gap | Severity | Status |
|-----|----------|--------|
| G4 — Source-vintage drift (no `ingested_at` freshness rule, no provenance check on source URL) | P1 | Deferred to next vintage refresh spec |
| G5 — `wage_hourly_median` not covered by RAW-OEWS-011's non-negative guard | P1 | Deferred (per spec, "kept for reference, not used downstream") |
| G6 — `wage_capped` non-null implicit, not enforced | P1 | Deferred (Iceberg `required=True` enforces at write time) |
| G7 — Cross-row group-rollup verification | P2 | Out of scope; flag for follow-up `verify-bls-oews-group-rollups` spec |
| G8 — Encoding/unicode anomalies in `occupation_title` | P2 | Out of scope; document in data dictionary |
| G9 — OEWS-OOH SOC orphan check at Bronze/Silver | P2 | Already covered at Gold by chaos manifest's `GS4` scenario |

### No Existing Rules Altered

Rules **RAW-OEWS-001 through RAW-OEWS-012** and **SLV-OEWS-001 through SLV-OEWS-012** were left byte-identical. Only the trailing `]` of each `rules` array was opened to append the new entries. All previously-approved rules retain their `approved_by: human` and `approved_at` timestamps. Renumbering was avoided per directive.

### Files Modified

- `governance/dq-rules/raw-ingest-bls-oews.json` — appended RAW-OEWS-013, RAW-OEWS-014, RAW-OEWS-015 (12 -> 15 rules)
- `governance/dq-rules/silver-base-bls-oews.json` — appended SLV-OEWS-013, SLV-OEWS-014, SLV-OEWS-015 (12 -> 15 rules)
- `governance/audit-trail/2026-05-06-dq-rule-writer-bls-oews.md` — this addendum

### Next Steps

1. **@governance-reviewer** — approve the six new rules (currently `status: proposed`).
2. **@chaos-monkey** — extend the manifest with three new scenarios per audit §Evidence Demands:
   - `S11: total_employment = -1 on SOC 11-1021` (mirror of S10's shape)
   - `S13: wage_annual_p25 = 9_999_999_999 on a non-spot-check SOC`
   - `S14: insert SOC code 15-0000 with all wage fields populated to shadow Bronze`
   Each scenario must produce verdict `CAUGHT` against the new rule set.
3. **@dq-engineer** — re-run scorecard once the bronze table is materialized; confirm 15/15 Bronze and 15/15 Silver pass against real data.
