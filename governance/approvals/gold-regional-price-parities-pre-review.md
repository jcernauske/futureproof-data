# Governance Review: gold-regional-price-parities

**Review Type:** Pre-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-11
**Zone:** Gold (Consumable)
**Verdict:** APPROVED-WITH-ADVISORIES

---

## Scope of this review

This is the pre-implementation gate for `docs/specs/gold-regional-price-parities.md`, the Gold (Consumable) promote of `base.bea_rpp` into `consumable.regional_price_parities`. Parent specs `raw-ingest-bea-rpp` and `silver-base-bea-rpp` are both COMPLETE and staff-signed (2026-04-10). This review is the mandatory Gold-side anchor for Bronze staff-review **Condition 7** and Silver staff-review **Condition B** — both of which explicitly require the @governance-reviewer to verify at Gold pre-review that `verification_status` is preserved as a first-class column on every Gold row. That check is performed and passes.

No joins, no cross-source integration, no concept normalization. This is a pure Silver→Gold row-for-row promote with 4 derived columns, 1 provenance carry-forward, and 2 new business glossary terms (BT-106, BT-107). Greenfield mode — target table does not yet exist.

---

## Pre-Implementation Checklist

- [x] **Problem statement and success criteria** — present; identifies MCP tools, frontend, and stretch-goal consumers
- [x] **Input data sources identified with paths** — `base.bea_rpp` (51 rows, COMPLETE, contract ACTIVE)
- [x] **Output artifacts defined with paths and formats** — `consumable.regional_price_parities`, Iceberg, 51 rows, 15 columns
- [x] **Transformations described (what changes, why)** — 2 carry-forwards (passthrough + verification_status), 5 derivations (cost_tier + 4 adjusted_Nk), 1 provenance column (promoted_at)
- [x] **Zone assignment correct** — Gold/Consumable, matches project convention (`consumable.*` target namespace confirmed against `domain/manifest.yaml` and the 9 existing `consumable-*.yaml` contracts)
- [x] **Primary implementation agent identified** — @primary-agent, full 18-step workflow enumerated
- [x] **DQ rule categories specified** — P0 structural, P0 cost_tier, P0 adjusted_Nk, P0 verification_status carry-forward, P0 temporal/grain, P0 spot-checks, P1 freshness/distribution
- [x] **CDE mapping impact assessed** — all 8 Silver CDEs carry forward; cost_tier and adjusted_Nk inherit CDE-by-derivation from rpp_all_items and purchasing_power_multiplier
- [x] **Lineage scope defined** — Silver (base.bea_rpp) → Gold (consumable.regional_price_parities), single input table, no joins
- [x] **Breaking changes to existing schemas flagged** — N/A (greenfield)
- [x] **Testing approach defined** — spot-check verification for all 8 BEA-verified states with exact-value assertions; chaos pack focus areas named (boundary edges, arithmetic, carry-forward)

### Data Model Gate (Greenfield)

Greenfield mode — models MUST be complete before implementation begins. The spec correctly schedules @semantic-modeler as step 3 of the workflow (after @data-steward glossary terms and before @data-analyst EDA). Models are expected to land at:

- `governance/models/gold-regional-price-parities-conceptual.md`
- `governance/models/gold-regional-price-parities-logical.md`
- `governance/models/gold-regional-price-parities-physical.md`

Because `REQUIRE_HUMAN_APPROVAL = true` for this project (per CLAUDE.md), all three model stages must be APPROVED by a human before implementation proceeds. The spec's Governance Artifacts checklist anchors this requirement. **This gate is NOT discharged at this pre-review — it is deferred to the @semantic-modeler step and will be re-checked at post-implementation review.** The pre-review verdict below is conditional on the modeling gate being satisfied before @primary-agent writes any transformer code.

### Bronze Condition 7 Verification (mandatory Gold-side anchor)

