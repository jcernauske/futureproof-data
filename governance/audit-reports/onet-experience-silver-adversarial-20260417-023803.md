# Silver Adversarial Audit — base.onet_experience_profiles

- **Spec:** `docs/specs/onet-experience-requirements.md`
- **Zone:** Silver (normalize + model)
- **Target:** `base.onet_experience_profiles` (765 rows, Iceberg snapshot `5745163851101673330`)
- **Transformer:** `src/silver/onet_experience_transformer.py`
- **Audit type:** Light-weight verification (chaos reported 0 gaps)
- **Auditor:** adversarial-auditor
- **Timestamp:** 2026-04-17 02:38 UTC

## Method

Chaos runner at `scripts/silver_onet_experience_chaos_runner.py` reported 0 gaps over 5×9=45 probes against real Bronze. This audit independently re-examines the work rather than re-probing. Four activities:

1. Read 3 of 9 chaos scenarios (S1 bimodal, S2 tie-at-50%, S6 FK-missing) — independently reason about whether the mutation genuinely covers the claimed dimension.
2. Static read of `src/silver/onet_experience_transformer.py` looking for correctness concerns not already covered.
3. Cross-reference spec §Test Matrix (7 cases) against `tests/silver/test_onet_experience_transformer.py`.
4. Spot-check each of the 10 Silver DQ rules by running its SQL against the real Iceberg parquet directly and reasoning about its false-positive / false-negative potential.

## Chaos coverage spot-check (3 of 9 scenarios)

| Scenario | Coverage assessment |
|----------|---------------------|
| S1 bimodal_flips_tier (49/49 at cat1/cat11 + 2% spread) | Genuine. The mutation is a real adversarial distribution the transformer must survive. The delta (cat9→cat6, mid→early) is properly attributed via SLV-ONET-EXP-009 spot-check rule. |
| S2 boundary_tie_50_50 (50% at cat1 + 50% at cat2) | Genuine — tests the approved tie-break rule. Deterministically lands at cat1 per spec §Open Decisions Decision 1, and the resulting tier flip (mid→entry) trips rule SLV-ONET-EXP-009. |
| S6 missing_bls_soc_in_occupations (rewrites 15-1252.00 → 99-9999.00) | Genuine. Confirmed the FK-filter branch in `_aggregate_to_bls` (line 352) drops the SOC silently per the LEFT-JOIN intent. Baseline count 765 → 764 when target disappears. |

Assessment: **the three scenarios I read are real probes, not cosmetic**. The chaos runner's information-barrier claim ("rules loaded opaquely") is enforced by code (lines 141-157).

## Findings

### GAP 1 — HIGH — "Senior" tier is a razor-thin, single-row population

Rule `SLV-ONET-EXP-007` ("all 4 tiers represented") currently passes because the Silver table has exactly ONE row in the `senior` tier: `11-1011` (Chief Executives), `experience_years_typical = 8.5`. The senior/mid threshold is 8.0 years. The margin is **0.5 years**.

The value 8.5 is the unweighted average of two O*NET details for 11-1011:
- `11-1011.00` weighted median = category 11 → 12 years
- `11-1011.03` weighted median = category 8 → 5 years
- Unweighted mean = (12 + 5) / 2 = 8.5 → `senior` (barely)

If O*NET's next annual release shifts 11-1011.03's RW distribution so its weighted median drops to category 7 (3 years), the average becomes (12+3)/2 = 7.5 → `mid`. Then:
- `SLV-ONET-EXP-008` ("11-1011 tier = senior") would FAIL (P0)
- `SLV-ONET-EXP-007` ("all 4 tiers represented") would FAIL (P1)

This is not a transformer correctness bug — it's a **calibration fragility** that chaos did not surface because all 9 chaos scenarios targeted `15-1252.00` (Software Developers), not the senior-tier canary.

**Evidence:** `governance/dq-results/silver-onet-experience-20260417-023011.json` shows `tier_distribution: senior=1` and the single senior row at 8.5 yr. No chaos scenario probes what happens if 11-1011 drifts tier.

### GAP 2 — MEDIUM — Test theater in `test_spot_check_11_1011_senior`

The unit test uses a synthesized distribution for `11-1011.00` only (cat7=9.69, cat8=5.87, cat9=15.09, cat10=1.11, cat11=68.24) and asserts `experience_years_typical == 12.0`. But the real Silver row has `experience_years_typical == 8.5` because real Bronze contains TWO details (`11-1011.00` and `11-1011.03`), not one.

The test passes for the tier label (`senior`) but the year value it asserts is **impossible to reach from real data**. A reader of the test suite would conclude "Chief Executives resolves to 12 years" — the actual answer is 8.5. The test doesn't cover the multi-detail aggregation path for this specific SOC with real-data inputs.

Rule `SLV-ONET-EXP-008` is tighter — it asserts only the tier, which matches real data — but the unit test creates a **misleading mental model** of what the transformer produces in production.

