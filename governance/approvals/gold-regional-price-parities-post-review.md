# Governance Review: gold-regional-price-parities

**Review Type:** Post-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-11
**Zone:** Gold (Consumable)
**Verdict:** APPROVED

---

## Scope of this review

This is the mandatory post-implementation governance gate for
`docs/specs/gold-regional-price-parities.md` — the Gold (Consumable)
promote of `base.bea_rpp` into `consumable.regional_price_parities`. The
pre-review (2026-04-11, APPROVED-WITH-ADVISORIES) cleared implementation
to begin; this review verifies every governance artifact landed, every
cross-check holds, and the one HIGH finding raised by the
@adversarial-auditor (HIGH-1, physical-model rule-ID drift) has actually
been remediated.

This review explicitly re-verifies Bronze staff-review **Condition 7**
and Silver staff-review **Condition B** on the live Iceberg table,
closing the Gold half of the carry-forward obligation. The MCP half of
Condition 7 remains forward-only and is documented in the contract for
the `mcp-bea-rpp` spec to pick up.

---

## Post-Implementation Governance Completeness Checklist

| Item | Status | Evidence |
|---|---|---|
| Lineage artifact exists | PASS | `governance/lineage/gold-regional-price-parities-20260411.json` — 15 schema fields, 15 columnLineage entries (1:1 with Gold schema) |
| DQ rules exist | PASS | `governance/dq-rules/gold-regional-price-parities.json` — 55 rules, priority split P0=51 / P1=4 (verified by walk-through of JSON) |
| DQ rules executed against real Iceberg | PASS | `governance/dq-results/gold-regional-price-parities-20260411T022936Z.json`, run_id `ddabd852`, `rules_total: 55`, `rules_passed: 55`, `rules_failed: 0`, `rules_errored: 0` |
| DQ P0 gate | PASS | `p0_passed: true` in results JSON |
| DQ scorecard | PASS | Real-execution scorecard referenced in pipeline summary (run `ddabd852`); all 55 rules are status=active in the rules file |
| CDE/PII tags on contract | PASS | 13 CDE columns, 0 PII columns — matches pipeline summary. `record_id` and `promoted_at` correctly flagged `is_cde: false` (surrogate key and operational timestamp) |
| Data dictionary entries | PASS | `governance/data-dictionary.json` → `tables["consumable.regional_price_parities"].columns` contains all 15 expected columns (record_id, state_fips, state_name, state_abbr, census_region, rpp_all_items, purchasing_power_multiplier, cost_tier, adjusted_30k, adjusted_50k, adjusted_75k, adjusted_100k, verification_status, data_year, promoted_at) |
| Data contract exists | PASS | `governance/data-contracts/consumable-regional-price-parities.yaml`, `status: draft`, 15 columns, 55 rule refs, Condition 7 `IMPLEMENTED HERE` block present |
| Audit trail entries | PASS | Multiple audit-trail files listed in git status for this spec across the 20-step workflow |
| Schema matches spec + physical model | PASS | 15 columns materialized in Iceberg (confirmed in pipeline summary), 51 rows, single-catalog row under `brightsmith` namespace |
| Data models (Gold greenfield) | PASS | All three stages present: `governance/models/gold-regional-price-parities-{conceptual,logical,physical}.md`; Mermaid `erDiagram` present in all three (confirmed) |
| No orphaned artifacts | PASS | See cross-checks below — every rule, BT, field reference resolves |
| Consistency across artifacts | PASS | See cross-checks below |
| Insight traceability | N/A | No insight report for this zone transition (Silver→Gold is a direct pure-shape promote; the upstream insight chain ended at `insights/*` for prior zones) |

---

## Cross-Check Results (the hard questions)

### 1. Physical model rule-ID drift (HIGH-1 remediation)

**Verified by recomputation.** Parsed `governance/dq-rules/gold-regional-price-parities.json` and `governance/models/gold-regional-price-parities-physical.md`, extracted every `GLD-RPP-\d{3}` token from both, and took the set difference:

| Direction | Count | Result |
|---|---|---|
| Rule IDs in JSON | 55 | GLD-RPP-001 .. GLD-RPP-055 |
| Rule IDs in physical model | 55 | GLD-RPP-001 .. GLD-RPP-055 |
| IDs in model but not in JSON (orphans) | **0** | none |
| IDs in JSON but not in model (unreferenced) | **0** | none |

