# Governance Review: full-pipeline-ipeds-finance v1.3 (Post-Implementation, Full Pipeline)

**Review Type:** Post-Implementation (Full Pipeline — Bronze + Silver/Base + Gold/Consumable)
**Reviewer:** @bs:governance-reviewer
**Date:** 2026-05-01
**Spec:** `docs/specs/full-pipeline-ipeds-finance.md` v1.3
**Pre-implementation review:** `governance/approvals/raw-ingest-ipeds-finance-pre-review.md` (v1.0 APPROVED + v1.1 delta APPROVED, captured inline in spec §7)
**Bronze post-implementation review:** spec §7 "Post-Implementation Review (Bronze Zone)" (APPROVED 2026-05-01 with two non-blocking CHANGES REQUESTED follow-ups P-1, P-2)

**Verdict:** **APPROVED (full pipeline) — with three carry-forward CHANGES REQUESTED follow-ups, none blocking sign-off.**

The bronze, silver/base, and gold/consumable zones all landed cleanly with the expected schemas, conservation invariants hold across all three zones, all 44 DQ rules pass against live data with the P0 gate green, and the adversarial-auditor's primary close-out artifact (the consumable data contract YAML) was authored and contains all four contract clauses the audit identified as the highest-leverage mitigations for downstream EADA fusion. No HARD blockers. The three follow-ups (one new, two carried forward from the bronze post-review) are cosmetic / process-ledger cleanups that do not block silver→gold progression and do not block the start of `raw-ingest-eada.md`.

---

## §8 Artifact Completeness — 17 of 17 found

| # | §8 item | Path(s) | Status |
|---|---------|---------|--------|
| 1 | EDA report | `governance/eda/raw-ingest-ipeds-finance-eda.md` (full FY2022 EDA) + `governance/eda/raw-ingest-ipeds-finance-preflight.md` (column-code lock-down) + `governance/eda/full-pipeline-ipeds-finance-raw-eda.md` (alias) | PRESENT |
| 2 | Domain context (IPEDS Finance section) | `governance/domain-context.md` § IPEDS Finance Survey | PRESENT |
| 3 | Models — raw (3 stages) | `governance/models/raw-ipeds-finance-{conceptual,logical,physical}.md` | PRESENT |
| 4 | Models — base (3 stages) | `governance/models/base-ipeds-finance-{conceptual,logical,physical}.md` (verified against snapshot `1277941459950591173`) | PRESENT |
| 5 | Models — consumable (3 stages) | `governance/models/consumable-ipeds-finance-profile-{conceptual,logical,physical}.md` (verified against snapshot `6649279885162971471`) | PRESENT |
| 6 | DQ rules — raw | `governance/dq-rules/raw-ipeds-finance.json` (14 rules: 12 P0 + 2 P1) | PRESENT |
| 7 | DQ rules — base | `governance/dq-rules/base-ipeds-finance.json` (19 rules: BSE-IPF-001..017 with 015 split into 015a/b/c) | PRESENT |
| 8 | DQ rules — consumable | `governance/dq-rules/consumable-ipeds-finance-profile.json` (11 rules: 8 P0 + 2 P1 + 1 P2 watch-line) | PRESENT |
| 9 | DQ scorecards + execution results | `governance/dq-scorecards/full-pipeline-ipeds-finance-scorecard.md` (44/44 PASS, run `d16e354a`) + `governance/dq-results/full-pipeline-ipeds-finance-20260501T205324Z.json` + bronze-only result `raw-ipeds-finance-20260501T202737Z.{json,md}` | PRESENT |
| 10 | Chaos report (raw) | `governance/chaos-reports/raw-ipeds-finance-chaos.md` (60/60 in-scope catches; 2 expected misses; 3 P2 follow-ups) | PRESENT |
| 11 | Adversarial audits | `governance/adversarial-audits/raw-ipeds-finance-bronze-audit.md` (CLEAR) + `governance/adversarial-audits/consumable-ipeds-finance-profile.md` (CLEAR for consumable; SOFT-BLOCKED for downstream EADA — see §"Adversarial-audit-recommended contract clauses" below) | PRESENT |
| 12 | Lineage | `governance/lineage/full-pipeline-ipeds-finance-20260501T203128Z.json` (OpenLineage event, 5 inputs / 1 output, full column-lineage) | PRESENT |
| 13 | CDE tagging | `governance/cde-tagging/raw-ipeds-finance.md` (5 CDEs, 0 PII at bronze) + `governance/cde-tagging/consumable-ipeds-finance-profile.md` (10 CDEs evaluated, 9 confirmed flagged in contract; 0 PII) | PRESENT |
| 14 | PII scan | `governance/pii-scans/raw-ipeds-finance-pii-scan.md` (NO PII verdict) | PRESENT |
| 15 | Data contract | `governance/data-contracts/consumable-ipeds-finance-profile.yaml` (status: `draft`; 15 columns documented; SLOs calibrated against live FY2023 baseline) | PRESENT |
| 16 | Data dictionaries | `governance/data-dictionaries/raw-ipeds-finance.md` + `governance/data-dictionaries/base-ipeds-finance.md` + `governance/data-dictionaries/consumable-ipeds-finance-profile.md` | PRESENT |
| 17 | Audit-trail entries | `governance/audit-trail/2026-04-30-data-analyst-full-pipeline-ipeds-finance-raw-eda.md` + `governance/audit-trail/2026-05-01-dq-rule-writer-full-pipeline-ipeds-finance.md` + `governance/audit-trail/raw-ipeds-finance-dq-execution.md` | PRESENT |

