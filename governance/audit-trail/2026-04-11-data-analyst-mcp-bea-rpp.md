# Audit Trail: @data-analyst — mcp-bea-rpp

**Date:** 2026-04-11
**Agent:** @data-analyst
**Spec:** `docs/specs/mcp-bea-rpp.md`
**Zone:** MCP (AI-Ready)
**Task:** Eval-set coverage + tool-response analysis for `get_regional_price_parity`
and `compare_purchasing_power`.

---

## Scope

This is an MCP-zone analysis. The MCP zone exposes existing Gold data without
transforming it, so there is no new data to profile. The analytical work is:

1. Confirm the eval set covers all 11 spec requirement categories.
2. Profile the distribution of eval cases (tool, state, edge-case buckets).
3. Re-verify the 8 BEA spot-check rows in the eval match the Gold table
   byte-for-byte.
4. Verify strict-mode behavior exhaustively: all 43 estimate rows refuse, all
   8 `bea_official` rows succeed.
5. Verify `compare_purchasing_power` arithmetic is byte-for-byte reproducible
   with the full-precision multipliers.
6. Identify untested input shapes / edge cases.

---

## Actions Taken

1. Read `docs/specs/mcp-bea-rpp.md`, `src/mcp_server/futureproof_server.py`,
   and the full eval set `data/ai_ready/eval/mcp-bea-rpp-eval.jsonl`.
2. Loaded the Gold parquet at
   `data/gold/iceberg_warehouse/consumable/regional_price_parities/data/
   00000-0-07edfd60-dda9-4d71-936a-0ea5bdb54bb6.parquet` directly with
   pyarrow and confirmed 51 rows, 8 `bea_official` / 43 `estimate`, single
   `data_year=2024`, 5 cost tiers, 4 census regions.
3. Classified every eval case by `case_id` prefix into 11 spec categories
   and counted coverage.
4. Verified byte-for-byte parity between every `verified-*` eval case and
   its Gold row across 12 fields.
5. Instantiated a live `FutureProofMCPServer` against the local Iceberg
   catalog (same technique as `scripts/dq_mcp_manual.py`) and ran every
   one of the 65 eval cases through the actual handler, comparing each
   response against the case's `verification_key`
   (dotted-path equality + `message_contains` substring match).
6. Ran an exhaustive strict-mode sweep: probed every one of the 51 states
   with `verified_only=true` to confirm the "8 succeed, 43 refuse"
   acceptance criterion without relying on the eval set's sample of 5
   refusals.
7. Reproduced `compare_purchasing_power` arithmetic for every success case
   by computing `round(salary * ppm, 2)` off the Gold row with the
   full-precision multipliers stored in the eval
   (CA=`0.9033423667570009`, IA=`1.1389521640091116`).
8. Probed 19 ad-hoc edge cases on `get_regional_price_parity` and 13 on
   `compare_purchasing_power` to surface input shapes the eval does not
   cover.

---

## Key Findings

- **All 65 eval cases pass against the live MCP server.** 0 failures, 0
  exceptions.
- **All 8 BEA spot-check rows match Gold byte-for-byte** across 12 fields
  (`state_name`, `state_abbr`, `state_fips`, `census_region`, `rpp_all_items`,
  full-precision `purchasing_power_multiplier`, `cost_tier`, the four
  `adjusted_Nk` values, `data_source==verification_status`, `data_year`).
- **All 11 spec requirement categories are covered at or above the minimum.**
  The spec asks for ≥ 50 mechanically verifiable cases; the eval delivers 65.
- **Strict mode is exhaustively correct.** The live sweep over all 51 states
  confirms: 8 `bea_official` succeed (AR, CA, DC, HI, IA, MS, NJ, OK), 43
  `estimate` refuse with a structured null, zero cross-contamination.
- **`compare_purchasing_power` arithmetic is byte-for-byte reproducible.** All
  7 success cases reproduce exactly using
  `round(salary * purchasing_power_multiplier, 2)` and the full-precision
  multipliers preserved in both the eval's `expected_output` and the live
  tool response. The canonical spec example (CA vs IA at $65K →
  `58717.25 vs 74031.89`) matches exactly. `difference_pct = 26.08` is
  invariant across all five salary levels (as expected — the ratio only
  depends on `ppm_b / ppm_a`).
- **No anomalies, no arithmetic discrepancies, no raised exceptions.**

---

## Coverage Summary

| Category (spec §Eval Set) | Required | Present |
|---|---|---|
| 1. All 8 BEA-verified states with full payloads | 8 | 8 |
| 2. Sample of estimated states (≥ 5) | 5 | 8 |
| 3. All 3 input forms (FIPS/USPS/name) for representative state | 3 | 3 (California) |
| 4. Case-insensitive input forms | ≥ 1 | 5 |
| 5. Strict-mode positive cases | ≥ 1 | 8 (all 8 BEA states) |
| 6. Strict-mode refusal cases | ≥ 1 | 5 (TX, NY, WA, FL, IL) |
| 7. Unknown-state rejection | ≥ 1 | 5 |
| 8. `compare_purchasing_power` success at common salary levels | 4 | 7 |
| 9. `compare_purchasing_power` salary validation | 4 | 7 |
| 10. `compare_purchasing_power` same-state rejection | ≥ 1 | 3 |
| 11. `compare_purchasing_power` strict mixed-provenance refusal | ≥ 1 | 4 |
| **Total eval cases** | **≥ 50** | **65** |

---

## Coverage Gaps (informational, not blocking)

Every spec requirement is met. These are defense-in-depth edges the live
server already handles correctly but the eval set does not pin:

1. Float or zero-stripped FIPS input (`6`, `6.0`).
2. NaN / inf salary.
3. `salary = False` (eval only tests `True`).
4. Same-state detection via whitespace (`CA` vs `  CA  `).
5. Strict-mode refusal where only state_b is the estimate (all four eval
   strict-refuse cases have the offender in state_a or make it the first
   encountered).
6. Tab / non-space whitespace in full state name.
7. `verified_only` as a non-bool truthy value (the handler already coerces
   via `bool(...)` but no eval case pins it).

Detailed recommendations are in `governance/eda/mcp-bea-rpp-eda.md`
(Section "Untested Input Shapes").

---

## Artifacts Produced

- `governance/eda/mcp-bea-rpp-eda.md` — full EDA / eval-coverage report with
  per-bucket tables, byte-for-byte verification matrix, arithmetic
  reproduction table, and untested-edge inventory.
- `governance/audit-trail/2026-04-11-data-analyst-mcp-bea-rpp.md` — this
  audit entry.

---

## Decisions

- **No changes recommended to the eval set.** It meets all 11 spec
  categories at or above the minimum, and every case passes against the live
  server. The surfaced gaps are defense-in-depth, not acceptance criteria.
- **Strict-mode "refuses all 43 estimates" verified via live sweep**, not
  relying solely on the eval's sample. Documented in the EDA report so
  @dq-rule-writer and @staff-engineer can cite the exhaustive check.
- **Arithmetic spec example (CA vs IA at $65K) reproduced exactly** —
  acceptance criterion "`58,717.25 vs 74,031.89`" met.

---

## Spec References

- `docs/specs/mcp-bea-rpp.md` — §Eval Set (11 categories), §Acceptance
  Criteria (exhaustive strict mode, arithmetic example, ≥ 50 cases).
- Parent specs: `raw-ingest-bea-rpp`, `silver-base-bea-rpp`,
  `gold-regional-price-parities` (all COMPLETE).
- Parent EDA: `governance/eda/gold-regional-price-parities-eda.md`.

---

*Logged 2026-04-11 by @data-analyst*