| Check | Result |
|---|---|
| Gold schema includes `verification_status` as a first-class column | **PASS** — column 13 of 15, type string, required=yes |
| Gold carries `verification_status` unchanged from Silver (no re-derivation) | **PASS** — listed under "Silver passthrough" in §Gold Transformations |
| Gold has a P0 allow-list rule on `verification_status` values | **PASS** — spec §DQ Rules "verification_status values IN (`bea_official`, `estimate`)" |
| Gold has a P0 count-of-8 rule matching the Silver invariant | **PASS** — spec §DQ Rules "COUNT(\*) WHERE verification_status='bea_official' = 8" |
| Gold enforces canonical 8-state FIPS set for `bea_official` rows | **PASS** — spec §DQ Rules "Every `bea_official` row's `state_fips` IN the 8-state canonical set" |
| MCP carry-forward obligation documented as forward-only | **PASS** — spec §Bronze Staff Review Conditions explicitly forwards the `data_source`/strict-mode requirement to `mcp-bea-rpp` |
| Spec references Silver contract's `staff_review_conditions.condition_7_carry_forward` block | **PASS** — spec §Bronze Staff Review Conditions cites Bronze Condition 7 by name as "implemented here" |

**Bronze Condition 7 is fully anchored at Gold.** This discharges the Gold half of Silver staff-review Condition B. The MCP half remains open and will be enforced at `mcp-bea-rpp` pre-review.

---

## Sanity Checks

### Cost tier boundary analysis

Breakpoints are documented as left-closed (`>=`). The 8 BEA-verified RPP values are:

| State | RPP | Tier (CASE) | Expected | Match |
|---|---|---|---|---|
| CA | 110.7 | very_high | very_high | YES |
| HI | 110.0 | very_high | very_high | YES |
| DC | 109.9 | very_high | very_high | YES |
| NJ | 108.8 | very_high | very_high | YES |
| AR | 86.9 | very_low | very_low | YES |
| MS | 87.0 | very_low | very_low | YES |
| IA | 87.8 | very_low | very_low | YES |
| OK | 87.8 | very_low | very_low | YES |

**None of the 8 BEA-verified values sits at an exact breakpoint** (108.0, 103.0, 97.0, 91.0). Left-closed convention is unambiguous for every anchored state. If any `estimate` row happens to land exactly on 108.0, 103.0, 97.0, or 91.0, the left-closed rule gives it the higher tier — this is defensible and matches the spec's text.

### Adjusted salary arithmetic spot-check

All 8 `adjusted_50k` values in the spec's §DQ Rules spot-check table recompute to the cent:

```
CA: 50000 * (100/110.7) = 45167.12  (spec: 45167.12) OK
HI: 50000 * (100/110.0) = 45454.55  (spec: 45454.55) OK
DC: 50000 * (100/109.9) = 45495.91  (spec: 45495.91) OK
NJ: 50000 * (100/108.8) = 45955.88  (spec: 45955.88) OK
AR: 50000 * (100/86.9)  = 57537.40  (spec: 57537.40) OK
MS: 50000 * (100/87.0)  = 57471.26  (spec: 57471.26) OK
IA: 50000 * (100/87.8)  = 56947.61  (spec: 56947.61) OK
OK: 50000 * (100/87.8)  = 56947.61  (spec: 56947.61) OK
```

8/8 exact matches. The @dq-rule-writer will have authoritative reference values for `adjusted_50k`; the other three levels (`adjusted_30k/75k/100k`) follow mechanically from the same multiplier and do not need separate hand-checks.

### Distribution rule severity (estimate-distribution risk)

The 43/51 estimated rows are primary-agent placeholders. The spec is correct to classify the "at least 3 distinct cost tiers present" rule as **P1** (soft) rather than P0. The exact tier distribution depends on estimate values that are not BEA-authoritative, so hard-coding a distribution invariant would overfit to the current placeholder set and break the moment the live BEA API refresh replaces the 43 estimates. P1 is the right call.

The spec's §DQ Rules cost_tier section also says "All 5 cost tiers are expected but only 4 may materialize with the current estimates" — this honest disclosure is appropriate for a partial_verification-tier contract. **Gold DQ MUST NOT codify a P0 "exactly 5 tiers present" rule** until after the live BEA API refresh. The spec gets this right.

### Consumable namespace convention

Verified against `/Users/jcernauske/code/bright/futureproof-data/domain/manifest.yaml` and `/Users/jcernauske/code/bright/futureproof-data/governance/data-contracts/`:

- Existing Gold tables: `consumable.career_outcomes`, `consumable.occupation_profiles`, `consumable.onet_work_profiles`, `consumable.career_transitions`, `consumable.ai_exposure`, `consumable.program_career_paths`, `consumable.career_branches`
- Existing contract file pattern: `consumable-<table-name>.yaml`

