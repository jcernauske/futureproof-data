# Governance Review: raw-ingest-college-scorecard-institution (Gold-zone enrichment)

**Review Type:** Post-Implementation (Gold zone / CSI enrichment onto `consumable.career_outcomes`)
**Reviewer:** @governance-reviewer
**Date:** 2026-04-16
**Verdict:** **APPROVED**

**Scope:** Gold-zone enrichment wiring `base.college_scorecard_institution` into `consumable.career_outcomes` via LEFT JOIN on `unitid`, adding 6 net-new columns (IDs 32–37), re-sourcing `institution_control` in place (ID 4 preserved), and shipping the 9 GLD-CSI-* DQ rules declared in the spec.

Parent gate: Pre-implementation review APPROVED 2026-04-16 (same day). All B1–B7 blockers resolved prior to implementation.

---

## Summary

| Signal | Claimed | Verified against | Result |
|---|---|---|---|
| Row count preserved at 69,947 | Yes | DuckDB `iceberg_scan` over `data/gold/iceberg_warehouse/consumable/career_outcomes` (version guessing on) | **69,947** — confirmed |
| Column count = 37 | Yes | DuckDB `iceberg_scan` schema | **37** — confirmed |
| Field IDs 1–31 preserved | Yes | Parsed `metadata/00004-*.metadata.json`, diffed vs schema-id 0 | **No renames on IDs 1–31**. IDs 32–37 are the 6 new columns (`net_price_annual`, `cost_of_attendance_annual`, `net_price_4yr`, `tuition_in_state`, `tuition_out_of_state`, `room_board_on_campus`), all `required=false`. `institution_control` remains at ID 4 — confirmed. |
| DQ 51/51 PASS | Yes | `governance/dq-results/gold-career-outcomes-college-scorecard-csi-enrichment-20260416T162106Z.json` (`source: iceberg`, `evidence_hash: 1f57cd28e28b296b`) | `rules_total=51`, `rules_passed=51`, `p0_passed=true`, `p0_failures=[]`, `p1_failures=[]`. `gld_csi_summary.total=9` (9 PASS); `gld_co_summary.total=42` (42 PASS regression — no GLD-CO regressions). |
| Scorecard 25 P0 / 22 P1 / 4 P2 | Yes | `governance/dq-scorecards/gold-career-outcomes-college-scorecard-csi-enrichment-scorecard.md` | Evidence hash `1f57cd28e28b296b`; 25/25 P0 PASS, 22/22 P1 PASS, 4/4 P2 PASS; scorecard built from real Iceberg execution, not test fixtures. |
| Chaos 5 cycles, 45/45 | Yes | `governance/chaos-manifests/gold-career-outcomes-college-scorecard-csi-chaos.md` | 9 scenarios × 5 cycles = 45 invocations, 45 detections, 100%. |
| Cross-artifact CDE count = 13 | Yes | Contract (`cde_summary.cde_count: 13`, 13× `is_cde: true`); data-dictionary.json (`consumable.career_outcomes` = 37 cols, 13 with `is_cde=true`); CDE registry (reports 13 aligned across all three). | **Aligned at 13 in all three places.** This closes the HIGH finding B1 from the adversarial audit (dictionary had been stale at 31 cols / 11 CDEs). |
| Contract v1.0.0 → v1.1.0 | Yes | `governance/data-contracts/consumable-career-outcomes.yaml` | `version: "1.1.0"`; changelog entries for both 1.0.0 and 1.1.0 present. MINOR bump matches CAB classification. |
| CAB: APPROVE WITH CONDITIONS, severity MINOR | Yes | `governance/reviews/raw-ingest-college-scorecard-institution-gold-cab-review.md` | Verdict confirmed; conditions (MINOR bump, cde_count=13, changelog, audit-trail) all landed. |
| Business glossary BT-113/114/115/116 | Yes | `governance/business-glossary.json` | All 4 terms present at lines 1434/1447/1460/1473 with relationships to BT-110/111. |
| Models (conceptual, logical, physical) updated | Yes | `governance/models/gold-career-outcomes-college-scorecard-{conceptual,logical,physical}.md` | All 3 files reference `net_price_annual` / `cost_of_attendance_annual` / `institution_control`; each contains a Mermaid `erDiagram`. Physical matches live Iceberg schema (37 fields). |
| Lineage: 2 Silver inputs, supersedes prior | Yes | `governance/lineage/gold-career-outcomes-college-scorecard-csi-enrichment-20260416T163000Z.json` | `inputs` block lists `base.college_scorecard` and `base.college_scorecard_institution`; `institution_control` column lineage explicitly re-sourced with rationale; prior `gold-career-outcomes-college-scorecard-20260406T220000Z.json` retained (OL events are additive, not destructive). |
| Spec stale estimates (207, 4.55%) corrected | Yes | `docs/specs/raw-ingest-college-scorecard-institution.md` §Enrichment Mode note 5 | Line 277 now cites "207 UNITIDs … 2,559 distinct … 2,352 matched … Row-level null rate … 4.55% each; `institution_control` 2.58% null". Pre-EDA "~1,131" estimate explicitly called out as corrected. This closes audit carry-forward C2. |
| Adversarial audit: APPROVED_WITH_CAVEATS, HIGH resolved | Yes | `governance/reviews/raw-ingest-college-scorecard-institution-gold-adversarial-audit.md` | HIGH finding (B1 dictionary staleness) is resolved — dictionary now at 37/13. MEDIUM C1 (contract description of `institution_control` still reads "~55-80%" at L86; "~1,131" still at L489) is **carry-forward**, explicitly "may merge; close in a subsequent chore". See Advisory A1 below. |

