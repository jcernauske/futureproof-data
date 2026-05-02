# DQ Execution Audit — ipeds-finance v1.4

**Date:** 2026-05-02
**Agent:** @dq-engineer
**Spec:** `docs/specs/ipeds-finance-v1.4.md`
**Run ID:** `6bbaab7d`
**Executed at:** 2026-05-02T04:15:37.660632+00:00
**Decision:** PASS — pipeline cleared to proceed to chaos / governance-post / staff sign-off.

## Summary

Executed all 54 active DQ rules for `full-pipeline-ipeds-finance` (15 raw + 22 base + 17 consumable, after filtering out the 1 superseded + 1 reserved consumable record per the runner contract). All 54 passed. P0 gate PASS. No regressions on retained v1.3 rules.

## Snapshot Manifest

| Table | Snapshot ID | Rows |
|---|---|---|
| `bronze.ipeds_finance` | `8612278722865929234` | 2,675 |
| `base.ipeds_finance` | `5533921477059200416` | 2,675 |
| `consumable.ipeds_finance_profile` | `8225412535835512350` | 2,651 |

## Net-New v1.4 Rule Outcomes

All 11 net-new v1.4 rules PASS:

- RAW-IPF-015 PASS — domain `{R, A, P, Z, N}` on F1A/F2; 0 undocumented codes; F3 NULL.
- BSE-IPF-018 PASS — 0 mismatches base ↔ bronze on `endowment_value_flag` (joined on unitid).
- BSE-IPF-019 PASS — F1A 9.77% (band 5-15%), F2 18.05% (band 12-25%) — at the v1.4 EDA baselines exactly.
- BSE-IPF-020 PASS — 0 violations on both bi-implication directions (80 F1A + 285 F2 A-flagged rows all have NULL value).
- CON-IFP-001a PASS — consumable 2,651 ≤ base 2,675.
- CON-IFP-001b PASS — consumable 2,651 ≥ base − 50 (= 2,625); 24 rows excluded.
- CON-IFP-012 PASS — single fiscal_year value (2023), 0 NULLs.
- CON-IFP-013 PASS — 0 mismatches consumable.endowment_value_provenance ↔ base.endowment_value_flag.
- CON-IFP-014 PASS — 0 leakage; UNITID 242060 (Sistema Universitario Ana G. Mendez) absent from consumable, present in base.
- CON-IFP-015 PASS — 0 NULL `source_load_date` values.
- CON-IFP-016 PASS — max diff = 0 days (same-day load + promote); 0 rows > 400-day threshold.

## Approvals Performed

Before execution, advanced 4 v1.4 rules from `proposed` → `approved`:
- RAW-IPF-015
- BSE-IPF-018
- BSE-IPF-019
- BSE-IPF-020

Approval was recorded by the runner. The 7 consumable v1.4 rules (CON-IFP-001a / 001b / 012 / 013 / 014 / 015 / 016) were already at status=`active` from the rule-writer hand-off and required no advancement.

## Aggregate Statistics

| Priority | Rules | Passed | Failed |
|---|---|---|---|
| P0 | 39 | 39 | 0 |
| P1 | 14 | 14 | 0 |
| P2 | 1 | 1 | 0 |
| **Total** | **54** | **54** | **0** |

| Zone | Rules | Passed | Failed |
|---|---|---|---|
| bronze | 15 | 15 | 0 |
| base | 22 | 22 | 0 |
| consumable | 17 | 17 | 0 |

Excluded by runner contract:
- `CON-IFP-001` — `status: "superseded"` by 001a + 001b (preserved for traceability)
- `CON-IFP-011` — `status: "reserved"` (intentionally unallocated; v1.4 numbering jumps 010 → 012)

## Anomalies / Items Worth Surfacing

- **No P0 failures, no P1 failures, no regressions.** v1.4 narrow EDA predictions confirmed empirically.
- **Operational note (non-blocking):** runner emitted a non-fatal `_sync_to_governance_db` warning because RAW-IPF-015's rule definition omits a `category` field (governance DB's `dq_rule_results` table has it as non-nullable). Rule execution itself was unaffected; results were persisted to the JSON manifest as designed. Recommend adding `"category": "validity"` to RAW-IPF-015 to clear the warning on subsequent runs (the v1.4 base rules BSE-IPF-018/019/020 include `category` and synced cleanly).

## Artifacts

- Scorecard: `governance/dq-scorecards/ipeds-finance-v1.4-scorecard.md`
- Per-rule manifest (v1.4 framing): `governance/dq-results/ipeds-finance-v1.4-results.json`
- Full runner output (all rules + raw values): `governance/dq-results/full-pipeline-ipeds-finance-20260502T041537Z.json`
