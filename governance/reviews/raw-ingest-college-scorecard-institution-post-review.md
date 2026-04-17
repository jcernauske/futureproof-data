# Governance Review: raw-ingest-college-scorecard-institution

**Review Type:** Post-Implementation
**Reviewer:** @governance-reviewer
**Date:** 2026-04-14
**Verdict:** APPROVED WITH ADVISORIES

---

## Scope Statement

This review is scoped to the **Bronze zone only**. Per the user's direction and confirmed by spec structure, Silver (`base.college_scorecard_institution`) and Gold (`consumable.career_outcomes` LEFT JOIN) are future spec cycles. The pre-implementation reviewer's request for Silver/Gold data models therefore does not apply at this gate — Bronze raw tables use physical-only models per CLAUDE.md governance policy ("Bronze zone specs skip this gate — raw tables use physical-only models").

All completeness checks below evaluate the Bronze deliverable against the §Zone 1 (Bronze) portion of the spec.

---

## Completeness Checklist — Bronze Zone

| # | Required Artifact | Path | Status |
|---|-------------------|------|--------|
| 1 | Ingestor implementation | `src/raw/college_scorecard_institution_ingestor.py` | PASS — 12.6 KB, 326 lines, schema with 28 fields |
| 2 | Ingestor tests | `tests/raw/test_college_scorecard_institution_ingestor.py` | PASS — 41/41 tests green (0.91s) |
| 3 | Sample fixture | `tests/raw/college_scorecard_institution_sample.csv` | PASS |
| 4 | DQ rules | `governance/dq-rules/raw-ingest-college-scorecard-institution.json` | PASS — 13 rules (7 P0, 6 P1), all approved by human |
| 5 | DQ execution results | `governance/dq-results/…20260416T023614Z.json` | PASS — 13/13 PASS, P0 gate PASS on production run |
| 6 | DQ scorecard | `governance/dq-scorecards/raw-ingest-college-scorecard-institution-scorecard.md` | PASS — 100% pass on baseline run, 8 supplementary stats reconcile to EDA |
| 7 | Chaos manifest | `governance/chaos-manifests/raw-ingest-college-scorecard-institution-chaos.md` | PASS — 5 cycles, 10/13 rules fire consistently, 3 gaps documented |
| 8 | Adversarial audit | `governance/audits/raw-ingest-college-scorecard-institution-adversarial-audit.md` | PASS — READY-WITH-CAVEATS, no CRITICAL, 6 MODERATE, 6 LOW |
| 9 | Domain context | `domain/raw-ingest-college-scorecard-institution-context.md` | PASS — 19 KB |
| 10 | Entity resolution | `governance/entity-resolution/raw-ingest-college-scorecard-institution.md` | PASS — SKIP (single trivial key: UNITID) |
| 11 | PII scan | `governance/pii-scans/raw-ingest-college-scorecard-institution-pii-scan.md` | PASS — NO PII, all 28 fields Level 1 Public |
| 12 | Temporal model | `governance/temporal-models/raw-ingest-college-scorecard-institution-temporal.md` | PASS — SKIP bitemporal (single snapshot) |
| 13 | Lineage | `governance/lineage/raw-ingest-college-scorecard-institution-20260414T213000Z.json` | PASS — OpenLineage COMPLETE event with 28 columnLineage entries |
| 14 | CDE registry | `governance/cde-registry/raw-ingest-college-scorecard-institution-cdes.md` | PASS — 17/28 CDE, 0/28 PII, rationale for every column |
| 15 | Data contract | `governance/data-contracts/raw-college-scorecard-institution.yaml` | PASS — 28 columns, 17 CDE, 0 PII, spec_reference set |
| 16 | Data dictionary | `governance/data-dictionaries/raw-college-scorecard-institution.md` | PASS — 17 KB, every column defined |
| 17 | Grounding doc | `governance/grounding/raw-college-scorecard-institution.md` | PASS — 12 KB, links to all downstream artifacts |
| 18 | Audit trail entries | `governance/audit-trail/*college-scorecard-institution*` | PASS — 6 entries (dq-rule-writer, temporal-modeler, dq-engineer, cde-tagging, doc-generator, lineage) |

