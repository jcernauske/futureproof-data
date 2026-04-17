# Governance Review: raw-ingest-college-scorecard-institution (Gold zone) — SECOND PASS

**Review Type:** Pre-Implementation (Gold zone — Zone 3 of `raw-ingest-college-scorecard-institution`) — **Re-review #2**
**Reviewer:** @governance-reviewer
**Date:** 2026-04-16
**Spec:** `docs/specs/raw-ingest-college-scorecard-institution.md` (§Zone 3 — Gold)
**Parent gate status:** Bronze COMPLETE (13/13 DQ PASS against real Iceberg), Silver APPROVED 2026-04-16 (23/23 DQ PASS against real Iceberg), Silver advisory A3 CLOSED.
**Prior verdict:** CHANGES REQUESTED (2026-04-16 — see original review preserved below).
**Verdict:** **APPROVED**

---

## Executive Summary (Re-Review)

The spec author resolved all seven blocking items (B1–B7) from the first pass and both non-trivial advisories (A1, A2). The most consequential change is the explicit **scope-down of the ROI formula migration** — that work is now handed off to a sequential follow-up spec `roi-formula-cost-of-attendance.md`, and the Problem Statement has been rewritten so that `net_price_annual` and its six sibling columns land as nullable columns on `consumable.career_outcomes` without touching the engine's `compute_stat_roi` signature. This is the right call for a hackathon timeline and it removes the B4 traceability hole that drove the original block.

The Gold zone is now **implementation-ready**. The spec names the transformer file, the insertion point, the join key, the promote mode, the row-count invariant, the unmatched-UNITID expectation, and the schema-evolution posture. DQ coverage is 9 rules with 4 P0 / 4 P1 / 1 P2 — above the minimum requested in B2 — and critically includes explicit row-count preservation, the invariant pair (`net_price ≤ COA` and `net_price_4yr = 4 × annual`), the BT-111 negative-allowed rule calibrated to Silver's observed -$1,180 min, the unmatched-UNITID pattern check, and the `institution_control` insight-report closure rule. CDE assessment is inline on the 7-column table with rationales. Governance artifact list is complete and enumerates all downstream outputs.

**Residual items (all advisory):** A3 (EDA coverage calibration) is partially addressed by the spec's §Enrichment Mode note #5 and the DQ rule GLD-CSI-005 explicit "calibrated during EDA" language — the risk of a spurious post-hoc relaxation is materially reduced from the first pass. A4 (4,170 UNITID cardinality verification) remains an EDA step, non-blocking. A5 (MCP silent capability unlock on `institution_control`) is correctly deferred to the post-review.

No new blockers. No new CHANGES REQUESTED items. Proceed to implementation.

---

## Resolution Matrix — Blocking Items (B1–B7)