---

## Checklist Results

### Post-Implementation Governance Completeness

- [x] **Lineage:** OL event `gold-career-outcomes-college-scorecard-csi-enrichment-20260416T163000Z.json` exists, names both Silver inputs, and provides column-level `inputFields` + `transformationDescription` for each of the 37 output columns including the re-sourced `institution_control`.
- [x] **DQ Rules:** `governance/dq-rules/gold-career-outcomes-college-scorecard.json` covers both legacy GLD-CO-* (42 rules) and new GLD-CSI-* (9 rules) families.
- [x] **DQ Execution:** Executed against the real Iceberg table (`source: iceberg`, warehouse path recorded, `executed_at: 2026-04-16T16:21:06Z`).
- [x] **DQ P0 Gate:** `p0_passed=true`; 25/25 P0 PASS with `p0_failures=[]`.
- [x] **DQ Scorecard:** Produced from the real execution (`evidence_hash=1f57cd28e28b296b`), not fixtures.
- [x] **Chaos hardening:** 5 cycles, 45/45 detections (100%), exit condition satisfied.
- [x] **CDE/PII Tags:** 13 CDE flags set on the contract; 0 PII (contract: `cde_summary.pii_count: 0`). 2 new CDEs (`net_price_annual`, `cost_of_attendance_annual`) per spec §Zone 3; 5 new non-CDEs rationalized in registry.
- [x] **Data Dictionary:** `consumable.career_outcomes` has 37 column entries, 13 with `is_cde=true`. The 7 newly-added field names are all present.
- [x] **Data Contracts:** `consumable-career-outcomes.yaml` at v1.1.0 with cde_count=13 and changelog entry for this update.
- [x] **Audit Trail:** Entries present for this spec on 2026-04-16 — `lineage-tracker`, `doc-generator`, `dq-engineer` (bronze+silver lineage), plus CAB approval and prior review history.
- [x] **Schema Changes:** Match the spec's §Zone 3 ADD-COLUMN declarations (6 new nullable) and in-place re-source of `institution_control` (not a new column). Iceberg `required=false` on IDs 32–37, and `institution_control` remains at ID 4.
- [x] **Data Models (Gold):** All 3 stages updated; each carries a Mermaid `erDiagram`. Physical reflects live schema.
- [x] **No Orphaned Artifacts:** Dictionary, contract, CDE registry, models, and lineage all reference the same 37 column names as the live Iceberg table.
- [x] **Consistency:** CDE counts agree at 13 across contract / dictionary / registry. Column names agree across contract / dictionary / lineage / physical model / live Iceberg.

### Insight Traceability (Silver → Gold)

The 2026-04-06 insight report recommended surfacing `institution_control` (previously 100% null on `consumable.career_outcomes`). This update:

- [x] **Implementation:** `institution_control` re-sourced from `base.college_scorecard_institution` via LEFT JOIN on unitid; post-enrichment coverage 97.42%.
- [x] **Validation:** `GLD-CSI-007` (completeness threshold) and `GLD-CSI-009` (value-set enforcement: {Public, Private nonprofit, Private for-profit}) both PASS. Row-level null rate 2.58% as documented in the EDA session.

Loop closed.

### CAB Conditions Met

| Condition | Status |
|---|---|
| MINOR bump 1.0.0 → 1.1.0 | **Done** — `version: "1.1.0"` in contract. |
| `cde_summary.cde_count: 13` | **Done** — present at line 675. |
| Changelog entry with justification | **Done** — v1.1.0 entry visible at line 708. |
| Audit-trail entry for CAB decision | **Done** — present in `governance/audit-trail/`. |

### Adversarial Audit Blockers

| ID | Severity | Status |
|---|---|---|
| B1 — Dictionary stale at 31 cols / 11 CDEs | HIGH | **RESOLVED** — dictionary now 37 / 13 verified. |
| C1 — Contract description of `institution_control` still reads "~55-80%" + "~1,131" | MEDIUM | **Carry-forward** per adversarial auditor's own wording ("may merge; close in a subsequent chore"). Filed as Advisory A1 below. |
| C2 — Spec §Enrichment Mode note 5 | LOW | **RESOLVED** — spec now cites 207/4.55%/2.58%. |
| C3 — Optional P2 co-null sentinel | LOW | Carry-forward (advisory only). |
| C4 — Fixture-based integration smoke test | INFO | Carry-forward (advisory only). |

---

## Issues Found