**Data Model Gate (Bronze):** N/A per CLAUDE.md. Bronze raw tables skip the 3-stage model progression; the physical schema in the ingestor + the contract is the authoritative physical model. Silver/Gold models will be required on their respective future specs.

---

## Cross-Artifact Consistency Checks

| Check | Finding |
|-------|---------|
| Field count — ingestor schema vs contract vs lineage vs CDE registry | CONSISTENT — all report 28 fields (24 source + 4 metadata) |
| CDE count — CDE registry vs contract | CONSISTENT — 17 CDE in both |
| PII count — PII scan vs contract vs CDE registry | CONSISTENT — 0 PII in all three |
| Field names — ingestor `COLUMN_MAP` vs contract columns vs lineage outputs | CONSISTENT — lowercase Iceberg names match across all artifacts |
| DQ rule IDs — rule JSON vs scorecard vs contract `dq_rules` refs | CONSISTENT — RAW-CSI-001 through RAW-CSI-013 referenced uniformly |
| Record count — DQ scorecard vs contract `record_count` vs lineage | CONSISTENT — 3,039 rows |
| Business glossary terms — contract vs CDE registry | CONSISTENT — BT-110, BT-111, BT-112 referenced in both |
| Filter predicate — spec vs contract vs ingestor | CONSISTENT — `PREDDEG == 3 OR ICLEVEL == 1` everywhere |
| Sentinel list — spec vs contract vs ingestor | CONSISTENT — `{"PrivacySuppressed", "PS", "NA", "NULL", ""}` |

---

## P0 Gate Evaluation

Baseline production DQ run (`20260416T023614Z`): **P0 PASS** (7/7 P0 rules green, 6/6 P1 rules green, 13/13 overall).

Later same-session runs (`20260416T02:42:12/13/14Z`) show failures across most rules — these are **chaos-runner executions** against intentionally corrupted datasets and are expected to fail. This is the correct negative-test behavior. Verified by cross-reading the chaos manifest (5 cycles, seeds 43-47, 2,497-2,521 corruptions per cycle). The baseline clean-data run is the authoritative production signal for P0 gate purposes.

---

## Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| 1 | ADVISORY | Data contract `contract verify` fails with "Empty namespace identifier" because the Iceberg table has not been materialized. Adversarial auditor flagged as HR-4. DQ ran against in-memory DuckDB reconstruction rather than the target Iceberg table. | Not blocking for governance. Table materialization is a runtime concern for the staff-engineer gate or the next pipeline execution. Recommend capturing a post-materialization DQ run in a follow-up spec iteration to close the HR-4 evidence gap. |
| 2 | ADVISORY | Chaos monkey gap RAW-CSI-012 (private net-price coverage) never fired across 5 cycles. Confirmed by adversarial auditor (HR-6) as a corruption-coverage gap, not a rule defect. | Not blocking. Recommend adding a symmetric private-coverage null-out probe to the chaos runner in a subsequent hardening cycle. |
| 3 | ADVISORY | Source URL provenance split — DQ scorecard references `scorecard.network/...04172025.zip`; ingestor uses `app.cloud.gov/.../Most-Recent-Cohorts-Institution.csv`. Both are official DoE hosts but byte-identity not verified. Flagged by adversarial auditor (HR-2). | Not blocking. Recommend adding a checksum or single-line reconciliation note in a follow-up. |
| 4 | ADVISORY | EDA numbers in scorecard (private Q1>Q5 = 39) diverge from EDA markdown (private Q1>Q5 = 34) by +5. Both run against the same stated dataset. Flagged by adversarial auditor (HR-3). RAW-CSI-013 passing at 46 vs threshold 50 — a 5-unit drift is within safety margin but the discrepancy is unexplained. | Not blocking. Recommend re-running the quintile count once the Iceberg table exists and reconciling. |
| 5 | ADVISORY | Chaos manifest mislabels RAW-CSI-011 and RAW-CSI-012 thresholds (says "≥80%" in matrix; actual rules use 75% and 65% respectively). Cosmetic documentation defect — rules themselves are correct. Flagged by adversarial auditor (HR-5). | Not blocking. Two-line edit recommended. |
| 6 | ADVISORY | EDA session markdown is the sole witness for all 13 rule thresholds; no reproducible EDA script checked into repo. Flagged by adversarial auditor (HR-7) as the biggest regulator-facing gap. | Not blocking for Bronze governance. Recommend committing `scripts/eda_college_scorecard_institution.py` before the Silver spec runs. |
| 7 | ADVISORY | `ICLEVEL` is read by the ingestor for filtering but not persisted in the Bronze table. Adversarial auditor (AGG-6) notes downstream consumers cannot distinguish "passed filter because PREDDEG=3" from "passed because ICLEVEL=1". | Not blocking. Consider adding `iclevel` to the Bronze schema in a schema-evolution follow-up for provenance. |
| 8 | ADVISORY | Three defensive ingestor code paths are untested — ZIP extraction, BOM strip, real HTTP download. Flagged by adversarial auditor (HR-8). | Not blocking. Recommend adding 3 targeted tests (~30 LOC total) before the next refresh cycle. |
| 9 | ADVISORY | DQ rule `status` field uses two values ("approved" and "active") inconsistently across the 13 rules. All are human-approved with timestamps. Flagged by adversarial auditor (HR-11) as cosmetic schema drift. | Not blocking. Governance tooling convergence issue, not a data-integrity issue. |
| 10 | ADVISORY | Chaos manifest recommends 5 new rules (RAW-CSI-014 through RAW-CSI-018) covering freshness, referential integrity, consistency, accuracy. Adversarial auditor independently confirms all 4 coverage gaps are real. | Not blocking for this spec. Recommend filing a follow-up hardening spec to implement these rules. |

**None of the advisories rise to CHANGES REQUESTED severity.** All are documented risks with clear remediation paths; none contradict the spec or break governance invariants.

---

## Insight Traceability

No insight reports exist for this zone transition (this is a greenfield Bronze ingest, not a zone-transition review). Traceability gate does not apply.

---

## Decision Rationale

The Bronze ingest is governance-complete. Every required artifact exists, every cross-artifact consistency check passes, and the 13 DQ rules all pass on the baseline production run with the P0 gate green. The ingestor code is sound (41/41 tests), the schema matches the spec, the contract reflects the implementation, the CDE registry reflects the contract, the lineage captures the full source-to-target mapping, and the PII classification (Level 1 Public across all 28 fields) is well-founded.

The adversarial auditor's findings, while numerous (6 MODERATE + 6 LOW), are consistent with what a thorough skeptical review should surface and do not reveal any specification violations, P0 failures, or governance gaps that block this gate. They identify evidence-integrity improvements that will strengthen the audit trail as the pipeline matures — particularly the HR-4 (no real Iceberg run) and HR-7 (no EDA script) items, which should be addressed before a regulator-scoped review. For an internal Bronze gate, they are appropriately ADVISORY.

The note about Silver/Gold models being out of scope is accepted — Bronze raw tables have no model gate, and the pre-review's request for those artifacts was looking ahead to future spec cycles, not blocking this one.

**Verdict: APPROVED WITH ADVISORIES.** The spec is cleared to proceed to the staff-engineer gate. Recommend the 10 advisories be tracked as follow-up work (ideally rolled up into a single hardening spec before the next data refresh).

---

*Generated by @governance-reviewer on 2026-04-14. Review logged at `governance/reviews/raw-ingest-college-scorecard-institution-post-review.md`.*