`consumable.regional_price_parities` matches this convention. Expected contract file path: `governance/data-contracts/consumable-regional-price-parities.yaml`. **NOTE**: the spec §Governance Artifacts lists the path as `governance/data-contracts/gold-regional-price-parities.yaml`, which does NOT match the project's actual `consumable-*.yaml` pattern. See ADVISORY-1 below.

### Business glossary state

Verified against `governance/business-glossary.json`:

| Term ID | Status | Notes |
|---|---|---|
| BT-098 Regional Price Parity (RPP) | PRESENT (line 1265) | Already anchored at Bronze |
| BT-099 Purchasing Power Multiplier | PRESENT (line 1278) | Anchored at Silver |
| BT-100 State FIPS Code | PRESENT (line 1291) | Anchored at Bronze |
| BT-101 State Name | PRESENT (line 1304) | Anchored at Bronze |
| BT-102 RPP Data Year | PRESENT (line 1317) | Anchored at Bronze |
| BT-103 USPS State Abbreviation | PRESENT (line 1330) | Anchored at Silver |
| BT-104 Census Region | PRESENT (line 1343) | Anchored at Silver |
| BT-105 Data Verification Status | PRESENT (line 1356) | Anchored at Silver |
| BT-106 Cost Tier | **ABSENT** — new in this spec | Scoped to @data-steward step |
| BT-107 Adjusted Salary | **ABSENT** — new in this spec | Scoped to @data-steward step |

No phantom references. The 8 carried-forward terms all resolve to real entries in the glossary; the 2 new terms (BT-106, BT-107) are correctly scoped to this spec and will be added by @data-steward as step 2 of the workflow. Their draft definitions in the spec are sufficient to guide @data-steward and do not contradict the existing BT-098/099/105 definitions.

### Quality tier honesty

The spec §Silver Input and §Data Contract both declare the Gold quality tier as `partial_verification` — **unchanged from Silver/Bronze**. This is correct. 43/51 rows are still primary-agent estimates; no verification work happens at Gold, so the tier cannot improve. The spec does not overstate the quality tier. The forward-only path (live BEA API refresh flips the count-of-8 to count-of-51 as a minor-version bump) is documented identically at Silver and Gold, consistent with the partial_verification → high tier transition plan.

---

## Issues Found

| # | Severity | Description | Resolution Required |
|---|---|---|---|
| 1 | ADVISORY | Spec §Gold Schema header says "(14 columns)" but the schema table lists 15 rows, and §Data Contract §Null guarantee correctly says "0% nulls on all 15 columns". The 15-count is authoritative; the "14" in the header is a stale heading. | @primary-agent or @doc-generator: fix header to "Gold Schema (15 columns)" before the physical model is drafted. Not blocking, but fix before post-review. |
| 2 | ADVISORY | Spec §Governance Artifacts lists the data contract path as `governance/data-contracts/gold-regional-price-parities.yaml`, which does not match the project's actual `consumable-*.yaml` naming convention (9 existing contracts all use `consumable-<table>.yaml`). | @doc-generator: write the contract to `governance/data-contracts/consumable-regional-price-parities.yaml` to match convention. Update the spec's Governance Artifacts checklist to reflect the convention. Not blocking pre-review. |
| 3 | ADVISORY | The "passthrough integrity" DQ rule (Gold row `rpp_all_items` == Silver row for same `state_fips`) is correctly marked `evaluation_mode: production_only`. Make sure @dq-engineer and @chaos-monkey both know this rule cannot run in unit tests that mock the Silver input — it requires the real Iceberg table. | @dq-engineer + @chaos-monkey: read the evaluation_mode marker and skip this rule in non-production contexts. Test harness should explicitly assert it was exercised at least once in production mode before post-review. |
| 4 | ADVISORY | Spec does not explicitly name a chaos scenario for the left-closed breakpoint edge (a synthetic row at exactly `rpp=108.0`, `103.0`, `97.0`, `91.0`). The spec §Agent Workflow mentions "cost_tier boundary edges" at step 9 but does not enumerate the scenarios. | @chaos-monkey: write 4 synthetic boundary-row scenarios (one per breakpoint) asserting the higher tier wins and verify the Gold CASE expression matches. Not blocking pre-review but noting for step 9 planning. |
| 5 | ADVISORY | The spec names @cab-review as "greenfield, expected SKIP" at step 7. This is consistent with how the project has handled prior Gold greenfield specs, but the SKIP must still be logged to `governance/audit-trail/` with a rationale. | @primary-agent: log the SKIP decision with rationale at step 7. Not blocking pre-review. |

