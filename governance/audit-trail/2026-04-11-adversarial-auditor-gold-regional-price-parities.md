# Audit Trail — @adversarial-auditor — gold-regional-price-parities

**Date:** 2026-04-11
**Agent:** @adversarial-auditor
**Spec:** `docs/specs/gold-regional-price-parities.md`
**Target table:** `consumable.regional_price_parities`
**Session purpose:** Complementary skeptical audit of Gold artifacts for
hallucination, governance theater, and hidden problems the chaos monkey
cannot find. Runs at workflow step 13/18 after @chaos-monkey, before
@lineage-tracker / @doc-generator post-review and @staff-engineer sign-off.

---

## Actions taken

1. Read the full spec, physical model, transformer module, cost_tier
   module, promote runner, chaos report, EDA report, and 730-line test
   file end-to-end.
2. Loaded the authoritative DQ rules JSON (55 rules) and inspected the
   SQL of the load-bearing rules: GLD-RPP-023 (classification
   correctness), GLD-RPP-024 (TN boundary witness), GLD-RPP-026/028/030/032
   (adjusted_Nk derivation purity), GLD-RPP-036/037 (verification_status
   count + allow-list), GLD-RPP-043 (cross-zone passthrough, production_only),
   GLD-RPP-044/050 (CA/IA spot checks), GLD-RPP-021/022 (cost_tier
   non-null + IN-list), GLD-RPP-016–020 (rpp / multiplier / inverse
   invariant).
3. Loaded the data contract and cross-checked per-column `dq_rules`
   arrays against the rule SQL for 9 columns (record_id, state_fips,
   state_name, rpp_all_items, purchasing_power_multiplier, cost_tier,
   adjusted_50k, verification_status, data_year). Zero drift cases.
4. Queried the live `consumable.regional_price_parities` table via
   `brightsmith.infra.iceberg_setup.get_catalog` + `read_with_duckdb`:
   - row count = 51
   - columns = 15 in the spec-declared order
   - cost_tier distribution = `{very_high:4, high:8, average:13, low:11,
     very_low:15}` — **bit-identical to the EDA projection**
   - verification_status = `{bea_official:8, estimate:43}`
   - bea_official state_fips set = `['05','06','11','15','19','28','34','40']`
     — exact allow-list
   - TN (fips '47') rpp=91.0, cost_tier='low' — left-closed witness holds
   - All 8 BEA spot checks match spec values to zero delta.