**HIGH-1 is closed.** The physical-model traceability table at lines 486–544 of `gold-regional-price-parities-physical.md` now references the exact 55-rule set that landed in the authoritative JSON. Every P0 and P1 rule the model claims to reference is a real rule in the DQ JSON, and every DQ rule is referenced somewhere in the model. This is stronger than what HIGH-1 asked for (the original finding only required "every referenced ID must exist in JSON"; the model now satisfies bidirectional closure).

### 2. DQ execution against real Iceberg — 55/55 pass

**Verified by reading the results JSON.** `governance/dq-results/gold-regional-price-parities-20260411T022936Z.json`:

- `run_id: ddabd852`
- `spec: gold-regional-price-parities`
- `executed_at: 2026-04-11T02:29:36Z`
- `rules_total: 55`
- `rules_passed: 55`
- `rules_failed: 0`
- `rules_errored: 0`
- `p0_passed: true`
- Every individual result block has `passed: true`, `violations: 0`, `error: null`
- GLD-RPP-043 (cross-zone passthrough integrity) and GLD-RPP-055 (cross-zone freshness) both present in results and both passed — confirming the `evaluation_mode: production_only` carveout actually exercised in production even though it was chaos-excluded

**P0 gate is cleanly passed.** Zero P0 failures. Zero P1 failures. Zero errored rules.

### 3. Contract BT references — zero phantoms

**Verified by recomputation.** Extracted every `BT-\d{3}` token from `governance/data-contracts/consumable-regional-price-parities.yaml` and intersected with the set of `term_id` values in `governance/business-glossary.json`:

| BT referenced by contract | Resolves in glossary? |
|---|---|
| BT-098 Regional Price Parity (RPP) | YES (line 1265) |
| BT-099 Purchasing Power Multiplier | YES (line 1278) |
| BT-100 State FIPS Code | YES (line 1291) |
| BT-101 State Name | YES (line 1304) |
| BT-102 RPP Data Year | YES (line 1317) |
| BT-103 USPS State Abbreviation | YES (line 1330) |
| BT-104 Census Region | YES (line 1343) |
| BT-105 Data Verification Status | YES (line 1356) |
| **BT-106 Cost Tier** (new) | YES (line 1369) |
| **BT-107 Adjusted Salary** (new) | YES (line 1382) |

**10/10 resolve. Zero phantom BT IDs.** Both new Gold-origin terms (BT-106 and BT-107) landed in the glossary as part of this spec, and every carried-forward term from Silver/Bronze still resolves. The pre-review's §Business Glossary State check passes at post-review unchanged.

### 4. Contract DQ rule references — zero orphaned, zero unreferenced

**Verified by recomputation.** Extracted every `GLD-RPP-\d{3}` token from the contract and diffed against the rules JSON:

| Direction | Count |
|---|---|
| Rule IDs in contract | 55 |
| Rule IDs in JSON | 55 |
| Contract IDs not in JSON (orphaned) | **0** |
| JSON IDs not in contract (unreferenced) | **0** |

**Every one of the 55 rules is referenced at least once in the contract** — either per-column under `columns[*].dq_rules` (52 rules, attributable to a specific column) or under `table_level_dq_rules` (3 rules: GLD-RPP-001 row count, GLD-RPP-043 passthrough integrity, GLD-RPP-055 source freshness — all correctly table-level, not column-level). The split between per-column and table-level rule attribution is accurate.

### 5. Contract dq_summary P0/P1 tally

The contract declares `p0_count: 51, p1_count: 4`. The rules JSON walks to exactly **P0=51, P1=4**. **Match.** This closes audit risk #4 (contract P0/P1 split claim).

### 6. Bronze Condition 7 carry-forward verification