**No CHANGES REQUESTED and no REJECTED issues.** All 5 findings are ADVISORY and resolvable without blocking implementation.

---

## Decision Rationale

The spec is the smallest Gold transformation in the project — a pure Silver→Gold shape pass with 4 arithmetic derivations and 1 carry-forward. Every pre-implementation checklist item is satisfied. Every piece of load-bearing arithmetic recomputes to the cent. The business glossary terms are real, not phantom (BT-098..BT-105 all present in `business-glossary.json`), and the two new terms (BT-106, BT-107) are properly scoped to the @data-steward step with usable draft definitions.

Most importantly, **Bronze staff-review Condition 7 is fully anchored at Gold**: `verification_status` is a first-class column, has a P0 allow-list rule, has a P0 count-of-8 rule, has a P0 canonical-FIPS rule, and the spec explicitly references the Bronze staff review by name as the source of the requirement. This discharges the Gold half of Silver staff-review Condition B. The MCP half (per-row `data_source` in tool response, strict mode refuses `estimate` rows) is correctly forwarded to `mcp-bea-rpp` as a forward-only obligation.

The spec does not overstate quality. It correctly keeps the Gold quality tier at `partial_verification` because 43/51 rows remain estimates, it correctly classifies the cost_tier distribution rule as P1 (soft) because the current distribution is a function of unverified placeholders, and it correctly leaves the live BEA API refresh as a downstream minor-version bump rather than a pre-Gold blocker.

The 5 advisories are all cosmetic or housekeeping: a column-count typo in a section header, a contract filename that should match the project's `consumable-*` convention, an evaluation_mode caveat that needs to land in the test harness, a chaos-scenario enumeration gap, and an audit-trail logging reminder for the @cab-review SKIP. None of them is a governance gap. None of them changes the schema, the DQ rule set, the glossary references, or the verification posture.

**The Data Model Gate is explicitly deferred to @semantic-modeler (step 3 of the workflow).** This pre-review approval is conditional on the three model stages landing and being APPROVED before @primary-agent writes transformer code. That condition will be re-verified at post-implementation review, where the physical model must match the implementation.

---

## Verdict

**APPROVED-WITH-ADVISORIES.** Implementation may begin. Proceed to @data-steward (BT-106, BT-107) and then @semantic-modeler (three-stage models with human approval per `REQUIRE_HUMAN_APPROVAL=true`). Post-implementation review will re-verify Bronze Condition 7 on the actual Iceberg table, confirm the physical model matches the implementation, and check that the 5 advisories above have been resolved.

Gold half of Silver staff-review Condition B discharged here.

---

## Artifacts referenced

| Path | Role |
|---|---|
| `/Users/jcernauske/code/bright/futureproof-data/docs/specs/gold-regional-price-parities.md` | Spec under review |
| `/Users/jcernauske/code/bright/futureproof-data/docs/specs/raw-ingest-bea-rpp.md` | Bronze parent (COMPLETE) |
| `/Users/jcernauske/code/bright/futureproof-data/docs/specs/silver-base-bea-rpp.md` | Silver parent (COMPLETE) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/approvals/raw-ingest-bea-rpp-staff-review.md` | Bronze staff review — source of Condition 7 |
| `/Users/jcernauske/code/bright/futureproof-data/governance/approvals/silver-base-bea-rpp-staff-review.md` | Silver staff review — source of Condition B (Gold pre-review anchor) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/data-contracts/silver-base-bea-rpp.yaml` | Silver contract — 11-column source of truth for the passthrough set and the `condition_7_carry_forward` block |
| `/Users/jcernauske/code/bright/futureproof-data/governance/business-glossary.json` | Verified BT-098..BT-105 present; BT-106/107 absent as expected |
| `/Users/jcernauske/code/bright/futureproof-data/domain/manifest.yaml` | Verified `consumable.*` target namespace convention |
| `/Users/jcernauske/code/bright/futureproof-data/governance/data-contracts/consumable-*.yaml` | 9 existing contracts confirming the filename convention |

---

*— End of Pre-Implementation Governance Review —*