| ID | Original gap | Evidence of resolution in updated spec | Status |
|----|--------------|----------------------------------------|--------|
| B1 | §Zone 3 missing enrichment mode, transformer file, insertion point, join key, promote semantics | New §Enrichment Mode subsection (lines 255–279) names `src/gold/college_scorecard_career_outcomes.py`, provides the `institution` CTE SQL, specifies insertion point ("after the existing `cip_bands` CTE"), join key (`b.unitid = i.unitid`), LEFT JOIN rationale, row-count invariant (69,947), null-propagation behavior, unmatched-UNITID count (~1,131), `promoted_at` refresh semantics (note #6), and additive Iceberg schema evolution (note #7). | **RESOLVED** |
| B2 | 4 DQ rules insufficient; missing row-count preservation, COA coverage, `institution_control` coverage, unmatched-UNITID pattern, 4× invariant | §Gold DQ Rules (lines 281–295) now lists 9 rules: GLD-CSI-001 (row count, P0), GLD-CSI-002 (`net_price ≤ COA`, P0), GLD-CSI-003 (4× invariant, P0), GLD-CSI-004 (negative floor calibrated to BT-111 and Silver's observed min, P0), GLD-CSI-005/006/007 (coverage for `net_price_annual` / `cost_of_attendance_annual` / `institution_control`, P1, all labeled "calibrated during EDA"), GLD-CSI-008 (unmatched-UNITID pattern, P1), GLD-CSI-009 (categorical safety, P2). Exceeds the minimum of 5 additional rules requested. Pre-calibration targets are 60%, not the blind 80% that A3 flagged. | **RESOLVED** |
| B3 | No CDE/PII assessment for the 7 new columns | Inline CDE column added to the §Zone 3 7-row table (lines 243–251): `net_price_annual` = **CDE** with dual rationale (ROI-formula driver per follow-up spec + MCP-consumed); `cost_of_attendance_annual` = **CDE** with invariant-partner + display rationale; `institution_control` = non-CDE categorical with explicit rationale; 4 remaining fields = non-CDE display-only. Data Contract Update section (lines 299–307) re-asserts the 2 CDE flags and the minor version bump. | **RESOLVED** |
| B4 | ROI formula migration orphaned — `loan_pct` undefined, engine transformer not rewired, engine spec untouched | §Problem Statement (line 14) and §Cross-Source Integration Notes (lines 366–372) now explicitly scope the formula change to the follow-up spec `roi-formula-cost-of-attendance.md` (sequential). `debt_median` remains the active ROI driver for this spec. §Zone 3 scope note (line 237) restates: "The ROI-formula wiring … is **out of scope for this spec**." This is option (a) from the first-pass Path to APPROVED — the recommended path for the hackathon timeline. No engine-transformer change, no `loan_pct` definition needed at this gate. | **RESOLVED (scope-down)** |
| B5 | 3 Gold data models for `gold-career-outcomes-college-scorecard` must be updated | §Governance Artifacts Produced at Gold (line 313) calls out "Updated conceptual / logical / physical data models under `governance/models/gold-career-outcomes-college-scorecard-*.md` (additive — 7 new attributes on the `CareerOutcomes` entity; Mermaid `erDiagram` and DDL blocks updated)". Model update is now a named deliverable. | **RESOLVED (spec gate)** — actual model edits happen during implementation; post-review will verify the files changed. |
| B6 | Business glossary: terms needed for `institution_control`, `tuition (in/out)`, `room_board`, `net_price_4yr` | §Governance Artifacts (line 314) names the four missing terms explicitly and assigns `@data-steward` at the Gold pipeline's glossary step. BT-110/111/112 reuse is acknowledged. | **RESOLVED (spec gate)** — glossary additions happen at implementation; post-review will verify. |
| B7 | No §Governance Artifacts section enumerating downstream outputs | Full §Governance Artifacts Produced at Gold section (lines 309–321) enumerates: updated models (×3), new/updated glossary terms, updated data contract with 2 CDE flags + minor version bump, updated data dictionary (7 entries), DQ rules file (9 `GLD-CSI-*` rules), DQ scorecard, lineage event naming **two** Silver inputs, updated CDE registry (+2), chaos-manifest update with two specific chaos cases (corrupt a `net_price_annual`, corrupt institution row count). | **RESOLVED** |

## Resolution Matrix — Advisories (A1–A5)

| ID | Original advisory | Status in updated spec |
|----|-------------------|------------------------|
| A1 | §Success Criteria line 4 named only one column; should list all 7 | **RESOLVED** — line 62 now enumerates all 7: `net_price_annual`, `cost_of_attendance_annual`, `net_price_4yr`, `institution_control`, `tuition_in_state`, `tuition_out_of_state`, `room_board_on_campus`. |
| A2 | `promoted_at` refresh semantics not explicit | **RESOLVED** — §Enrichment Mode note #6 (line 278): "`promoted_at` timestamp refreshes to the new promotion time on all rows — this is consistent with the idempotent promote pattern and is not data drift." |
| A3 | `net_price_annual` ≥80% non-null threshold unvalidated | **MATERIALLY MITIGATED** — GLD-CSI-005/006/007 are all labeled "threshold **calibrated during EDA** after first real join", with a pre-calibration target of ≥60% that matches the conservative end of the A3 coverage range. Risk of a spurious post-hoc relaxation is low. Remains technically advisory — actual calibration happens at EDA. |
| A4 | 4,170 UNITID cardinality not independently verified | **UNCHANGED (non-blocking)** — still an EDA step. §Enrichment Mode note #5 cites the `4,170 − 3,039 = 1,131` figure inline, so the implementing agent has a clear verification target. |
| A5 | MCP `get_school_programs` silently returns real `institution_control` post-enrichment | **DEFERRED TO POST-REVIEW** — not a pre-implementation concern; post-review will verify MCP spec update and test case addition. |

---

## Pre-Implementation Checklist — Re-Verified

| # | Item | Pass | Notes |
|---|------|------|-------|
| 1 | Clear problem statement and success criteria | PASS | Problem statement rewritten to match the scoped-down deliverable; success criteria now lists all 7 columns plus DQ rule count, contract update, model updates, glossary updates, and lineage update (7 criteria total, line 56–68). |
| 2 | Input data sources identified with paths | PASS | Same as first review. |
| 3 | Output artifacts defined with paths and formats | PASS | §Enrichment Mode fully specifies — was PARTIAL, now PASS. |
| 4 | Transformations described | PASS | New CTE SQL + LEFT JOIN key + null-propagation behavior + row-count invariant + schema evolution all specified. |
| 5 | Zone assignment correct | PASS | Unchanged. |
| 6 | Primary implementation agent identified | PASS | Unchanged. |
| 7 | DQ rule categories specified | PASS | 9 rules, proper P0/P1/P2 mix, all named and ID'd — was PARTIAL, now PASS. |
| 8 | CDE mapping impact assessed | PASS | Inline CDE column with rationales — was FAIL, now PASS. |
| 9 | Lineage scope defined | PASS | §Governance Artifacts calls out the new lineage event with **two** Silver inputs superseding the prior single-input event — was PARTIAL, now PASS. |
| 10 | Breaking changes to existing schemas flagged | PASS | Schema axis: no change. Semantic axis: `debt_median` explicitly remains the ROI driver for this spec (scope-down resolves the semantic breakage concern) — was PARTIAL, now PASS. |
| 11 | Testing approach defined | PASS | DQ coverage at Gold is explicit, unmatched-UNITID pattern rule gives a golden-case check, row-count invariant is a hard P0 gate — was FAIL, now PASS. |

### Data Model Gate (Backfill on existing Gold table)

| # | Item | Pass | Notes |
|---|------|------|-------|
| 12 | Conceptual model will be updated with 7 new columns | PASS (spec gate) | Named deliverable in §Governance Artifacts. Post-review verifies. |
| 13 | Logical model will be updated | PASS (spec gate) | Same. |
| 14 | Physical model will be updated | PASS (spec gate) | Same. Mermaid `erDiagram` + DDL blocks explicitly called out. |
| 15 | Mermaid erDiagram consistency | N/A at this gate | Verified at post-review. |

### Insight Traceability

The 2026-04-06 Silver→Gold insight report recommendation on `institution_control` is now **explicitly closed** by GLD-CSI-007 (coverage rule with inline note: "**Validates the 2026-04-06 insight-report recommendation that `institution_control` be surfaced**"). This is exactly the pattern that was missing from sec_edgar_grist and is the right way to close an insight loop.

---

## Issues Found — Re-Review

No blockers. No CHANGES REQUESTED. Advisories below are all carry-over from the first pass and are non-blocking at the pre-implementation gate.

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| A3 | ADVISORY (carry-over, materially mitigated) | `net_price_annual` / `cost_of_attendance_annual` / `institution_control` non-null thresholds are pre-calibrated to ≥60% and explicitly labeled "calibrated during EDA". Implementing agent should run the coverage query during Gold EDA and commit the final thresholds into the DQ rules file before scorecard execution. | Run coverage query during EDA; commit final thresholds. Non-blocking. |
| A4 | ADVISORY (carry-over) | The `4,170 − 3,039 = 1,131` unmatched-UNITID arithmetic should be verified against `SELECT COUNT(DISTINCT unitid) FROM consumable.career_outcomes` before committing GLD-CSI-008's `± 10%` tolerance. | Verify during EDA. Non-blocking. |
| A5 | ADVISORY (carry-over, deferred) | MCP `get_school_programs` silently unlocks real `institution_control` values post-enrichment. MCP spec (`docs/specs/mcp-futureproof-core.md`) should document the capability change and add a test case. | Flag for post-review and `@staff-engineer`. Non-blocking at this gate. |

---

## Decision Rationale

**Why APPROVED:**

1. **B4 scope-down is the right call.** The follow-up spec pattern (`roi-formula-cost-of-attendance.md`) lets this spec ship the columns cleanly without dragging in an engine-transformer signature change, a `loan_pct` definition exercise, and a cascade through `program_career_paths` (626K rows). The Problem Statement is now internally consistent — it lands data, it enables the formula change, it doesn't implement the formula change. All three claims are now true.

2. **B1–B3 and B5–B7 are concretely addressed.** Every blocking item has a specific line-number reference in the updated spec. The §Enrichment Mode subsection is the kind of implementation-ready detail that the first pass was missing across the board. The 9-rule DQ suite is above the minimum and correctly calibrated (60% pre-EDA threshold, not 80%).

3. **Insight traceability closed.** GLD-CSI-007 has an inline comment naming the 2026-04-06 insight report as the origin of the rule. This is the first time in this project's history that an insight-report recommendation has been closed with an explicit validating DQ rule. Worth noting for the audit trail.

4. **Scope is well-bounded.** 7 nullable columns, 1 LEFT JOIN on a proven key (unitid, same source provider), 69,947-row invariant, no grain change, no existing-column changes. The risk profile is low and the validation surface (9 DQ rules + row-count invariant + existing GLD-CO-* regression gate) is high.

**Why not held for advisories:**

A3/A4/A5 are all EDA- or post-review-bounded. A3 has been materially mitigated by the spec author's explicit "calibrated during EDA" language and a 60% pre-calibration target that sits at the conservative end of the range I flagged in the first pass. Holding a spec at pre-implementation for EDA-step items would be an overreach.

---

## Path to Post-Implementation Gate

Implementation can proceed. At post-review, I will verify:

1. `src/gold/college_scorecard_career_outcomes.py` contains the `institution` CTE and the LEFT JOIN per §Enrichment Mode note #2–#3.
2. `consumable.career_outcomes` row count is exactly 69,947 (or whatever the current production count is — verified against pre-enrichment baseline).
3. All 7 new columns present in the Iceberg schema; all nullable.
4. 9 `GLD-CSI-*` rules exist at `governance/dq-rules/gold-career-outcomes-college-scorecard.json` and have been **executed against real Iceberg data** (not test data) with results in `governance/dq-results/`. P0 rules pass. P1 rules with "calibrated during EDA" have their thresholds committed.
5. Data contract `governance/data-contracts/consumable-career-outcomes.yaml` has the 7 new columns with `net_price_annual` and `cost_of_attendance_annual` flagged `is_cde: true` with inline rationales. Minor version bumped.
6. 7 new entries in `governance/data-dictionary.json`.
7. 3 model files (`gold-career-outcomes-college-scorecard-{conceptual,logical,physical}.md`) updated; Mermaid `erDiagram` blocks render; physical DDL matches implementation.
8. Business glossary: 4 new/reused terms for `institution_control`, `tuition`, `room_board`, `net_price_4yr`. APPROVED status.
9. New lineage event naming **two** Silver inputs.
10. Updated CDE registry (+2).
11. Chaos manifest covers the 2 specified cases.
12. GLD-CO-* regression gate still passes (all existing rules on `consumable.career_outcomes`).
13. MCP `get_school_programs` returns non-null `institution_control` for known institutions (A5 follow-up).

---

## Audit Trail (Re-Review)

Filed: 2026-04-16T20:00:00Z.
Reviewer: @governance-reviewer.
Spec: `docs/specs/raw-ingest-college-scorecard-institution.md` §Zone 3.
Prior verdict: CHANGES REQUESTED (B1–B7 blocking). All 7 resolved. A1/A2 resolved. A3 materially mitigated. A4/A5 deferred as non-blocking.
Verdict: **APPROVED**.
Next reviewer action: Post-implementation review after Gold transformer runs, DQ rules execute, and governance artifacts are produced.

---

---

## ORIGINAL REVIEW (2026-04-16T18:30:00Z) — preserved for audit history

# Governance Review: raw-ingest-college-scorecard-institution (Gold zone)

**Review Type:** Pre-Implementation (Gold zone — Zone 3 of `raw-ingest-college-scorecard-institution`)
**Reviewer:** @governance-reviewer
**Date:** 2026-04-16
**Spec:** `docs/specs/raw-ingest-college-scorecard-institution.md` (§Zone 3 — Gold)
**Parent gate status:** Bronze COMPLETE (13/13 DQ PASS against real Iceberg), Silver APPROVED 2026-04-16 (23/23 DQ PASS against real Iceberg), Silver advisory A3 CLOSED.
**Verdict:** **CHANGES REQUESTED**

---

## Executive Summary

The Gold zone scope for this spec is a **schema backfill** of the existing `consumable.career_outcomes` table (69,947 rows, grain `unitid × cipcode × credential_level`) via LEFT JOIN to the newly-materialized `base.college_scorecard_institution` (3,039 rows, grain `unitid`). Seven nullable columns are added; no existing column is renamed, retyped, or removed. The backward-compatibility claim is credible *on the schema axis*.

However, the Gold section of the spec is **under-specified on the dimensions that matter most for a Gold enrichment**, and — separately — the most important downstream claim in the spec's own Problem Statement (the ROI formula change `earnings / debt_median → earnings / (net_price × 4 × loan_pct)`) is **not implemented, not bounded, and not verifiable** as currently written. The engine transformer (`src/gold/futureproof_engine.py`) computes ROI from `debt_to_earnings_annual`, and the spec says nothing about rewiring it. A pre-implementation review cannot approve a Gold enrichment whose stated business purpose is untraceable to any concrete derivation, DQ rule, or downstream consumer change.

Four blocking gaps (B1–B4) must be resolved before implementation begins. Three additional CHANGES REQUESTED items (B5–B7) cover DQ coverage, CDE flagging, and the governance artifact checklist. Advisory items (A1–A5) are documented but non-blocking.

**Estimated remediation effort:** ~2 hours of spec edits; no pipeline re-run required.

---

## Checklist Results — Pre-Implementation Gate

### Standard pre-implementation checklist

| # | Item | Pass | Notes |
|---|------|------|-------|
| 1 | Clear problem statement and success criteria | PASS | Problem statement is strong; success criteria list includes the Gold column addition (§Success Criteria line 4). |
| 2 | Input data sources identified with paths | PASS | Gold inputs: `base.college_scorecard_institution` (Silver, just materialized, 3,039 rows) + `base.college_scorecard` (Silver, 69,947 rows, already consumed by existing transformer). |
| 3 | Output artifacts defined with paths and formats | PARTIAL | Output table named (`consumable.career_outcomes`) but **mode of update** unspecified: does the transformer re-run end-to-end, or is this an additive ALTER TABLE? See B1. |
| 4 | Transformations described | PARTIAL | §Zone 3 names seven new columns and says "LEFT JOIN on unitid". No SQL, no null-propagation rules, no ordering/dedup behavior, no handling of multi-credential rows where institution data is the same. See B1. |
| 5 | Zone assignment correct | PASS | Consumable (Gold) is the correct zone for a product-facing enrichment. |
| 6 | Primary implementation agent identified | PASS | `@primary-agent` per §Agent Workflow step 7 ("Update Gold engine spec to LEFT JOIN new table"). |
| 7 | DQ rule categories specified | PARTIAL | Four rules listed at §250. See B2 — insufficient coverage. |
| 8 | CDE mapping impact assessed | **FAIL** | No CDE flags proposed for any of the 7 new columns. See B3. The existing contract flags `earnings_1yr_median`, `debt_median`, `debt_to_earnings_annual`, `program_value_index`, and all percentile bands CDE. `net_price_annual` drives an ROI formula change per the spec's own Problem Statement and is materially more load-bearing than `debt_median` becomes after the change. |
| 9 | Lineage scope defined | PARTIAL | No explicit statement that the existing lineage event for `consumable.career_outcomes` is superseded vs. a new event. See B7. |
| 10 | Breaking changes to existing schemas flagged | PARTIAL | §Zone 3 line 248 asserts "all current fields on `consumable.career_outcomes` are preserved". True on the schema axis. But **semantic breakage is unaddressed**: `debt_median`'s documented role in the contract (BT-011 CDE, "Primary business metric for student debt exposure … feeds debt-to-earnings ratio … program value index") changes if the ROI formula migrates to `net_price × 4 × loan_pct`. See B4. |
| 11 | Testing approach defined | **FAIL** | Zero test guidance in §Zone 3. No golden rows, no null-propagation cases, no coverage expectation for the 4,170-vs-3,039 UNITID gap. |

### Data Model Gate (Base/Gold — Backfill Mode)

This is a **Gold enrichment of an already-modeled table**, not a greenfield Gold spec. The existing `gold-career-outcomes-college-scorecard-*.md` models (conceptual, logical, physical) are in place and APPROVED. The enrichment must **update** those models, not re-derive them. Currently:

| # | Item | Pass | Notes |
|---|------|------|-------|
| 12 | Conceptual model updated with 7 new columns | **FAIL** | `governance/models/gold-career-outcomes-college-scorecard-conceptual.md` does not reference `net_price_annual`, `cost_of_attendance_annual`, or `institution_control`. See B5. |
| 13 | Logical model updated | **FAIL** | `governance/models/gold-career-outcomes-college-scorecard-logical.md` — same. |
| 14 | Physical model updated | **FAIL** | `governance/models/gold-career-outcomes-college-scorecard-physical.md` — same. DDL block will not match the post-enrichment Iceberg schema. Per the completeness checklist, physical model must match implementation. |
| 15 | Mermaid erDiagram present and consistent | N/A at this gate | Must be updated in B5. |

### Insight traceability

The 2026-04-06 Silver→Gold insight report (`governance/insights/silver-to-gold-insights.md`) line 93 explicitly flags the `institution_control` gap as **"Should be addressed before or alongside Gold implementation"** and recommends "Re-run raw ingestor to include CONTROL field from source CSV. Alternatively, join IPEDS Institutional Characteristics data on unitid." This spec's Gold enrichment **is** the recommended remediation. This is good — it closes a known insight. What is missing is an explicit DQ rule validating that the recommendation was implemented correctly (see B2). Per governance policy, every relevant recommendation in an Insight Report needs a validating DQ rule; absence of that rule is the exact failure mode that caused the sec_edgar_grist period disambiguation bug.

---

## Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| B1 | **CHANGES REQUESTED** | §Zone 3 omits the enrichment mode and the join/dedup SQL. Does the transformer re-run `derive_gold_rows()` end-to-end with an extended `GOLD_SQL`, or does it execute an additive `ALTER TABLE` + backfill UPDATE? The existing transformer is a full recompute via `promote()` — the idempotent pattern requires re-running the full SQL. The spec must state: "the existing transformer is extended to LEFT JOIN `base.college_scorecard_institution` as a new CTE prior to the final SELECT; `promoted_at` is refreshed; the full idempotent promote pattern re-runs." | Add an "Enrichment mode" subsection to §Zone 3 naming the transformer file (`src/gold/college_scorecard_career_outcomes.py`), the insertion point (new CTE `institution` after `cip_bands`), the LEFT JOIN key (`b.unitid = i.unitid`), and a note that the 69,947 row count is expected to be preserved exactly (no row drops, just column additions with nulls where no institution match). |
| B2 | **CHANGES REQUESTED** | DQ coverage at §250 is 4 rules; all are range/non-null checks on `net_price_annual`. **Five critical coverage gaps:** (a) no rule on `cost_of_attendance_annual` (≥80% non-null target from Silver is not re-asserted at Gold); (b) no rule on `institution_control` coverage (the insight report explicitly flagged this as a 100%-null gap — a Gold rule is the only way to verify the fix didn't silently regress); (c) no rule asserting row count is preserved exactly (`count(*) = 69,947 ± 0%` — the LEFT JOIN can go wrong if the institution-side grain breaks); (d) no rule on the `(4170 total UNITIDs in career_outcomes) − (3,039 matched UNITIDs) = 1,131 unmatched UNITIDs` expected null pattern; (e) no rule that `net_price_4yr = net_price_annual × 4 ± $1` is preserved at Gold (Silver enforces this; Gold must re-assert since the field is carried, not recomputed — or the spec must explicitly note Gold inherits the Silver invariant). | Add ≥5 Gold DQ rules covering each of (a)–(e). Minimum 2 P0 (row-count preservation, `net_price_annual ≤ cost_of_attendance_annual`), 3 P1. |
| B3 | **CHANGES REQUESTED** | No CDE/PII assessment for the 7 new columns. Per the spec's own Problem Statement, `net_price_annual` is the **new ROI formula driver**, which is the central business metric of the product. `program_value_index` and `debt_to_earnings_annual` are both flagged CDE in the current contract with rationales that explicitly cite ROI/affordability. `net_price_annual` in the post-enrichment state is at minimum as load-bearing as those fields — arguably more so, since the spec says `debt_median`'s role *demotes* to "reference/comparison" (line 14, 248, 311). The contract update described at §Data Contract Update (lines 258–263) lists only "Added … via LEFT JOIN" without touching the `is_cde` flag on any new column. | Explicitly assess CDE for: `net_price_annual` (recommend **CDE**), `cost_of_attendance_annual` (recommend **CDE** — sticker-price reference driving `net_price_annual ≤ cost_of_attendance_annual` invariant), `institution_control` (recommend non-CDE categorical with rationale), 4 remaining raw cost fields (recommend non-CDE display-only). Add CDE rationales inline in §Zone 3. |
| B4 | **CHANGES REQUESTED** | **The ROI-formula change is orphaned.** §Problem Statement (line 14) and §Cross-Source Integration Notes (line 310) assert the formula migrates to `earnings / (net_price × 4 × loan_pct)`. But: (i) `loan_pct` is undefined, not sourced, not in the schema; (ii) the engine transformer `src/gold/futureproof_engine.py` computes `compute_stat_roi(debt_to_earnings_annual)` from `debt_median / earnings_1yr_median` and has no pathway to consume `net_price_annual`; (iii) `docs/specs/gold-futureproof-engine.md` §ROI Stat Derivation (line 157) defines the formula in terms of debt-to-earnings; (iv) the data contract for `consumable.career_outcomes` documents `debt_to_earnings_annual` as the ROI metric (BT-019, is_cde: true). Either this Gold spec changes the ROI formula wiring or it does not. If it **does**, the engine spec needs a dependent update and the post-implementation gate will fail until that update lands; if it **does not**, the Problem Statement is misleading and must be rewritten to say "enables a future formula change" not "enables the formula change". | Either (a) mark the formula migration as **out of scope** in §Zone 3 with a pointer to a follow-up spec, or (b) define `loan_pct` (source? default? user-input?), add it to the schema or resolve it explicitly as a runtime parameter, update `gold-futureproof-engine.md` with the new `compute_stat_roi()` signature, and add a DQ rule on the new ratio. Option (a) is strongly preferred for this spec's scope and estimate. |
| B5 | **CHANGES REQUESTED** | The three data models for `gold-career-outcomes-college-scorecard` (conceptual, logical, physical) are not updated. Per the Gold completeness checklist, physical model must match implementation; adding 7 Iceberg columns without updating the physical model creates drift the post-review will block on. | Update all three models (conceptual refs the new business terms BT-110/111/112; logical adds the 7 attributes on `CareerOutcomes`; physical updates the DDL and Mermaid `erDiagram`). This is a ~30 min edit. Can happen in parallel with or before implementation. |
| B6 | **CHANGES REQUESTED** | Business glossary: BT-110/111/112 are defined in §Zone 2 (Silver, lines 222–226) and land in the Silver-scope glossary, but they are **equally** Gold business terms now. The Gold contract currently references BT-001 through BT-026; the 7 new columns will need business_term entries. BT-110/111/112 cover the new *surfaced* concepts but there is no glossary term for `net_price_4yr`, `tuition_in_state`, `tuition_out_of_state`, `room_board_on_campus`, or `institution_control`. | Confirm BT-110/111/112 are project-approved (they currently appear in `governance/business-glossary.json`; if not APPROVED, `@data-steward` runs pre-implementation). Add ≥3 new terms or reuse existing ones: 4-year net price, tuition (in-state/out-of-state), room and board, institution control. |
| B7 | **CHANGES REQUESTED** | No mention of lineage update. The existing lineage event at `governance/lineage/gold-career-outcomes-college-scorecard-*.json` names `base.college_scorecard` as the sole input. Post-enrichment it must name **two** Silver inputs. | Add a §Governance Artifacts section to §Zone 3 listing: new lineage event (2 inputs), updated data contract (7 new columns, CDE flags), updated data dictionary entries (7 rows), updated physical model DDL, updated CDE registry count, updated DQ rules and scorecard. |
| A1 | ADVISORY | §Success Criteria line 4 says "Gold update: `consumable.career_outcomes` gains `net_price_annual` column" — **only one column named**. §Zone 3 lists seven. Minor drafting inconsistency. | Update the success criterion to list all 7 columns. Non-blocking but trivially fixable. |
| A2 | ADVISORY | Spec says at §Zone 3 "existing columns unchanged" but does not explicitly preserve `promoted_at` semantics. If the transformer re-runs end-to-end (expected behavior per B1), `promoted_at` refreshes to the new promotion time for all 69,947 rows — this is correct and consistent with the idempotent promote pattern, but worth noting so the next consumer doesn't misread it as data drift. | Add a one-line note to §Zone 3 that `promoted_at` is refreshed on re-promotion. |
| A3 | ADVISORY | Coverage math for the LEFT JOIN: the EDA at `docs/sessions/eda-college-scorecard-institution.md` line 34 reports "2,352 of 2,559 field-of-study UNITIDs (91.9%) match institution-level data" (91.9% coverage from the **Silver base** perspective). From the **Gold career_outcomes** perspective (4,170 UNITIDs, not 2,559), the coverage will differ: 4,170 UNITIDs × some match rate. Without running the join, the expected non-null rate on `net_price_annual` could be anywhere from ~55% (if the extra 1,611 UNITIDs in career_outcomes beyond the 2,559 Silver base are mostly associate/certificate-dominant institutions already filtered out of the institution file) to ~91% (if they overlap). The spec's §Zone 3 DQ rule at line 253 says "`net_price_annual` non-null: ≥80% of rows (P1)" — **this threshold is unvalidated**. If actual coverage lands at 55–65%, the rule will fail spuriously and need to be relaxed post-hoc, which is exactly the workflow we try to avoid. | Recommend the dq-rule-writer run a quick coverage query during EDA and set the threshold from real data before implementation, or provisionally label this rule P2/advisory with a note to calibrate after first real run. |
| A4 | ADVISORY | The 4,170-UNITID figure cited in the prompt reflects `consumable.career_outcomes.unitid` cardinality. I did not independently re-verify this against the real Iceberg table. Note for whoever implements: run `SELECT COUNT(DISTINCT unitid) FROM consumable.career_outcomes` to confirm before calibrating the coverage DQ rule in B2(d). | Verify during EDA. Non-blocking at spec gate. |
| A5 | ADVISORY | MCP impact: `src/mcp_server/futureproof_server.py` line 100 declares `institution_control` in the pulled columns for `get_school_programs`, so **surfacing this column is a silent capability unlock** — the MCP tool has been asking for a field that was 100% null. Post-enrichment, real values will flow. This is good, but the MCP spec (`docs/specs/mcp-futureproof-core.md`) should be updated to document the new information content, and the test harness should add a case verifying `institution_control` returns non-null for known institutions. | Non-blocking at this gate; flag for the post-review and for `@staff-engineer` final review. |

---

## Specific Answers to the Review Questions

**1. Is §Zone 3 complete and unambiguous? Are the 7 columns fully defined?**
Partially. Column types, sources, and one-line semantics are given (§Zone 3 table, lines 238–246). Nullability is implied ("LEFT JOIN" → all new columns nullable) but not stated. Join/dedup SQL is absent. Enrichment mode is absent (re-promote vs ALTER + UPDATE). See **B1**.

**2. Is backward-compatibility credible?**
On the **schema axis**: yes. All existing 30 columns are preserved by name and type. The LEFT JOIN cannot drop rows if the join key is only on the right side. On the **semantic axis**: no — see **B4**. `debt_median`'s documented CDE role changes from "primary business metric" to "reference/comparison" but the data contract, the engine transformer, and the engine spec all still treat it as the ROI driver.

**3. Is the ROI formula change well-motivated and traceable?**
Motivation: excellent. The Problem Statement's $60K-school-with-scholarship-vs-$40K-school-no-aid example is the clearest student-finance argument I have seen in this repo. Traceability: **broken**. See **B4**. The formula migration is asserted in three places but implemented nowhere, and `loan_pct` is an undefined free variable. Either scope it out of this spec or wire it through to the engine and its contract.

**4. Are the 4 DQ rules at §250 sufficient?**
No. See **B2**. Five additional rules needed minimum: row-count preservation, `cost_of_attendance_annual` coverage, `institution_control` coverage (closes the insight recommendation), unmatched-UNITID pattern, `net_price_4yr = 4 × net_price_annual` invariant.

**5. Coverage implications of the LEFT JOIN?**
Silver base has 3,039 UNITIDs; `consumable.career_outcomes` has ~4,170 UNITIDs (per prompt; not independently verified — see **A4**). Minimum unmatched = 4,170 − 3,039 = **1,131 UNITIDs without institution data**. Those 1,131 UNITIDs × their cipcode × credlev combinations will have null `net_price_annual`. Depending on how concentrated their program counts are, the row-level null rate could be **~27%** (if the 1,131 unmatched UNITIDs have typical ~16 programs each = ~18,096 / 69,947 rows) or higher/lower. The §253 P1 threshold of "≥80% non-null" should be recalibrated after EDA. See **A3**.

**6. Should `net_price_annual` be flagged CDE?**
**Yes.** See **B3**. By the contract's own CDE criteria (see the `debt_to_earnings_annual` rationale at contract line 354: "Key affordability metric … directly consumed by the MCP layer and product UI"), `net_price_annual` meets the threshold on two independent counts: (i) it is the stated ROI formula driver post-enrichment; (ii) it is directly consumed by the MCP layer via `get_school_programs`. Rationale should explicitly cite both. `cost_of_attendance_annual` should also be CDE — it is the upper-bound invariant partner (`net_price_annual ≤ cost_of_attendance_annual`) and a key display field.

**7. Risks to downstream consumers?**
- **`gold-futureproof-engine`:** See **B4**. The engine does not consume these new columns today. If the ROI formula migrates (per spec), the engine transformer signature changes (breaking change on `compute_stat_roi`). If the ROI formula does not migrate, the spec's Problem Statement is misleading. **The spec must pick one.**
- **MCP server `get_school_programs`:** Already requests `institution_control` which is currently null; post-enrichment it will return real values. **Silent behavior change.** Add an MCP test case (see **A5**).
- **Frontend receipts / CareerCard UI:** The spec says `tuition_in_state`, `tuition_out_of_state`, `room_board_on_campus` are "for display/receipts" — no frontend spec claims this surface exists yet. Either the receipt UI is out of scope for this spec (document that) or a separate app spec is required.
- **`program_career_paths` (626,406 rows, downstream of `career_outcomes`):** The futureproof_engine transformer reads `career_outcomes`; if `debt_median` is semantically demoted (per **B4**), `compute_stat_roi` results may need to be recomputed. **This cascade is not mentioned in the spec.**

**8. Verdict: CHANGES REQUESTED.**

---

## Decision Rationale

**Why CHANGES REQUESTED, not APPROVED:**

1. **B4 is the load-bearing blocker.** The spec's most prominent business justification — the ROI formula change — is described in the Problem Statement and the Cross-Source Integration Notes but has no implementation pathway, no variable definition for `loan_pct`, and no update to the engine spec that actually owns the ROI derivation. A pre-implementation gate that lets this through will ship a Gold enrichment whose stated purpose is unfulfilled. Either scope out the formula change explicitly or wire it through.

2. **B1 is procedurally required.** Every other Gold spec in this repo (`gold-career-outcomes-college-scorecard`, `gold-futureproof-engine`, `gold-onet-profiles`, `gold-occupation-profiles-bls-ooh`) includes a §Transformations subsection with numbered steps. This spec's §Zone 3 is 30 lines and contains zero SQL and zero stepwise description. The implementing agent cannot write the CTE without guessing at insertion points.

3. **B2 is mandated by insight-report traceability.** The 2026-04-06 insight report explicitly flagged `institution_control` as a known gap blocking "institution-type segmentation". The spec closes the gap but does not validate the closure with a DQ rule. Governance policy is clear: every insight recommendation addressed by a spec must have a validating DQ rule, or the post-review blocks. This is exactly the pattern that bit the sec_edgar_grist project.

4. **B3 and B5–B7 are baseline completeness items.** They are fixable in ~30 minutes each; blocking now avoids cascading blocks at the post-review.

**Why not REJECTED:**

The spec is technically and substantively well-conceived. The Bronze and Silver zones are complete, high-quality, and independently verified. The Gold scope is small (LEFT JOIN, 7 columns, no row drops, no grain change). The problems are all at the spec-completeness layer, not the design layer. None of B1–B7 require a change to the underlying architecture; they all clarify or complete what is already implied.

**Why the advisories do not block:**

A1 is a one-word fix. A2 is a one-sentence clarification. A3/A4 are EDA calibration items for the dq-rule-writer, not spec defects. A5 is a post-review concern for the MCP/app layer, not this Gold spec.

---

## Path to APPROVED

1. Resolve **B4** — choose option (a) "formula change out of scope, documented as follow-up" OR option (b) "full formula rewire + engine spec update". Recommend (a) for hackathon timeline.
2. Add the §Enrichment Mode subsection to §Zone 3 covering **B1**: transformer file, insertion point, join key, promote mode, row-count preservation.
3. Expand **B2** with at least 5 additional DQ rules; 2 P0, 3 P1.
4. Add CDE assessment inline at §Zone 3 per **B3**; minimum recommendations: `net_price_annual` CDE, `cost_of_attendance_annual` CDE, `institution_control` non-CDE with rationale.
5. Update the three `gold-career-outcomes-college-scorecard-*.md` models per **B5**. Dispatch `@semantic-modeler` if auto-approval isn't in effect.
6. Confirm or add business-glossary terms per **B6**.
7. Add §Governance Artifacts list per **B7**.
8. Apply A1/A2 fixes inline.

Estimated effort: **~2 hours of spec editing.** No pipeline re-run. No Bronze/Silver rework. Once B1–B7 are resolved, I expect the re-review to issue **APPROVED** quickly.

---

## Artifacts Reviewed (this pre-review)

| Artifact | Path | Role |
|----------|------|------|
| Spec under review | `/Users/jcernauske/code/bright/futureproof-data/docs/specs/raw-ingest-college-scorecard-institution.md` | §Zone 3 = target of this review |
| Existing Gold spec (pattern reference) | `/Users/jcernauske/code/bright/futureproof-data/docs/specs/gold-career-outcomes-college-scorecard.md` | Baseline Gold transformer spec format |
| Engine Gold spec (ROI consumer) | `/Users/jcernauske/code/bright/futureproof-data/docs/specs/gold-futureproof-engine.md` | Where `compute_stat_roi` lives — drives B4 |
| Engine transformer (ROI consumer) | `/Users/jcernauske/code/bright/futureproof-data/src/gold/futureproof_engine.py` | Source of the current ROI wiring |
| Existing Gold transformer | `/Users/jcernauske/code/bright/futureproof-data/src/gold/college_scorecard_career_outcomes.py` | Target of the enrichment |
| Existing Gold contract | `/Users/jcernauske/code/bright/futureproof-data/governance/data-contracts/consumable-career-outcomes.yaml` | Contract to be updated |
| Silver base contract (join right side) | `/Users/jcernauske/code/bright/futureproof-data/governance/data-contracts/silver-base-college-scorecard-institution.yaml` | 3,039 rows, CDE count 26 |
| Silver post-review | `/Users/jcernauske/code/bright/futureproof-data/governance/reviews/silver-base-college-scorecard-institution-post-review.md` | A3 CLOSED confirmation |
| Insight report | `/Users/jcernauske/code/bright/futureproof-data/governance/insights/silver-to-gold-insights.md` | Source of `institution_control` recommendation (line 93) |
| Institution EDA | `/Users/jcernauske/code/bright/futureproof-data/docs/sessions/eda-college-scorecard-institution.md` | Coverage data underlying A3 |
| MCP server | `/Users/jcernauske/code/bright/futureproof-data/src/mcp_server/futureproof_server.py` | Downstream consumer (line 100 — A5) |
| Existing Gold models | `/Users/jcernauske/code/bright/futureproof-data/governance/models/gold-career-outcomes-college-scorecard-{conceptual,logical,physical}.md` | Targets of B5 update |
| Pipeline state | `/Users/jcernauske/code/bright/futureproof-data/governance/pipeline-state/raw-ingest-college-scorecard-institution-pipeline.json` | Gold mode = greenfield, started 2026-04-16T14:30:23Z |

---

## Audit Trail

Filed: 2026-04-16T18:30:00Z.
Reviewer: @governance-reviewer.
Spec: `docs/specs/raw-ingest-college-scorecard-institution.md` §Zone 3.
Verdict: CHANGES REQUESTED (4 blocking, 3 changes requested on governance completeness, 5 advisory).
Next reviewer action: re-review on resubmission after B1–B7 are resolved. Silver gate is APPROVED and unaffected by this verdict.