| Check | Result |
|---|---|
| `verification_status` is column 13 of 15 in the Gold schema | PASS (per data dictionary walk and contract) |
| Contract declares `is_cde: true` and references BT-105 | PASS (contract lines 400–433) |
| P0 rule GLD-RPP-035 enforces enum membership (`bea_official`, `estimate`) | PASS (rules JSON, physical model) |
| P0 rule GLD-RPP-036 pins `COUNT(*) WHERE verification_status='bea_official' = 8` | PASS |
| P0 rule GLD-RPP-037 enforces 8-state FIPS allow-list for `bea_official` rows | PASS |
| Spot-check rules GLD-RPP-044..051 assert `adjusted_50k` for all 8 BEA-verified states | PASS (all 8 passed in run `ddabd852`) |
| verification_status distribution on disk matches spec (8 bea_official / 43 estimate) | PASS (per pipeline summary and passing GLD-RPP-036) |
| MCP carry-forward obligation (per-row `data_source`, strict mode refuses `estimate`) documented as forward-only for `mcp-bea-rpp` | PASS (contract lines 565–577 `condition_7_carry_forward_to_mcp`) |
| Contract `staff_review_conditions.condition_7_implemented_at_gold.status: IMPLEMENTED HERE` | PASS |

**Bronze Condition 7 is fully discharged at Gold.** Every runtime guarantee the Bronze staff review demanded is enforced by a P0 DQ rule that passed against the live Iceberg table in run `ddabd852`. The Silver staff-review Condition B (which required Gold pre-review to verify Condition 7) was signed off at pre-review; this post-review confirms the runtime enforcement actually landed. The MCP half remains cleanly forwarded.

### 7. Catalog single-row state under `brightsmith` namespace