**Evidence:** `tests/silver/test_onet_experience_transformer.py:374-387`; compared against real Silver row `('11-1011', 9, 8.5, 'senior', 2, ...)`.

### GAP 3 — MEDIUM — DQ rule SLV-ONET-EXP-001 has a vacuous-pass risk

Rule 001 ("row count 720-810") uses SQL that wraps the count comparison in a subquery and returns a single-integer indicator with threshold `result = 0`. The rule runner at `scripts/silver_onet_experience_chaos_runner.py:150` handles `result = 0` thresholds like this:

```python
if len(res) == 0:
    return False, 0   # NO rows returned → treated as NOT violated
```

If a bug ever causes the CASE expression to return zero rows (e.g., the subquery errors silently in some DuckDB version and returns empty), this rule would spuriously PASS. The same risk applies to rule 007. The current `dq-results` JSON reports `actual_value: 0` for both 001 and 007, which is the "indicator" not the row count — a reviewer reading the JSON cannot distinguish "count is healthy" from "query returned empty." 

This is a tooling issue broader than this spec, but it's worth flagging here: the row-count rule's passing state reveals nothing about the actual row count. The `supplementary_stats.total_rows` field fortunately does record the real count (765), so the audit trail isn't blind — but the rule itself is information-poor.

**Evidence:** `governance/dq-rules/silver-onet-experience.json` SLV-ONET-EXP-001 SQL + `scripts/silver_onet_experience_chaos_runner.py:150-157`.

### No-gap confirmations (noting for the audit trail)

- **§Test Matrix 7-case coverage:** Every case has a dedicated unit test. Mapping verified:
  - Case 1 (empty distribution): `test_empty_distribution_case_skipped` + `test_all_zero_returns_none`
  - Case 2 (single category 100%): `test_single_category_100pct` + `test_single_category_at_cat_11`
  - Case 3 (all suppressed): `test_all_suppressed_still_produces_detail` + `test_all_suppressed_produces_row_with_flag`
  - Case 4 (tie at 50%): `test_tie_at_50pct_picks_lower` + `test_tie_at_50_picks_lower`
  - Case 5 (multi-detail aggregation): `test_multi_detail_aggregation`
  - Case 6 (missing source experience): belongs to Gold zone — not Silver scope
  - Case 7 (known-value spot checks): `test_spot_check_11_1011_senior`, `test_spot_check_15_1252_mid`, `test_spot_check_41_2031_bimodal_entry`
- **Record ID determinism & uniqueness:** 765 distinct `record_id`s, all prefixed `exp-`, no nulls.
- **Category→years midpoint integrity (n_details=1):** 0 mismatches across all 702 single-detail rows — the `CATEGORY_MIDPOINT_YEARS` map is applied correctly.
- **JSON distribution validity:** 0 invalid JSON rows; 0 rows with category-sum outside [95, 105].
- **Median-mode agreement:** 395 of 765 rows (52%) have median == mode; the rest are genuinely skewed distributions where these should differ (expected behavior).
- **Suppress-flag OR-logic:** 127 rows (17%) have `suppress_flag=True`. No DQ rule asserts count or content — acceptable per spec §CDE ("provenance flag only").
- **Negative `data_value` behavior:** Transformer doesn't guard against negative weights (would sum into the cumulative walk and could skew the median). **Not a gap for this spec** — Bronze rule validates `0 ≤ data_value ≤ 100`, so negatives can't reach Silver in practice.
- **Float precision at the 50% boundary:** Tested with `±1e-7` drift; the `_TIE_EPS = 1e-9` tolerance resolves correctly on both sides.

## Verdict

**GAPS FOUND (3)** — all 3 are non-blocking for Silver sign-off, but should be tracked:

1. **HIGH** — Senior tier is a single-row, 0.5-year-margin population. A trivial upstream change could silently break `SLV-ONET-EXP-007` (P1) and `SLV-ONET-EXP-008` (P0). Recommend either (a) adding a DQ rule that tolerates `senior >= 1` with an explicit "if zero senior, investigate 11-1011" hint, or (b) adding a chaos scenario that mutates 11-1011.03 to flip the senior-tier count to zero and verifying the rule catches it.
2. **MEDIUM** — `test_spot_check_11_1011_senior` uses synthesized single-detail input that produces 12.0 years; real data produces 8.5 years. The tier passes but the year assertion is test theater. Either rewrite the test to mirror real-data multi-detail input, or add a separate integration test that reads real Bronze and asserts the real-Silver 8.5-year outcome.
3. **MEDIUM** — Rules 001 and 007 use the `result = 0` indicator pattern, which can vacuously pass on an empty query result and leaves no audit-trail breadcrumb of the actual measured value in the rule-specific JSON entry. `supplementary_stats.total_rows` partially mitigates. Broader tooling concern — flag to `bs:dq-engineer`.

Gap 1 is the one a regulator would fixate on. The senior-tier rule passes today by a 0.5-year margin on a single occupation. That's not "verified" — that's "currently lucky."