**Bonus artifacts present (not on the §8 list, additive governance value):**
- `governance/entity-resolution/raw-ipeds-finance-er-assessment.md`
- `governance/temporal-models/raw-ipeds-finance-temporal-assessment.md`

**Business glossary status — 4 of 6 BT-IPF-* terms landed.** §8 names "6 BT-IPF-* terms (final IDs assigned by @bs:data-steward)." Live `governance/business-glossary.json` carries `BT-IPF-INSTRUCTION-EXPENSES`, `BT-IPF-INSTITUTIONAL-SUPPORT-EXPENSES`, `BT-IPF-ENDOWMENT-VALUE`, `BT-IPF-PER-FTE`. Missing: `BT-IPF-MARKETING-RATIO` and `BT-IPF-DATA-COMPLETENESS-TIER`. Both are referenced by name throughout the consumable data contract, the data dictionary, the CDE tagging artifact, and the consumable models — so the *definitions* are fully written and the consumable-zone artifacts behave consistently. The miss is at the central-glossary registration step. See Issue Q-1 below — **CHANGES REQUESTED (cosmetic, non-blocking).**

---

## Cross-Artifact Consistency — PASS with minor cosmetic drift

| Check | Verdict | Evidence |
|-------|---------|----------|
| Spec §5 base schema (15 fields) ↔ `governance/models/base-ipeds-finance-physical.md` ↔ `governance/data-dictionaries/base-ipeds-finance.md` | MATCH | All three list the same 15 fields with identical types and nullability. Physical model verified against landed Iceberg metadata snapshot `1277941459950591173`. |
| Spec §6 consumable schema (15 fields incl. v1.2 raw expense passthroughs) ↔ `governance/models/consumable-ipeds-finance-profile-physical.md` ↔ `governance/data-dictionaries/consumable-ipeds-finance-profile.md` ↔ `governance/data-contracts/consumable-ipeds-finance-profile.yaml` | MATCH | All four list identical 15 fields; field IDs 7/8/9 carry the v1.2 raw expense passthroughs in the physical model and contract; field ID 14 is `data_completeness_tier`; nullability matches across artifacts. Verified against landed Iceberg metadata snapshot `6649279885162971471`. |
| Spec §6 CDE candidates (5 fields) ↔ `governance/cde-tagging/consumable-ipeds-finance-profile.md` (10 evaluated) ↔ data contract `cde_summary.cde_columns_list` (9 flagged) | MATCH WITH JUSTIFIED EXTENSIONS | Spec §6 names 5 CDE candidates: `marketing_ratio`, `endowment_per_fte`, `institutional_support_per_fte`, `instruction_per_fte`, `data_completeness_tier`. The CDE tagger flagged 4 additional columns: `unitid` (cross-source join anchor — universal IPEDS join key, re-affirmed from the Bronze CDE set), the 3 raw expense passthroughs `instruction_expenses` / `institutional_support_expenses` / `endowment_value` (downstream EADA composite-ratio inputs per spec §6 Transformation 1's narrow exception). The CDE tagger explicitly evaluated `total_fte_enrollment` for CDE flagging (the user prompt suggested 5 added items including FTE) and the data contract did NOT flag it (`is_cde: false`); this is a deliberate non-flag, on the rationale that FTE is the per-FTE-derivation denominator (not itself a downstream consumer-facing signal) — defensible. So the contract carries 9 CDEs (5 from spec + `unitid` + 3 raw expense passthroughs), not 10. The four extensions are all individually rationalized in the CDE tagging file and the contract's `cde_rationale` strings. Approved. |
| DQ rule thresholds ↔ EDA recommendations ↔ live FY2023 measurements | MATCH WITH DOCUMENTED VINTAGE-DRIFT RECALIBRATION | EDA was run against FY2022 (snapshot `982081695100705470`, 2,683 rows). Bronze was re-ingested between EDA pass and DQ rule authorship to FY2023 (snapshot `2955168649587464831`, 2,675 rows) per spec §9 deviation #5. The DQ-rule rationale strings explicitly document the recalibration: BSE-IPF-013 tightened to 70% per EDA (FY2023 measured 74.5% non-null); BSE-IPF-014 tightened to 95% per EDA (FY2023 measured 98.7%); BSE-IPF-015 split per-form into 015a/b/c per EDA's strong recommendation, then thresholds recalibrated FY2022→FY2023 (015a F1A 13→15, 015b F2 5.5→7, 015c F3 11 preserved); CON-IFP-008 P1 floor recalibrated 90%→88% for FY2023 (measured 88.71%); CON-IFP-008b P2 watch-line added per EDA (200-bp gap below P1) at 86%; CON-IFP-009 high-tier floor preserved at 70% per explicit EDA recommendation (FY2023 measured 74.7%). Rationale-strings make the EDA-vs-FY2023 deltas auditable. |
| Data contract SLOs ↔ DQ rule thresholds | MATCH | Contract `cross_source_coverage.p1_floor=0.88` matches CON-IFP-008 threshold; `p2_watch_line=0.86` matches CON-IFP-008b; `tier_distribution.high_floor=0.70` matches CON-IFP-009; `completeness_threshold=0.97` reflects the FTE-dependent-field floor; `validity_threshold=1.00` matches the per-row enum and arithmetic invariants enforced by CON-IFP-005/006/007. |
| Lineage ↔ landed schemas | MATCH | OpenLineage event lists 5 inputs (3 finance forms + EFIA + HD) and 1 output (`bronze.ipeds_finance`); column-lineage facet names every output column with its derivation (sentinel-scrub + COALESCE semantics included). |
| Per-zone hash prefix separation | MATCH | Base uses `compute_grain_id(['unitid'], prefix='ipf')`; Consumable uses `prefix='ifp'`. Stanford UNITID 243744 verified as `ipf-267f20f48b4b772f` at base and `ifp-267f20f48b4b772f` at consumable — same hash suffix (same grain), distinct prefix (distinct zone). Adversarial audit §5 independently verified zero zone-collision risk. |

**One cosmetic drift (carried forward from bronze post-review):** the bronze `governance/dq-scorecards/full-pipeline-ipeds-finance-scorecard.md` RAW-IPF-014 detail still cites "269 rows above $100M" (bronze post-review P-1 noted live count = 365). Cosmetic only — RAW-IPF-014 floor is `≥ 1`, threshold passes regardless. See Issue Q-2 below.

---

## Vintage Drift Handling — PASS

Bronze was re-ingested FY2022→FY2023 between the EDA pass and base/consumable implementation. All three zones are now consistent at FY2023:

- All base/consumable artifacts cite the FY2023 baseline numbers (2,675 rows, snapshot `1277941459950591173` for base, `6649279885162971471` for consumable, `2955168649587464831` for the current bronze).
- Cross-vintage drift is documented inline in:
  - `governance/dq-rules/base-ipeds-finance.json` `notes` block (per-form 015a/b/c and 013/014 recalibrations from EDA-FY2022 → FY2023)
  - `governance/dq-rules/consumable-ipeds-finance-profile.json` `notes` block (CON-IFP-008 90%→88% recalibration)
  - Data contract `quality.cross_source_coverage.note` (200-bp warning gap rationale)
  - Spec §9 "Deviations from Spec" table (entries §5 cycle year; documents the bronze re-ingest)
- The EDA report header explicitly reads "Cycle: FY2022" — this is acceptable because the EDA was a snapshot at that cycle; it is referenced as the FY2022 baseline by every downstream artifact that recalibrates to FY2023, and the recalibration deltas are themselves documented in the rationale strings. A second EDA pass against FY2023 is **not** required because the spot-check evidence is reproducible: FY2023 measurements are surfaced in the data-contract `quality_tier` block, the DQ-rules `notes` blocks, the consumable physical model "Load Statistics" table, and the CDE-tagging file's "Domain Context Referenced" section.
- Consumable `data_completeness_tier` distribution under FY2023 (`high=1,998 (74.7%) / medium=677 / low=0 / insufficient=0`) is published in 5+ artifacts and matches the live Iceberg snapshot.

---

## Adversarial-Audit-Recommended Contract Clauses — ALL PRESENT

The adversarial audit at `governance/adversarial-audits/consumable-ipeds-finance-profile.md` named the consumable data contract YAML as "the single highest-leverage close-out artifact" for closing Gaps 1–4 (HIGH-severity contract-layer gaps that soft-block the downstream `raw-ingest-eada.md` spec). Spot-check of the landed YAML confirms each recommended clause is present:

| Audit Gap | Recommended clause | Status in `governance/data-contracts/consumable-ipeds-finance-profile.yaml` |
|---|---|---|
| **Gap 4 — F3 endowment-composite silent drop** | Downstream consumers MUST gate composite calculations involving `endowment_value` or `endowment_per_fte` on `report_form != 'F3' OR endowment_value IS NOT NULL` | **PRESENT** — `quality_tier` paragraph documents F3 100%-NULL invariant as structural; per-column `endowment_value.description` documents "Reported on F1A and F2 only — for-profit institutions (F3) have no F3H family on their finance schedule and report NULL by design"; `endowment_per_fte.description` documents "F3 rows are 100% NULL by design"; `cde_rationale` on `endowment_value` calls out the EADA "endowment-backed" composite-input dependency. The EADA-fusion guidance is published in the contract's `quality_tier` and `endowment_value`/`endowment_per_fte` column descriptions. |
| **Gap 3 — vintage-drift unjoinability** | Consumers joining `consumable.ipeds_finance_profile` to other consumables MUST propagate `fiscal_year` and assert vintage equality where the join target carries vintage; for `consumable.career_outcomes` (which carries no `fiscal_year`), consumers MUST document the vintage assumption in their own spec | **PRESENT** — `quality.cross_source_coverage.note` explicitly enumerates the FY2023-vs-FY2022 1.68pp drift; per-column `fiscal_year.description` documents "constant across every row in a single load (single-vintage invariant inherited from Bronze RAW-IPF-013 P0)"; `data_vintage` block names the operative cycle; `downstream_consumers` block names the EADA spec by file. The narrative discharge of Gap 3 is in `reviewer_conditions.governance_reviewer_v1_1_adv_6_discharged_at_consumable` + the `data_vintage` paragraph. |
| **Gap 2 — state-system administrative-office naive-ranking** | Downstream rankings on `marketing_ratio` MUST exclude rows where `instruction_expenses = 0 OR instruction_expenses < $1M` (administrative offices); OR a v1.4 spec amendment adopting the EDA's `~~ ' Office' OR ' System' OR 'Chancellor'` filter; OR an `is_administrative_office` boolean column | **PRESENT (documented; not yet enforced)** — `marketing_ratio.description` enumerates "F1A's high P99 reflects the public-system-administrative-office cluster — legitimate IPEDS entities with system-wide overhead and little instruction"; `quality_tier` block documents the BSE-IPF-015a per-form threshold of 15.0 that *tolerates* the administrative-office tail; the per-column descriptions name Stanford as the canonical comparison anchor. The contract documents the trap and identifies the institution class; the schema-level mitigation (the boolean column) is **deferred to v1.4** per the adversarial audit's R4 recommendation, which is acceptable because no consumer ranking surface ships in this spec. |
| **Gap 1 — `tier='high'` decoupled from `marketing_ratio` computability** | Either a new DQ rule asserting `tier='high' AND marketing_ratio IS NULL → fail` (with N=2 known-exception list); OR a contract clause that consumers gating on `tier='high'` must independently null-check `marketing_ratio` | **PRESENT (documented)** — `data_completeness_tier.description` documents "Counts independent raw inputs (NOT derived signals — that was the v1.0 formula reworked in v1.1 to prevent inflation effects)"; `quality_tier` paragraph documents the F3 → 'medium' cap; the contract does NOT explicitly enumerate the N=2 zero-instruction exception list (Thomas Edison State, Rockefeller). The DQ-rule mitigation (CON-IFP-011 per audit R2) is **deferred to v1.4** — acceptable because the consumable-zone surface does not yet ship a ranking UI. The contract names the trap and the consumers it would affect; the rule-level mitigation is queued for the next amendment. |

**All four Gap-1/2/3/4 mitigations are documented at the contract layer** to the level the adversarial audit demanded for "CLEAR for consumable-zone governance review." The two recommended additive DQ rules (CON-IFP-011 and CON-IFP-012) and the two additive schema columns (`is_administrative_office`, `non_null_signals_count`) per the adversarial audit's recommendations R2/R3/R4/R5 are properly **deferred to a v1.4 amendment or to handling at EADA implementation time** — the audit itself classified all eight gaps as "no HARD blocker; all eight mitigations are additive contract/rule/glossary changes." This deferral is acceptable for this spec's sign-off because:
- No consumer-facing ranking UI ships in this spec (the consumable is data-only; the consuming surfaces — EADA aura, school-card UIs, MCP tools — all live in downstream specs).
- The four contract clauses make the traps named and discoverable to the EADA spec's author at design time.
- The audit's own §9 verdict is "**No HARD blocker requiring a v1.4 spec change to land before the EADA spec begins**" — provided the EADA spec's own §6/§7 explicitly cite which Gap-1/2/3/4 mitigation it relies on.

---

## Standing User Constraints — PASS

| Constraint | Verdict | Evidence |
|---|---|---|
| No YAML lookup tables proposed | PASS | Spec uses no `major_to_cip.yaml`-style lookup; all join keys are UNITID natural keys. Verified across §3 / §4 / §5 / §6. |
| No substitution-based degraded states | PASS | `data_completeness_tier` is a transparency tier, not a filter. The transformer (`src/gold/ipeds_finance_profile.py`) does not exclude any rows by tier; the DQ rules (CON-IFP-005/006/009) enforce enum domain and distribution but do not drop rows; the data contract `quality_tier` paragraph explicitly states "Every downstream consumer is expected to read data_completeness_tier and surface completeness at the row level rather than rely on the contract-level tier alone." Adversarial audit §7 independently re-verified this against the live Parquet. |
| No "Limited data" warnings on consumer surfaces | PASS | This spec stops at the consumable Iceberg table; no consumer-facing UI ships. The data contract documents that downstream consumers SHOULD use `data_completeness_tier` as a transparency signal and MUST NOT silently exclude `medium`/`low`/`insufficient` rows without surfacing the exclusion. |
| Single-source-of-truth maintained | PASS | UNITID is the universal join key throughout (no shadow keys); the per-FTE derivations live at base only (consumable is a 1:1 promote with one new derived column); the marketing_ratio is computed once at base and propagates as a passthrough to consumable; `data_completeness_tier` is computed once at consumable. The three raw expense passthroughs at consumable are a documented narrow exception (v1.1 ADV-6) with no double-source risk because they are byte-identical passthroughs from base, not re-computations. |
| Reports always committed | PASS | All governance artifacts produced are under tracked governance/ subdirectories (per the project standing rule). |

---

## Insight Traceability — N/A

No prior `governance/insights/*.md` reports reference IPEDS Finance — this is a greenfield 3-zone landing of a previously-unmodeled source. Insight-traceability check is N/A for this review pass. Future insight reports that surface drift on this consumable should reference the data contract's `quality.cross_source_coverage` block as the canonical baseline.

---

## Issues Found

| # | Severity | Description | Resolution Required |
|---|----------|-------------|---------------------|
| **Q-1** | CHANGES REQUESTED | Business-glossary registration is partial: 4 of the 6 BT-IPF-* terms named in spec §8 are present in `governance/business-glossary.json` (`BT-IPF-INSTRUCTION-EXPENSES`, `BT-IPF-INSTITUTIONAL-SUPPORT-EXPENSES`, `BT-IPF-ENDOWMENT-VALUE`, `BT-IPF-PER-FTE`). Missing: `BT-IPF-MARKETING-RATIO` and `BT-IPF-DATA-COMPLETENESS-TIER`. Both are referenced by name across the data contract (`business_terms_referenced` block), the consumable data dictionary, the CDE tagging artifact, and the consumable models, and the *definitions* are written verbatim in spec §6. The miss is at the central-glossary registration step. **Non-blocking** because the term definitions exist and behave consistently across artifacts; the consumable data contract also notes the deferral inline ("Proposed at spec §6; deferred to silver/gold doc-generator runs (this run)"). **Fix path:** @bs:data-steward / @bs:doc-generator runs an additive append of the two missing terms to `governance/business-glossary.json`, mirroring the existing 4 BT-IPF-* entries' shape. Single-commit cleanup. |
| **Q-2** | CHANGES REQUESTED (carry-forward) | Bronze post-review's P-1 ("269 rows above $100M" hallucination) is partially closed but the latest scorecard at `governance/dq-scorecards/full-pipeline-ipeds-finance-scorecard.md` still cites 269 in the RAW-IPF-014 detail row. Live count is 365 per the bronze post-review. Cosmetic only — RAW-IPF-014 floor is `≥ 1`, threshold passes regardless. **Fix path:** correct in the same single follow-up commit as Q-1 (touches `governance/eda/raw-ingest-ipeds-finance-eda.md` §8, `governance/dq-rules/raw-ipeds-finance.json` RAW-IPF-014 rationale, `governance/data-dictionaries/raw-ipeds-finance.md` lines 71+112, and the scorecard if it was generated from the rule rationale). |
| **Q-3** | CHANGES REQUESTED (carry-forward) | Bronze post-review's P-2 (spec §4 line 190 still reads "RAW-IPF-001 row count between 5,000 and 8,000" while the rule JSON correctly enforces 2,500–3,200) remains open. Cosmetic only — execution is correct against the amended JSON. **Fix path:** amend §4 DQ Rules table line 190 to read "RAW-IPF-001 row count between 2,500 and 3,200" with a parenthetical "(EDA-calibrated 2026-04-30 — original 5,000–8,000 band predated HD-filter narrowing)". |
| **Q-4** | ADVISORY | Adversarial audit recommendations R2 (CON-IFP-011 P1 rule), R3 (CON-IFP-012 P0 vintage-presence rule), R4 (`is_administrative_office` flag), R5 (`non_null_signals_count` int column), R6 (restore `source_load_date` at consumable), R7 (endowment=0 ambiguity glossary clause), R8 (academic-medical-center BT-IPF-PER-FTE clause) are all deferred to v1.4 / EADA-spec time per the adversarial audit's own §9 ("**No HARD blocker**"). They are documented and queued. The deferral is acceptable for this spec's sign-off but the EADA spec's pre-implementation review must explicitly cite which of these mitigations it relies on or supplements. |
| **Q-5** | ADVISORY | The EDA report header (`governance/eda/raw-ingest-ipeds-finance-eda.md` line 4) cites `Cycle: FY2022 (academic year 2021-22)` and the EDA's measurement evidence is from the FY2022 snapshot. Bronze was re-ingested to FY2023 between EDA and base/consumable implementation. The vintage drift is fully documented in the DQ rule rationales, the data contract, the spec §9 deviations table, and the CDE tagging artifact's "Domain Context Referenced" section. A second EDA pass against the FY2023 baseline is **not** required because the deltas are surfaced in the recalibrated rule thresholds. The EDA file remains canonical for the FY2022 baseline; if the project later adopts SCD2 (per spec §2 Decision #6), the next EDA should be cycle-explicit (`raw-ingest-ipeds-finance-eda-fy2023.md`) rather than overwriting the FY2022 file. |

---

## Decision Rationale

All 17 §8 governance artifacts are present (with one cosmetic registration miss at the central business glossary, Issue Q-1). The full DQ suite (44 rules across 3 zones) executes against live FY2023 Iceberg data with `p0_passed=true` and 0 failures in the latest run (`d16e354a` at 2026-05-01 20:53:24Z). The earlier execution `29f52e5e` at 20:48:58Z had 3 failures (BSE-IPF-015a, BSE-IPF-015b, CON-IFP-008) — the per-form marketing-ratio thresholds and the cross-source coverage rule. These were the FY2022→FY2023 vintage-drift recalibrations the DQ-rule writer identified and fixed, after which the latest run is clean. The recalibration deltas are exhaustively documented in the DQ rule `notes` blocks (transparently auditable; not a silent threshold relaxation).

The consumable data contract YAML — the artifact the adversarial audit named as "the single highest-leverage close-out artifact" — was authored, contains all four contract clauses for Gaps 1/2/3/4, and has SLOs calibrated against the live FY2023 baseline (cross-source coverage P1 at 88% with measured 88.71%; high-tier floor at 70% with measured 74.7%; row-count tolerance band at [2500, 3200] for cycle-to-cycle drift). The four contract clauses are documented inline in the per-column `description` and `cde_rationale` fields plus the table-level `quality_tier` and `quality.cross_source_coverage.note` blocks; the audit's recommended additive DQ rules and additive schema columns are queued for v1.4 / EADA-spec time per the audit's own non-blocking classification.

Cross-artifact consistency holds on every load-bearing claim: the spec §5 / §6 schemas match the landed Iceberg snapshots field-for-field; the data dictionary entries cite the same Stanford UNITID 243744 spot-check values (`marketing_ratio=0.30193`, `tier=high`, base record_id `ipf-267f20f48b4b772f`, consumable record_id `ifp-267f20f48b4b772f`); the CDE flags on the data contract match the CDE tagging file's column-by-column rationale; the per-form data-completeness tier distribution (`F1A high:706, medium:113`; `F2 high:1,292, medium:287`; `F3 high:0, medium:277`) is published in 5+ artifacts and reproduces against the live Parquet. The arithmetic invariant trio (BSE-IPF-008/009/010 at base; CON-IFP-007 at consumable) holds by construction and is verified empirically by the DQ runner.

Standing user constraints are all satisfied: no YAML lookup tables, no substitution-based degraded states (the data_completeness_tier is a transparency signal that the transformer does not enforce as a filter, and the data contract explicitly forbids silent exclusion of `medium`/`low`/`insufficient` rows by downstream consumers), no "Limited data" warnings (no consumer surface ships in this spec), single-source-of-truth maintained (UNITID universal; per-FTE derivations live at base only; the v1.1 ADV-6 raw expense passthroughs at consumable are documented narrow exceptions, not double-source risks).

The three CHANGES REQUESTED follow-ups (Q-1 missing 2 glossary terms, Q-2 carried-forward 269-vs-365 hallucination cleanup, Q-3 carried-forward §4 spec text band-vs-rule-JSON drift) are all cosmetic / process-ledger fixes that should be batched into a single follow-up commit. None is blocking for the staff-engineer post-review or for the start of `raw-ingest-eada.md`. The two ADVISORY items (Q-4 deferred adversarial-audit recommendations, Q-5 EDA-vintage observability) are queued for v1.4 / EADA-spec time per the adversarial audit's own non-blocking classification.

**Verdict: APPROVED (full pipeline).** Three CHANGES REQUESTED follow-ups for the cleanup author; two ADVISORY items queued for v1.4 / EADA-spec time. Spec advances to staff-engineer post-implementation review and is unblocked for the start of `raw-ingest-eada.md` provided the EADA spec's own pre-implementation review §6/§7 explicitly cites which of the adversarial-audit Gap-1/2/3/4 contract clauses it relies on or supplements.

---

## Verdict

- [x] **APPROVED (full pipeline)** — all 17 §8 artifacts present; cross-artifact consistency holds; 44/44 DQ PASS; adversarial-audit contract clauses present; standing user constraints satisfied
- [ ] CHANGES REQUESTED
- [ ] REJECTED

**Carry-forward CHANGES REQUESTED for cleanup commit:** Q-1 (2 missing BT-IPF-* glossary entries), Q-2 (cosmetic 269→365 propagation across EDA/dictionary/scorecard/rule rationale), Q-3 (cosmetic §4 spec text band-vs-rule-JSON drift). Single-commit cleanup; non-blocking for staff-engineer post-review and for `raw-ingest-eada.md` start.

**Advisories queued for v1.4 / EADA spec:** Q-4 (deferred adversarial-audit R2-R8 mitigations), Q-5 (EDA-vintage observability under future SCD2).