| # | Severity | Description | Resolution Required |
|---|---|---|---|
| A1 | ADVISORY | Data contract `consumable-career-outcomes.yaml` still contains two pre-EDA comments: L86 ("~55-80% non-null") in the `institution_control` description, and L489 ("~1,131") in the header comment for the enrichment block. Adversarial audit classified these as MEDIUM carry-forward. Actual values are 97.42% coverage and 207 unmatched UNITIDs. | Open a follow-up chore to rewrite both comments with measured values. Non-blocking — contract *structure* (cde_summary, columns, constraints, changelog) is correct; only the inline prose is stale. |
| A2 | ADVISORY | Audit carry-forward C3 (optional P2 `GLD-CSI-012` co-null sentinel for `net_price_annual` vs `cost_of_attendance_annual` asymmetry) is not implemented. The existing P1 pair will pass/fail in lockstep. Value is marginal given the 100% chaos detection rate. | Optional; file as a nice-to-have if operational incidents suggest the asymmetry is a real failure mode. |

No CHANGES REQUESTED. No REJECTED items. No P0 failures. No GLD-CO regressions. All cross-artifact consistency checks reconcile.

---

## Decision Rationale

The implementation matches the spec byte-for-byte on the quantitative claims that determine correctness: 69,947 rows preserved, 37 columns, field IDs 1–31 unchanged, IDs 32–37 nullable and correctly named, `institution_control` re-sourced in place at ID 4. The DQ execution was performed against the real Iceberg table (confirmed via `source: iceberg` and evidence hash on disk), not fixtures, and all 51 rules PASS with the 42 legacy GLD-CO-* rules acting as a clean regression gate. Chaos monkey achieved 100% detection across 5 cycles — the hardening exit condition was satisfied and evidence was kept for all 5 cycles.

The adversarial audit's single HIGH blocker (B1, stale data-dictionary) is resolved: the dictionary now has 37 entries with 13 CDE flags matching the contract and registry. Cross-artifact CDE reconciliation — the exact surface the audit called "WEAK" — is now STRONG. The CAB's MINOR classification was honored end-to-end (v1.1.0 bump, cde_count=13, changelog, audit-trail). The 2026-04-06 insight report recommendation on `institution_control` is closed with both an implementation (97.42% coverage) and a validating DQ rule (GLD-CSI-007 + GLD-CSI-009).

The remaining audit items (C1 contract-prose staleness, C3 optional sentinel, C4 fixture smoke test) are explicitly designated carry-forward by the auditor. C2 (spec prose) is already fixed in §Enrichment Mode note 5, which I verified directly in the spec. The contract's inline L86/L489 comments remain stale — I am logging that as Advisory A1 rather than blocking, because (a) the auditor himself framed it that way, (b) the contract's machine-readable structure is correct, and (c) the accurate numbers exist elsewhere in-repo (EDA session, spec, scorecard) for any consumer who needs them.

No insight traceability gaps. No orphaned artifacts. No P0 failures. The spec is governance-complete and cleared to proceed to @staff-engineer.

**Verdict: APPROVED** (with two non-blocking advisories).

---

## Evidence Ledger

- Live table: `data/gold/iceberg_warehouse/consumable/career_outcomes/metadata/00004-195f7519-7bb6-44ea-9bd5-1ac386bd15d9.metadata.json` (37 fields, IDs 1–31 preserved, IDs 32–37 nullable)
- Live row count: DuckDB `iceberg_scan` with `unsafe_enable_version_guessing=true` → 69,947
- DQ execution: `governance/dq-results/gold-career-outcomes-college-scorecard-csi-enrichment-20260416T162106Z.json` (hash `1f57cd28e28b296b`)
- Scorecard: `governance/dq-scorecards/gold-career-outcomes-college-scorecard-csi-enrichment-scorecard.md`
- Chaos: `governance/chaos-manifests/gold-career-outcomes-college-scorecard-csi-chaos.md` (9 × 5 = 45/45)
- Contract: `governance/data-contracts/consumable-career-outcomes.yaml` (v1.1.0, cde_count=13, 13× is_cde:true)
- Dictionary: `governance/data-dictionary.json` → `tables.consumable.career_outcomes` (37 cols, 13 CDEs)
- CDE registry: `governance/cde-registry/gold-career-outcomes-college-scorecard-cdes.md` (reports 13 aligned)
- Glossary: `governance/business-glossary.json` BT-113/114/115/116 at lines 1434/1447/1460/1473
- Lineage: `governance/lineage/gold-career-outcomes-college-scorecard-csi-enrichment-20260416T163000Z.json` (2 Silver inputs, column-level transforms)
- Models: `governance/models/gold-career-outcomes-college-scorecard-{conceptual,logical,physical}.md` (all 3 with Mermaid erDiagram)
- CAB: `governance/reviews/raw-ingest-college-scorecard-institution-gold-cab-review.md` (MINOR, v1.1.0)
- Adversarial audit: `governance/reviews/raw-ingest-college-scorecard-institution-gold-adversarial-audit.md` (APPROVED_WITH_CAVEATS)
- Pre-review: `governance/reviews/raw-ingest-college-scorecard-institution-gold-pre-review.md` (APPROVED)
- Spec §Enrichment Mode note 5: `docs/specs/raw-ingest-college-scorecard-institution.md:277` (207 / 4.55% / 2.58%)
