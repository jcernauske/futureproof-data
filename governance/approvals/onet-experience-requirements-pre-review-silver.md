# Governance Review: onet-experience-requirements (Silver Zone)

**Review Type:** Pre-Implementation (Silver zone scope only)
**Reviewer:** @governance-reviewer
**Date:** 2026-04-16
**Verdict:** APPROVED (Silver implementation may begin)

---

## Scope of Review

This review covers readiness to proceed with the Silver zone of `docs/specs/onet-experience-requirements.md` — specifically the new Iceberg table `base.onet_experience_profiles` and its transformer `src/silver/onet_experience_transformer.py`. Bronze is closed (APPROVED post-review + staff sign-off). Gold and MCP zones are out of scope and will be gated by their own pre-reviews.

Evidence cross-checked on-disk:
- `docs/specs/onet-experience-requirements.md`
- `governance/models/silver-base-onet-experience-{conceptual,logical,physical}.md`
- `governance/approvals/silver-base-onet-experience-{conceptual,logical,physical}-approval.md`
- `governance/approvals/silver-base-onet-experience-business-terms-approval.md`
- `governance/approvals/onet-experience-requirements-open-decisions.md`
- `governance/dq-rules/silver-onet-experience.json`
- `governance/data-contracts/base-onet-experience-profiles.yaml`
- `governance/data-dictionary.json`
- `governance/business-glossary.json` (BT-117, BT-118 verified present)
- `governance/eda/raw-onet-experience-eda.md`
- `governance/dq-results/raw-onet-experience-2026041{7}-*.json` (Bronze executions)
- `src/silver/onet_transformer.py` (produces `base.onet_occupations`)

---

## Silver Pre-Implementation Checklist

| # | Item | Status | Note |
|---|------|--------|------|
| 1 | Silver transformer scope unambiguous (6 steps) | PASS | §Zone 2 §Silver Transformations enumerates: (a) filter to `scale_id='RW'` AND `element_id='3.A.1'`, (b) weighted-median category with tie-break to lower-numbered, (c) midpoint-table lookup (category 11 = 12.0 years), (d) four-tier derivation with human-approved thresholds, (e) XX-XXXX.XX → XX-XXXX truncation + unweighted-average aggregation, (f) distribution JSON preservation. Each step has a single, deterministic implementation. |
| 2 | Silver schema matches approved logical & physical models | PASS | All 11 fields reconciled: `record_id`, `bls_soc_code`, `experience_category_median`, `experience_years_typical`, `experience_tier`, `experience_category_mode`, `experience_distribution`, `onet_details_averaged`, `suppress_flag`, `source_load_date`, `ingested_at`. Field names, types, nullability (all NOT NULL), and CHECK constraints match across spec §Silver Schema ↔ logical §Attributes ↔ physical §Column Definitions ↔ data contract. CDE flags (3: `bls_soc_code`, `experience_years_typical`, `experience_tier`) align across physical model, data contract, and spec §CDE & PII Assessment. |
| 3 | Known edge cases from Bronze have Silver plan | PASS | Bimodal RW distribution (41-2031 Retail Salespersons, cat 1 = 39.75%, cat 5 = 32.02%): weighted-median walk produces category 5 → years=0.75 → tier='entry'; DQ rule SLV-ONET-EXP-010 asserts tier only (not category). Sum-to-100 tolerance: Bronze rule already enforces ±0.1, Silver inherits clean inputs. Suppression flag propagation: §Derivation Rules specifies `MAX(CASE WHEN recommend_suppress='Y' THEN 1 ELSE 0 END) = 1` logical-OR across contributing details → `suppress_flag BOOLEAN NOT NULL` in Silver. Spec §Test Matrix enumerates 7 edge cases (empty, single-100%, all-suppressed, 50% tie, multi-detail, missing source, known-value spots). |
| 4 | Silver DQ rules calibrated to recalibrated row count (~765) | PASS | Rule SLV-ONET-EXP-001 enforces `[720, 810]`. Contract `row_count_range: [720, 810]`. Physical-model notes (line 55) still say "~867 rows" as narrative text — this is an internal-model inconsistency but the binding artifact (DQ rule + contract volume) is correctly calibrated to the EDA-measured 765. Flagged advisory, not blocking. |
| 5 | Spot-check rules align with real Bronze data | PASS | SLV-ONET-EXP-008 (11-1011=senior, category 11, 12.0 yr), SLV-ONET-EXP-009 (15-1252=mid, category 9, 7.0 yr), SLV-ONET-EXP-010 (41-2031=entry, category 5, 0.75 yr — bimodal) all confirmed against EDA §6. Rule SLV-ONET-EXP-010 carries an explicit EDA-derived warning in its description against writing a `median_category ≤ 3` rule that would fail on real data. |
| 6 | Cross-dependency readiness — `raw.onet_experience` | PASS | Bronze ingest complete (35,998 rows; post-review + staff sign-off APPROVED 2026-04-17). Latest DQ execution: `governance/dq-results/raw-onet-experience-20260417-014651.json`. |
| 7 | Cross-dependency readiness — `base.onet_occupations` | PASS | Produced by `src/silver/onet_transformer.py` (line 487: `logger.info("Transforming base.onet_occupations...")`). Schema defined at line 82; ~798 rows per `silver-base-onet-physical.md`. FK relationship `base.onet_experience_profiles.bls_soc_code → base.onet_occupations.bls_soc_code` (one-to-one-or-zero) documented in logical model §Foreign Key Relationships; intended enforcement is a referential-integrity DQ rule (currently scoped as an advisory — see §Advisories). |