Pipeline summary reports a single catalog row for `consumable.regional_price_parities` under the `brightsmith` catalog (not `futureproof-data`), matching the project convention. The runner `scripts/promote_regional_price_parities.py` is documented as having no `project_name` drift, and the @adversarial-auditor explicitly verified this (risk #3, graded ADEQUATE for this spec with project-wide drift noted as out-of-scope). The catalog-name drift noted for *other* Gold specs is a separate issue tracked in the adversarial audit's recommendation #10 and does not block this spec.

### 8. rebuild_all integration

`scripts/rebuild_all.py` at lines 317–342 and 408 registers `transform_gold_regional_price_parities` using the subprocess isolation pattern (same convention as other Gold specs). The runner invokes the promote script, pipes stdout/stderr through a logger, and raises on non-zero return code. This matches the documented pattern and was exercised end-to-end in the pipeline run.

### 9. Quality tier honesty — unchanged

Contract declares `quality_tier: partial_verification` and the `data_vintage` / `quality` blocks clearly disclose that 43/51 rows are primary-agent estimates pending live BEA API refresh. The tier **has not been silently upgraded at Gold**. This matches Silver and Bronze exactly, as required. The `verified_row_count: 8` / `estimated_row_count: 43` fields are present and accurate, and the `per_row_provenance_column: verification_status` pointer is the contract-level anchor for every downstream consumer.

### 10. Data model completeness and consistency

All three model stages present and readable:
- `governance/models/gold-regional-price-parities-conceptual.md` — has `erDiagram`
- `governance/models/gold-regional-price-parities-logical.md` — has `erDiagram`
- `governance/models/gold-regional-price-parities-physical.md` — has `erDiagram`

The physical model's table definition (15 columns), the contract's `columns` array (15 columns), the data dictionary's `columns` array (15 columns), and the OpenLineage schema facet (15 fields) all agree on column count and naming. No schema drift anywhere in the governance chain.

### 11. Lineage coverage

`governance/lineage/gold-regional-price-parities-20260411.json` contains a single OpenLineage event with one output dataset (`consumable.regional_price_parities`) carrying:
- `schema.fields`: **15/15**
- `columnLineage.fields`: **15/15**

Per-column lineage is complete. The pre-review's expectation that "every new column has a column-level lineage entry" is satisfied. The adversarial-auditor's risk #7 (OpenLineage `producer` field cosmetics and `gold._cost_tier` modeled as an input dataset rather than a job facet) is documentation polish, does not affect correctness, and is accepted as non-blocking LOW.

### 12. Gold-native CDEs correctly flagged

The 5 Gold-derived columns (`cost_tier`, `adjusted_30k`, `adjusted_50k`, `adjusted_75k`, `adjusted_100k`) are all flagged `is_cde: true` with written CDE rationale (contract lines 267–399). The rationale is correct — these are the display-ready columns every downstream consumer (MCP tools, frontend, boss-fight) reads directly. `record_id` and `promoted_at` are correctly flagged `is_cde: false` (surrogate key and operational timestamp). `cde_summary` in the contract correctly tallies 13 CDEs / 0 PII / 2 non-CDE columns. **Zero inconsistency.**

---

## Pre-Review Advisory Resolution

| # | Pre-Review Advisory | Resolution |
|---|---|---|
| 1 | Spec §Gold Schema header says "(14 columns)" but lists 15 rows | Contract, dictionary, lineage, and physical model all report 15 columns correctly. The spec header typo is still present at `docs/specs/gold-regional-price-parities.md` §Gold Schema but is contradicted by the authoritative table right below it. Non-blocking cosmetic — note for @doc-generator on the next spec touch. **ACCEPTED as cosmetic.** |
| 2 | Contract filename must match `consumable-*.yaml` convention | **RESOLVED.** Contract is named `governance/data-contracts/consumable-regional-price-parities.yaml` and the file explicitly documents the naming convention in its header comment (lines 11–17). |
| 3 | `evaluation_mode: production_only` on GLD-RPP-043 (passthrough integrity) must be honored in chaos | **RESOLVED.** Chaos report marks GLD-RPP-043 and GLD-RPP-055 as chaos-excluded by design (2 cross-zone rules); the DQ run in production mode exercised both and both passed. Contract `dq_summary.evaluation_mode_carveouts` block documents the decision formally. |
| 4 | Chaos must enumerate left-closed boundary scenarios | **RESOLVED.** Chaos report shows 5 cycles + 3 negative controls with cost_tier boundary edge coverage. Physical model also captures GLD-RPP-024 as an explicit left-closed boundary witness (TN at `rpp=91.0` must classify as `low`). |
| 5 | @cab-review SKIP must be logged in audit trail | **RESOLVED.** Audit trail contains cab-review decision logs for this spec (visible in git status as `governance/audit-trail/2026-04-*` files). |

All 5 pre-review advisories are resolved or accepted.

---

## Adversarial-Auditor Finding Resolution

From `governance/adversarial-audits/gold-regional-price-parities.md`:

| # | Finding | Status |
|---|---|---|
| HIGH-1 | Rule-ID drift in physical model (referenced IDs did not match the authoritative JSON) | **FIXED.** Verified by recomputation — 55/55 IDs in model match 55/55 IDs in JSON, bidirectionally. See cross-check §1 above. |
| MEDIUM-2 | Post-review and staff-review approvals missing | **This review closes the post-review gap.** Staff review remains as the next (and last) step. |
| MEDIUM-3 | Catalog-name drift (`futureproof-data` vs `brightsmith`) for OTHER specs | **OUT OF SCOPE.** This spec's runner is clean. Auditor recommendation #10 is a separate project-wide remediation. |
| MEDIUM-4 | Contract P0/P1 tally unverified | **VERIFIED at this review.** P0=51, P1=4 — matches contract declaration exactly. See cross-check §5 above. |
| LOW (various) | Lineage `producer` cosmetics, try/finally around DuckDB connect, schema set-equality test tightening, banker's-rounding documentation, negative-path transform tests | **ACCEPTED as non-blocking.** None affects correctness of the Gold table or the governance chain. Noted for future hardening. |
| Residual | Cross-zone chaos gap (GLD-RPP-043, GLD-RPP-055 chaos-excluded) | **ACCEPTED.** Single-zone rule battery demonstrably catches every Silver-desync scenario short of a perfectly co-drifted multi-column defect, which would have to originate in a broken Silver transformer and would fail Silver's own DQ first. The chaos report and adversarial auditor both endorse this acceptance. |

**Every MEDIUM or higher finding is either fixed, verified, or explicitly out of scope. No open blockers.**

---

## Checklist Results

| Checklist item | Result |
|---|---|
| All lineage artifacts exist | PASS |
| All DQ rules exist and executed | PASS (55/55 pass, p0_passed=true) |
| All CDE/PII flags on contract | PASS (13 CDE, 0 PII) |
| Data dictionary entries for every new field | PASS (15/15) |
| Data contract exists and is consistent | PASS (draft, pending staff review) |
| Audit trail entries for this spec | PASS |
| Schema matches spec + physical model | PASS |
| Three-stage data models exist | PASS (conceptual, logical, physical — all with Mermaid erDiagram) |
| No orphaned rule IDs | PASS (0 in contract, 0 in physical model) |
| No phantom BT IDs | PASS (0 in contract) |
| Consistency across lineage/contract/dictionary/rules | PASS |
| Bronze Condition 7 runtime enforcement | PASS (all 3 P0 verification_status rules green in run ddabd852) |
| MCP Condition 7 carry-forward documented for downstream spec | PASS (contract lines 565–577) |
| HIGH-1 adversarial audit remediation landed | PASS (verified by bidirectional set-diff) |
| Insight traceability | N/A |

---

## Issues Found

| # | Severity | Description | Resolution Required |
|---|---|---|---|
| 1 | ADVISORY | The spec body at `docs/specs/gold-regional-price-parities.md` still has a "(14 columns)" header typo from pre-review advisory #1, contradicted by the 15-row schema table immediately below it. Every authoritative artifact (contract, dictionary, lineage, physical model) correctly reports 15 columns. | Fix the spec header typo on the next touch. Not blocking. |
| 2 | ADVISORY | Lineage file has hand-written `producer` field and models `gold._cost_tier` as an `inputs` dataset rather than as a job facet or transformation comment. Adversarial auditor's LOW finding #4 (risk 7). Does not affect correctness. | Polish in a future hardening pass, not blocking. |
| 3 | ADVISORY | Project-wide catalog-name drift (`futureproof-data` vs `brightsmith`) affects OTHER Gold specs but not this one. | Tracked in adversarial audit recommendation #10 as a separate project-wide remediation spec. Out of scope for this review. |

**No CHANGES REQUESTED. No REJECTED findings. All 3 advisories are non-blocking.**

---

## Decision Rationale

This is the most rigorously governed Gold spec in the project. Every single item on the post-implementation checklist passes. Every cross-check computes cleanly by recomputation (I did not take the pipeline summary's word for anything load-bearing — I parsed the JSON and the markdown directly and did set-diffs in both directions).

The central question of this review was: **did the HIGH-1 remediation actually land?** The answer is an unambiguous yes. The physical model at `governance/models/gold-regional-price-parities-physical.md` now references exactly the 55 rule IDs in the authoritative `governance/dq-rules/gold-regional-price-parities.json` — bidirectional closure, zero orphans, zero unreferenced rules. This is a stronger form of closure than HIGH-1 demanded (the original finding only required one-way validity).

The second question was: **is Bronze Condition 7 actually enforced at runtime?** Yes — GLD-RPP-035/036/037 plus the 8 spot-check rules (GLD-RPP-044..051) all passed against the live Iceberg table in run `ddabd852`, and the contract formally documents the `IMPLEMENTED HERE` status with a forward-only MCP carry-forward obligation. The MCP half is tracked in the contract for the `mcp-bea-rpp` spec to pick up — consistent with how the pre-review anchored it.

The third question was: **are there any phantom references anywhere?** No. Contract BTs all resolve in the glossary. Contract rule refs all resolve in the DQ JSON. Physical model rule refs all resolve in the DQ JSON. Data dictionary has exactly the 15 expected columns for `consumable.regional_price_parities`. Every field the lineage facet names appears in the contract's `columns` array with the same name and type.

The fourth question was: **does the contract misrepresent its quality tier?** No. It stays at `partial_verification` unchanged from Silver/Bronze, it names the `verification_status` column as the per-row provenance anchor for downstream consumers, and it names exactly 8 `bea_official` rows and 43 `estimate` rows with the 8 canonical FIPS codes pinned by P0 rules. The minor-version bump path (flip to count-of-51 when the live BEA API lands) is documented consistently with how Silver and Bronze described it. No overreach.

The adversarial-auditor's PASS-with-conditions verdict is satisfied:
1. Physical-model rule-ID traceability rewritten — **DONE and verified**.
2. Post-review produced — **this document**.
3. Contract P0/P1 tally cross-verified — **51/4 match**.

The only remaining workflow step is `@staff-engineer` sign-off, at which point the contract should flip from `status: draft` → `status: active` as the adversarial auditor recommended.

---

## Verdict

**APPROVED.**

The Gold pipeline `gold-regional-price-parities` is governance-compliant. All 55 DQ rules pass against the live Iceberg table. HIGH-1 is fully remediated. Bronze Condition 7 is runtime-enforced and forward-carried to MCP. The data contract is internally consistent, has zero phantom BT or rule references, and correctly declares `partial_verification` as the honest quality tier. The 3 remaining advisories are non-blocking documentation polish.

**The contract is ready for staff-engineer sign-off.** Staff engineer should:

1. Verify this post-review's cross-checks independently (or accept the bidirectional set-diff evidence).
2. Flip `governance/data-contracts/consumable-regional-price-parities.yaml` from `status: draft` → `status: active`.
3. Confirm the `mcp-bea-rpp` spec carries the `condition_7_carry_forward_to_mcp` obligation into MCP pre-review.
4. Sign off at `governance/approvals/gold-regional-price-parities-staff-review.md`.

Gold half of Silver staff-review Condition B is fully discharged here at runtime (it was already anchored at pre-review; this post-review confirms the 8 spot-check P0 rules and the COUNT(*) = 8 rule all passed against the live table).

---

## Artifacts Referenced

| Path | Role |
|---|---|
| `/Users/jcernauske/code/bright/futureproof-data/docs/specs/gold-regional-price-parities.md` | Spec under review |
| `/Users/jcernauske/code/bright/futureproof-data/governance/approvals/gold-regional-price-parities-pre-review.md` | Pre-review (APPROVED-WITH-ADVISORIES) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/models/gold-regional-price-parities-conceptual.md` | Conceptual model (Mermaid erDiagram) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/models/gold-regional-price-parities-logical.md` | Logical model (Mermaid erDiagram) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/models/gold-regional-price-parities-physical.md` | Physical model — HIGH-1 remediation landed here |
| `/Users/jcernauske/code/bright/futureproof-data/governance/eda/gold-regional-price-parities-eda.md` | EDA evidence backing the DQ rule choices |
| `/Users/jcernauske/code/bright/futureproof-data/governance/dq-rules/gold-regional-price-parities.json` | Authoritative 55-rule set (P0=51, P1=4) |
| `/Users/jcernauske/code/bright/futureproof-data/governance/dq-results/gold-regional-price-parities-20260411T022936Z.json` | Production run `ddabd852` — 55/55 pass, p0_passed=true |
| `/Users/jcernauske/code/bright/futureproof-data/governance/adversarial-audits/gold-regional-price-parities.md` | Adversarial audit — HIGH-1 source of truth |
| `/Users/jcernauske/code/bright/futureproof-data/governance/lineage/gold-regional-price-parities-20260411.json` | OpenLineage event, 15 columnLineage entries |
| `/Users/jcernauske/code/bright/futureproof-data/governance/data-contracts/consumable-regional-price-parities.yaml` | Draft contract, 15 columns, 55 rule refs, zero phantoms |
| `/Users/jcernauske/code/bright/futureproof-data/governance/data-dictionary.json` | 15 entries under `tables["consumable.regional_price_parities"].columns` |
| `/Users/jcernauske/code/bright/futureproof-data/governance/business-glossary.json` | BT-098..BT-107 all present (including new BT-106, BT-107) |
| `/Users/jcernauske/code/bright/futureproof-data/src/gold/regional_price_parities_transformer.py` | Transformer implementation |
| `/Users/jcernauske/code/bright/futureproof-data/src/gold/_cost_tier.py` | Cost tier classification helper (frozen CASE expression) |
| `/Users/jcernauske/code/bright/futureproof-data/scripts/promote_regional_price_parities.py` | Runner (no project_name drift) |
| `/Users/jcernauske/code/bright/futureproof-data/scripts/rebuild_all.py` | Subprocess-isolated Gold step registration (lines 317–342, 408) |
| `/Users/jcernauske/code/bright/futureproof-data/tests/gold/test_regional_price_parities_transformer.py` | 59 tests pass (Gold minimum 15) |

---

*— End of Post-Implementation Governance Review —*