5. Audited banker's rounding: exhaustively compared Python `round(N × ppm,
   2)` against `Decimal.quantize('0.01', ROUND_HALF_UP)` for every
   (state, N) pair across all 51 × 4 = 204 adjusted_Nk values. **Zero
   divergences** on the current vintage. Risk is documented in the
   transformer docstring but not exercisable on today's data.
6. Probed `data/catalog/catalog.db` directly via sqlite3:
   - Single `regional_price_parities` row under `catalog_name='brightsmith'`.
   - RPP stack (bronze, base, consumable) all under `brightsmith`.
   - Legacy `futureproof-data` catalog_name still exists on 17 other rows
     from prior specs — out of scope for this audit but worth flagging
     because it is the exact failure mode the promote runner's
     defensive commentary was written to prevent.
7. Ran `scripts/promote_regional_price_parities.py` end-to-end. Exit 0,
   idempotent: `rows_read=51, rows_derived=51, promoted=0, skipped_dedup=51`.
8. Ran `uv run pytest tests/gold/test_regional_price_parities_transformer.py -q`
   → `59 passed in 0.84s`.
9. Verified `scripts/rebuild_all.py` contains a dedicated
   `transform_gold_regional_price_parities()` step (lines 317–343) that
   subprocesses the promote script. The step is appended to the rebuild
   sequence at line 407 after Silver is complete.
10. Inspected `governance/lineage/gold-regional-price-parities-20260411.json`:
    single COMPLETE event, `producer: null`, inputs include
    `gold._cost_tier` (a source module, not a dataset). Minor OpenLineage
    shape issues, no correctness impact.
11. Grepped for secrets / tokens / credentials across all files matching
    `*regional_price_parities*`. Zero matches.
12. **Cross-checked the physical model's DQ-rule traceability table
    (lines 486–514) against the authoritative rules JSON.** Found
    substantial documentation drift: the table uses an old 27-rule
    numbering (GLD-RPP-001..027) while the authoritative file has 55
    rules at completely different IDs. The behavior is correct; the
    document is misleading.
13. Enumerated glossary entries BT-106 (Cost Tier) and BT-107 (Adjusted
    Salary). Both definitions match the spec, the code, the DQ rules, and
    the contract with **no drift**. Breakpoints stated exactly as
    `108/103/97/91` with left-closed semantics.
14. Loaded `governance/dq-results/gold-regional-price-parities-20260411T022936Z.json`
    for run `ddabd852`. Confirmed `rules_total=55, rules_passed=55,
    rules_failed=0, rules_errored=0, p0_passed=true`.
15. Listed `governance/approvals/`: only `pre-review` exists.
    Post-review and staff-review are still ahead in the workflow.

---

## Findings summary

- **HIGH-1 (1 finding):** Rule-ID drift between
  `governance/models/gold-regional-price-parities-physical.md` (lines
  486–514) and `governance/dq-rules/gold-regional-price-parities.json`.
  Documentation-only but regulator-unfriendly. **Must fix before staff
  review.**
- **MEDIUM (4 findings):** Missing post/staff approvals (expected at
  workflow step 13); legacy catalog-name drift from other specs;
  unverified P0/P1 split claim; chaos injection-ordering gaps.
- **LOW (5 findings):** Cross-zone rules never exercised in chaos;
  lineage `producer` null + non-dataset "input"; banker's-rounding risk
  not exercisable on current vintage; no try/finally on duckdb.connect;
  schema ↔ SALARY_ANCHORS loose coupling.
- **INFO (3 findings):** Test guardrails look tautology-adjacent but
  aren't; test fixture distribution intentionally decoupled from live;
  no negative-path transform() test.

**Zero P0/Critical defects.**

---

## Verdict

**PASS with conditions.** Adversarial-auditor gate conditionally passes
pending:

1. Rewrite the physical model's rule-ID traceability table against the
   authoritative 55-rule numbering.
2. Produce post-review and staff-review approvals.
3. Cross-verify the contract's `p0_count / p1_count` totals.

The chaos-monkey "no DQ rule gaps" conclusion holds — the HIGH-1 finding
is documentation drift that chaos cannot and should not find.

Full deliverable:
`governance/adversarial-audits/gold-regional-price-parities.md`.

---

## Artifacts produced

- `governance/adversarial-audits/gold-regional-price-parities.md` (this
  audit report with 13 numbered risks, evidence, control grades, and
  recommendations).
- `governance/audit-trail/2026-04-11-adversarial-auditor-gold-regional-price-parities.md`
  (this audit-trail entry).

## Artifacts read but not modified

- `docs/specs/gold-regional-price-parities.md`
- `src/gold/regional_price_parities_transformer.py`
- `src/gold/_cost_tier.py`
- `scripts/promote_regional_price_parities.py`
- `scripts/rebuild_all.py`
- `tests/gold/test_regional_price_parities_transformer.py`
- `governance/eda/gold-regional-price-parities-eda.md`
- `governance/dq-rules/gold-regional-price-parities.json`
- `governance/dq-results/gold-regional-price-parities-20260411T022936Z.json`
- `governance/chaos-reports/gold-regional-price-parities-chaos.md`
- `governance/data-contracts/consumable-regional-price-parities.yaml`
- `governance/lineage/gold-regional-price-parities-20260411.json`
- `governance/models/gold-regional-price-parities-physical.md`
- `governance/business-glossary.json` (BT-106, BT-107 entries)
- `governance/approvals/gold-regional-price-parities-pre-review.md`
- `data/catalog/catalog.db` (read-only sqlite queries)
- `data/gold/iceberg_warehouse/consumable/regional_price_parities/*` (via
  pyiceberg read path)