---

## Data Model Gate (Base zone greenfield)

All three Silver models are present, human-approved, and include rendering-valid Mermaid `erDiagram` blocks:

| Stage | Path | Approval | Status |
|-------|------|----------|--------|
| Conceptual | `governance/models/silver-base-onet-experience-conceptual.md` | `silver-base-onet-experience-conceptual-approval.md` | APPROVED (Jeff Cernauske, 2026-04-16) |
| Logical | `governance/models/silver-base-onet-experience-logical.md` | `silver-base-onet-experience-logical-approval.md` | APPROVED (Jeff Cernauske, 2026-04-16) |
| Physical | `governance/models/silver-base-onet-experience-physical.md` | `silver-base-onet-experience-physical-approval.md` | APPROVED (Jeff Cernauske, 2026-04-16) |

Each model references approved glossary terms (BT-117, BT-118) and cites the open-decisions approval for tier thresholds and the category-11 midpoint. Traceability from conceptual → logical → physical is explicit and consistent.

---

## Business Glossary & Decision Pins

- **BT-117 (Related Work Experience)** and **BT-118 (Experience Tier)** — present in `governance/business-glossary.json`; approved via `silver-base-onet-experience-business-terms-approval.md` (2026-04-16).
- **Tier thresholds** (0-1 / 1-4 / 4-8 / 8+ → entry/early/mid/senior) — pinned via `onet-experience-requirements-open-decisions.md` Decision 1; cited by logical model §Tier Thresholds, physical model §Column Definitions, contract `experience_tier.cde_rationale`, and DQ rules SLV-ONET-EXP-005/007/008/009/010.
- **Category-11 midpoint = 12 years** — pinned via open-decisions Decision 2; cited by logical model §Midpoint Mapping, physical model §CHECK bound rationale.
- **Multi-detail aggregation = unweighted average** — pinned via open-decisions Decision 3; cited by both logical and physical models in the derivation-rules tables.

All three pinned values are human-approved before any code is written. No drift risk between transformer logic and DQ rules.

---

## Silver DQ Coverage Summary

10 Silver rules defined in `governance/dq-rules/silver-onet-experience.json`, broken down by dimension:

| Dimension | Count | Rules |
|-----------|-------|-------|
| Volume | 1 (P0) | SLV-ONET-EXP-001 (row count 720–810) |
| Validity | 4 (P0) | 002 (format), 004 (years range), 005 (tier enum), 006 (median range) |
| Uniqueness | 1 (P0) | 003 (bls_soc_code uniqueness) |
| Coverage | 1 (P1) | 007 (all 4 tiers represented) |
| Consistency (spot checks) | 3 (P0) | 008 (11-1011=senior), 009 (15-1252=mid), 010 (41-2031=entry) |

P0/P1 breakdown: 8 P0, 2 P1. Spot checks are deterministic single-row assertions grounded in EDA-measured values.

---

## Issues Found

| # | Severity | Description | Resolution |
|---|----------|-------------|------------|
| 1 | ADVISORY | Physical model narrative says "~867 rows" (line 55) while the binding DQ rule and contract both say `[720, 810]` (~765). The binding artifacts are correct; the model narrative has stale text from the pre-recalibration draft. | Update physical model row-count narrative to `~765` during Silver implementation, or register as a post-implementation doc-cleanup item. Not blocking — DQ will execute against the correct threshold. |
| 2 | ADVISORY | Logical model declares FK `base.onet_experience_profiles.bls_soc_code → base.onet_occupations.bls_soc_code` with "enforcement: Referential integrity DQ rule" — but no such referential-integrity rule exists in the Silver DQ rule set today. | Add a referential-integrity rule (e.g., "every `bls_soc_code` in `onet_experience_profiles` must exist in `base.onet_occupations`") during Silver implementation or immediately post-execution. Low risk in practice (both sides derive from the same O*NET source) but desirable for governance completeness. |
| 3 | ADVISORY | Test matrix §Test Matrix in the spec lists 7 weighted-median edge cases but the chaos-monkey and unit-test execution against these is not yet scheduled in Silver. Bronze chaos already ran and was APPROVED. | Ensure Silver transformer's pytest suite and/or chaos-monkey cycle explicitly cover the 7 cases (empty distribution, single-category-100%, all-suppressed, tie at 50% → lower-numbered, multi-detail averaging, missing source experience, known-value spots). Non-blocking for implementation start; required before Silver post-review. |
| 4 | ADVISORY | Physical model CHECK bound `experience_years_typical <= 15.0` is intentionally looser than the theoretical max of 12.0 (category-11 midpoint) for defensive headroom. This is documented and defensible, but means the Silver CHECK constraint will never be exercised by real data. | No action. Noted for completeness. |

No CHANGES REQUESTED. No REJECTED.

---

## Decision Rationale

Silver readiness is complete. Every hard prerequisite is in place on-disk: three human-approved models with rendering Mermaid, approved glossary terms (BT-117/BT-118), open-decisions approval pinning the three derivation choices that enter both transformer logic and DQ spot-check rules, a 10-rule DQ rule set correctly calibrated to the EDA-measured row count of ~765, a CDE-tagged data contract consistent with the spec's §CDE & PII Assessment, and confirmed cross-dependency availability (`raw.onet_experience` post-Bronze-approval, `base.onet_occupations` produced by the existing `src/silver/onet_transformer.py`).

The six Silver transformation steps are unambiguous, deterministic given clean Bronze inputs, and traceable to the logical/physical models' §Derivation Rules tables. Spot checks are grounded in real Bronze data — the 41-2031 bimodal case in particular is instrumented correctly (asserting tier, not category, avoiding the trap that would have been introduced by a naive `median_category ≤ 3` rule).

Advisory items #1–#4 above can be resolved during or immediately after implementation and do not block the transformer build.

**Verdict: APPROVED (Silver implementation may begin)**

---

## Audit Trail

- Review scope: Silver zone only (Bronze closed with staff-engineer APPROVED; Gold/MCP deferred).
- Review type: Pre-Implementation re-entry for Silver phase (spec was globally APPROVED at Phase 0; this is the Phase 3 readiness gate for `bs:primary-agent` to start the transformer).
- Reviewer: @governance-reviewer
- Date: 2026-04-16
- Artifacts cross-referenced: 13 files across `governance/models/`, `governance/approvals/`, `governance/dq-rules/`, `governance/data-contracts/`, `governance/business-glossary.json`, `governance/eda/`, `governance/dq-results/`, and `src/silver/`.
- Next gate: Silver post-implementation review after `bs:primary-agent` + `bs:dq-engineer` + `bs:chaos-monkey` + `bs:lineage-tracker` complete Phase 3 steps 17–22.
