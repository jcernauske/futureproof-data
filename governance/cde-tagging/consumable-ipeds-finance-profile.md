# CDE/PII Tagging: consumable.ipeds_finance_profile

**Table:** `consumable.ipeds_finance_profile` (Iceberg: `consumable.ipeds_finance_profile`)
**Spec:** `docs/specs/ipeds-finance-v1.4.md` (v1.3 — re-tag delta from v1.3 baseline)
**Parent zones (this pipeline):** `bronze.ipeds_finance` (raw) → `base.ipeds_finance` (silver) → `consumable.ipeds_finance_profile` (this file)
**Date:** 2026-04-30 (v1.3 baseline) · 2026-05-02 (v1.4 re-tag — `endowment_value_provenance` CDE add, `source_load_date` NOT-CDE, semantic correction propagation)
**Agent:** @cde-tagger
**Zone:** Gold (Consumable — base→gold shaping promote, no cross-source joins)
**Contract:** `governance/data-contracts/consumable-ipeds-finance-profile.yaml` *(v1.4 amendment to be merged by @doc-generator — embed the v1.4 column fragments below)*
**Upstream tagging:**
- `governance/cde-tagging/raw-ipeds-finance.md` (Bronze; v1.4 adds `endowment_value_flag` to the CDE list — 6 CDE: `unitid`, `instruction_expenses`, `institutional_support_expenses`, `endowment_value`, `total_fte_enrollment`, `endowment_value_flag`; 0 PII)
- `governance/cde-tagging/base-ipeds-finance.md` (Base; new in v1.4 — 6 CDE matching bronze passthrough plus the renamed-at-consumable provenance flag still named `endowment_value_flag` at base; 0 PII)
**Upstream PII scan:** `governance/pii-scans/raw-ipeds-finance-pii-scan.md` (verdict: **NO PII** — all 13 bronze fields v1.4 Level 1 Public; institution-level federal survey data; the v1.4 `endowment_value_flag` addition is a 5-code enum literal, not a person identifier)

---

## Domain Context Referenced

- `governance/domain-context.md` §IPEDS Finance (2026-04-30 entry, refinalized against actually-landed FY2022 bronze; superseded again to FY2023 in current load) — establishes IPEDS Finance as the ninth FutureProof source: F1A (public/GASB) ∪ F2 (private NFP/FASB) ∪ F3 (private for-profit), joined to **EFIA** (12-Month Instructional Activity, NOT EFFY headcount) on UNITID for `total_fte_enrollment = COALESCE(FTEUG,0)+COALESCE(FTEGD,0)+COALESCE(FTEDPP,0)`, filtered to 4-year-bachelor's-or-above via HD `ICLEVEL=1 AND HLOFFER>=5`; locked column codes `F1C011/F1C071/F1H02`, `F2E011/F2E061/F2H02`, `F3E011/F3E03C1`; F3 endowment 100% structurally NULL (no F3H family); endowment imputation prevalence 25-31% on F1A/F2 (NCES bureau-imputed, accept-as-real per §2 Decision #8); 90.39% UNITID overlap with `consumable.career_outcomes` on FY2022 / 88.71% on FY2023 (CON-IFP-008 P1 recalibrated to 88%). **PII section explicitly reaffirms: none (institution-level public data).** Domain-context further pins this consumable as the upstream feeder of `consumable.institution_aura` (forward-looking "brand gravity" composite) — `marketing_ratio` and `endowment_per_fte` planks per spec `docs/specs/full-pipeline-eada.md` §6 (Decision 11).
- `governance/eda/raw-ingest-ipeds-finance-eda.md` — 2,683 FY2022 rows (current load 2,675 FY2023); form mix F1A 30.6% / F2 59.0% / F3 10.4% (FY2022); `data_completeness_tier` distribution `high=1,998 / medium=677 / low=0 / insufficient=0` (74.7% high — comfortably above CON-IFP-009 70% floor); per-form tier `F1A: high:706, medium:113`, `F2: high:1,292, medium:287`, `F3: high:0, medium:277` (all 277 F3 rows at `medium`, none at `high` — confirms v1.2 reviewer rework prevents F3 misleading-`high` classification driven by structural endowment NULL); Stanford UNITID 243744 spot-check `tier=high`, `marketing_ratio=0.30193`, all 4 raw inputs present.
- `governance/pii-scans/raw-ipeds-finance-pii-scan.md` — **NO PII** across all 12 bronze columns; zero-PII claim cascades through base and consumable. Grain unchanged at one row per UNITID (2,675 rows). k-anonymity is not the relevant frame here (institution grain, not person grain) — every row identifies a public legal entity (a postsecondary institution) under a federal mandatory-disclosure regime (Title IV).
- **Applicable regulations:** NONE — IPEDS Finance is U.S. Department of Education / NCES public-domain federal survey data published under §132 HEA (institutional reporting requirement). No FERPA exposure (no student records — NCES applies all student-privacy aggregation upstream). No GLBA exposure (institution-level GAAP balance-sheet aggregates, not bank/account/transactional data). No HIPAA, GDPR, CCPA, PCI DSS, or SOX exposure. The only triggered framework is the underlying §132 HEA / IPEDS public-records regime itself (informational — these figures are mandated to be public).
- **PII expectations:** NONE — all 15 consumable columns are institution-level aggregates, deterministic ratios of institution-level aggregates, a synthesized completeness tier derived from non-null counts, an institution name (organization, not person), pipeline metadata, or Iceberg framework columns. Per the v1.4 IPEDS Finance domain-context entry, "PII reaffirmed as none (institution-level public data)" is the canonical posture across the IPEDS Finance pipeline.
- **Sibling consumable CDE patterns referenced for consistency:**
  - `governance/cde-tagging/gold-regional-price-parities.md` — closest single-source single-table consumable analogue. Sets the precedent that pre-computed display-ready derivations consumed directly by Gemma / MCP / frontend are CDE at consumable when no client-side math intervenes. Also sets the precedent that grain surrogate (`record_id`) and batch stamp (`promoted_at`) are non-CDE in every consumable.
  - `governance/cde-tagging/raw-eada.md` — the EADA Bronze tagging file explicitly names `marketing_ratio` and `endowment_per_fte` as IPEDS-Finance-sourced consumable CDE candidates that this file is responsible for tagging. See "CDE-to-Gold dependency table" in that file — these flags are the IPEDS-side completion of the cross-spec aura composite.

---

## Table Context: Why CDE Decisions Matter Here

`consumable.ipeds_finance_profile` is the **business-ready, institution-level finance profile** for FutureProof. It is a pure base→consumable shaping promote (no cross-source joins, no derived score; the Gold layer does not compute anything new beyond the synthesized `data_completeness_tier`). The four per-FTE values, the marketing ratio, and the three raw dollar passthroughs are exposed verbatim from base, then re-keyed under a fresh `ifp-` `record_id` namespace.

CDE density here is shaped by three downstream consumption realities:

1. **The four per-FTE / ratio derivations are the analytical payload.** `marketing_ratio`, `instruction_per_fte`, `institutional_support_per_fte`, and `endowment_per_fte` are the four columns that any school-comparison surface, any "brand-vs-teaching-spend" lens, and any per-student efficiency comparison reaches for. Without these four columns this table has no business-consumer value beyond what the College Scorecard institution table already provides. Spec §6 Data Contract names all four as CDE candidates; this tagging pass affirms all four.
2. **The fused EADA aura table reads two of these columns directly.** Per `docs/specs/full-pipeline-eada.md` §6 Decision 11 and the §6 amended consumable CDE candidate list, `consumable.institution_aura` consumes `marketing_ratio` and `endowment_per_fte` as direct aura composite inputs (alongside EADA-sourced `athletic_spend_per_fte`). The aura table is itself a consumer-facing school-card / school-picker surface. Tagging these two columns CDE is mandatory both because of the per-row student-facing lens AND because of the cross-spec composite they feed. The same value flow reaches the consumer twice — once standalone, once as an aura input.
3. **The three raw dollar passthroughs (`instruction_expenses`, `institutional_support_expenses`, `endowment_value`) are exposed at consumable for downstream EADA composite ratios.** Per spec §6 Transformation 1 ("The three raw dollar passthroughs are exposed at consumable so downstream specs (notably `raw-ingest-eada.md`) can compute composite ratios without back-joining to base"), these three columns exist in the consumable specifically as upstream feeders for the EADA fusion. Their CDE status is therefore **derivative of the same cross-spec aura logic** that drives the per-FTE flags — they are the raw building blocks the per-FTE columns and `marketing_ratio` are constructed from. Tagging them CDE here forces governance attention on a value-flow that crosses spec boundaries.
4. **`data_completeness_tier` gates downstream consumer behavior.** Per spec §6 Transformation 2 and CON-IFP-005/006 P0 DQ rules, this synthesized 4-valued enum is the row-level signal a consumer (frontend, MCP tool, EADA fusion) can use to decide whether to show a school card, hedge a comparison, or skip the row entirely. v1.2 added it to the §6 Data Contract CDE candidate list specifically because it is the `should I trust this row?` gate for downstream UI.

The base→consumable relationship is pure shaping:

- **12 columns carry forward from base unchanged** (`unitid`, `institution_name`, `report_form`, `fiscal_year`, `total_fte_enrollment`, `instruction_expenses`, `institutional_support_expenses`, `endowment_value`, `institutional_support_per_fte`, `instruction_per_fte`, `endowment_per_fte`, `marketing_ratio`)
- **1 column is newly synthesized in consumable** (`data_completeness_tier`)
- **2 columns are consumable operational/grain** (`record_id` with `ifp-` prefix, `promoted_at` batch timestamp)
- **v1.4 ADDS 2 new consumable columns:**
  - `endowment_value_provenance` — renamed passthrough from `base.ipeds_finance.endowment_value_flag` per spec §2 Decision A. The rename happens at consumable; bronze + base preserve the IPEDS-vocabulary `endowment_value_flag` name (faithful-to-source convention).
  - `source_load_date` — restored passthrough from `base.ipeds_finance.source_load_date`. Documents when the bronze source was loaded (NCES revises previously-published vintages preliminary → revised → final); distinct from `fiscal_year` and `promoted_at`.

Per Brightsmith governance, CDE flags do **not** propagate across zones. The bronze CDE set (`unitid`, `instruction_expenses`, `institutional_support_expenses`, `endowment_value`, `total_fte_enrollment`, plus `endowment_value_flag` added in v1.4) is **not** mechanically reproduced here — each column is re-evaluated against its consumable role below. In this case, `unitid` is re-affirmed as CDE (cross-source join anchor), `total_fte_enrollment` is re-affirmed as CDE (denominator for downstream EADA `athletic_spend_per_fte` per `docs/specs/full-pipeline-eada.md` §5 Decision 3 "cross-source LEFT JOIN" — this consumable IS the join target), and the three raw dollar passthroughs are re-affirmed as CDE (raw-input feeders for the EADA composite ratios per spec §6 Transformation 1 cross-spec note). The four per-FTE / ratio derivations are newly evaluated at consumable as the table's analytical payload and all four are flagged. `data_completeness_tier` is newly evaluated as the row-level trust gate and is flagged. **v1.4 adds `endowment_value_provenance` as a CDE** (interpretation-changing for any analysis that uses `endowment_value` or `endowment_per_fte` — see column #11 below); **v1.4 also adds `source_load_date` as NOT-CDE** (vintage-observability metadata, not a substantive measure — see column #16 below).

---

## Columns Flagged as CDE

| # | Column | Type | is_cde | Origin | Rationale |
|---|--------|------|--------|--------|-----------|
| 1 | `unitid` | long | **true** | Base passthrough (re-evaluated) | **Primary key** of the consumable table (CON-IFP-002 non-null 100% / CON-IFP-003 uniqueness P0). Sole join anchor for the cross-spec EADA fusion (`consumable.institution_aura` FULL OUTER JOIN per `docs/specs/full-pipeline-eada.md` §6) and for every consumer cross-walk to `consumable.career_outcomes` (CON-IFP-008 P1 ≥88% overlap), `consumable.program_career_paths`, and `bronze.college_scorecard_institution`. UNITID coercion failures here orphan the entire row from the aura composite and cap the addressable surface of every school card. IPEDS external standard (federal NCES taxonomy). Re-affirmed from Bronze CDE set. |
| 2 | `total_fte_enrollment` | double | **true** | Base passthrough (re-evaluated) | **FTE backbone for all four per-FTE derivations on this row AND for the EADA cross-source FTE pull-through** per `docs/specs/full-pipeline-eada.md` §5 Decision 3 (Option A: cross-source LEFT JOIN to `base.ipeds_finance.total_fte_enrollment` — but the FUSED consumable per §6 reads from this table at consumable grain). Wrong values silently mis-state every per-FTE figure on every school card AND every `athletic_spend_per_fte` value on every aura composite. The EFIA-not-EFFY-not-EFTOTLT FTE source pin (per domain-context.md and spec §3) is the highest-risk field-selection in this pipeline; CDE tagging forces governance attention on it at the consumable surface. Re-affirmed from Bronze CDE set. |
| 3 | `instruction_expenses` | double | **true** | Base passthrough (re-evaluated; **explicitly re-exposed at consumable per spec §6 Transformation 1**) | Raw dollar passthrough exposed at consumable per spec §6 Transformation 1 specifically so that downstream EADA fusion (`docs/specs/full-pipeline-eada.md`) can compute composite ratios without back-joining to base. Numerator of `instruction_per_fte` (downstream column on this same row); denominator of `marketing_ratio` (downstream column on this same row). Re-affirmed from Bronze CDE set with **expanded rationale at consumable**: not just an upstream input but an exposed-at-consumable feeder for cross-spec composites. Sources: F1C011 (F1A) / F2E011 (F2) / F3E011 (F3). |
| 4 | `institutional_support_expenses` | double | **true** | Base passthrough (re-evaluated; **explicitly re-exposed at consumable per spec §6 Transformation 1**) | Raw dollar passthrough exposed at consumable per spec §6 Transformation 1 for downstream EADA composite-ratio computation. Numerator of `institutional_support_per_fte` (downstream column on this row); numerator of `marketing_ratio` (downstream column on this row). Re-affirmed from Bronze CDE set with expanded consumable rationale. Sources: F1C071 (F1A) / F2E061 (F2) / F3E03C1 (F3 — pre-2014-15 belief that F3 omits institutional support is REFUTED per domain-context.md; 100% non-null on FY2022/FY2023). |
| 5 | `endowment_value` | double | **true** | Base passthrough (re-evaluated; **explicitly re-exposed at consumable per spec §6 Transformation 1**) | Raw dollar passthrough exposed at consumable per spec §6 Transformation 1 for downstream EADA composite-ratio computation. Sole numerator of `endowment_per_fte` (downstream column on this row, also a direct aura composite input per `docs/specs/full-pipeline-eada.md` §6 Decision 11). 100% structurally NULL on F3 rows (no F3H family — proprietary institutions do not maintain endowments by design); F1A/F2 endowment imputation prevalence ≈ 25-31% (NCES bureau-imputed via prior-year × market-return per domain-context.md, accept-as-real per §2 Decision #8 — `endowment_value_provenance` flag column proposed for v1.4). Re-affirmed from Bronze CDE set with expanded consumable rationale. Sources: F1H02 (F1A) / F2H02 (F2) / N/A (F3). |
| 6 | `institutional_support_per_fte` | double | **true** | Base passthrough (computed at base from `institutional_support_expenses / total_fte_enrollment`) | **Directly student-facing per-student spend figure.** Drives the "how much does this school spend on administration / overhead per student" lens on school comparison surfaces. NULL when either `institutional_support_expenses` or `total_fte_enrollment ≤ 0` is missing (no imputation per spec §2 Decision #8). Spec §6 Data Contract names as CDE candidate. Reciprocally constrained against `instruction_per_fte` and `marketing_ratio` by CON-IFP-007 P0 arithmetic invariant (`institutional_support_per_fte / instruction_per_fte ≈ marketing_ratio` within 0.001 where all three non-null). |
| 7 | `instruction_per_fte` | double | **true** | Base passthrough (computed at base from `instruction_expenses / total_fte_enrollment`) | **Directly student-facing per-student spend figure.** Drives the "how much does this school spend on me / on teaching per student" headline number on school comparison surfaces — the most analytically interpretable of the four per-FTE columns and the one most likely to drive student decision-making in a fight-card or pentagon-explainer surface. NULL when either operand is missing. Spec §6 Data Contract names as CDE candidate. CON-IFP-007 arithmetic invariant denominator (must equal `institutional_support_per_fte / marketing_ratio` within 0.001 where all three non-null). |
| 8 | `endowment_per_fte` | double | **true** | Base passthrough (computed at base from `endowment_value / total_fte_enrollment`) | **Direct aura composite input per `docs/specs/full-pipeline-eada.md` §6 Decision 11** — one of the three forward-looking aura signals (alongside `marketing_ratio` and EADA-sourced `athletic_spend_per_fte`). Domain-context.md describes endowment_per_fte as "absolute floor of institutional resource gravity" — the "wealth and endowment" plank of the brand-gravity composite. Also displayed standalone as a per-student endowment figure on school comparison surfaces. NULL on 100% of F3 rows by design (no F3H family) AND on any F1A/F2 row where FTE is missing. Spec §6 Data Contract names as CDE candidate. **The per-FTE column with the most cross-spec leverage** — wrong here means wrong twice (standalone display + aura composite). |
| 9 | `marketing_ratio` | double | **true** | Base passthrough (computed at base as `institutional_support_expenses / instruction_expenses`) | **Direct aura composite input per `docs/specs/full-pipeline-eada.md` §6 Decision 11** — the "brand-spend as a share of operating budget" plank. Domain-context.md describes marketing_ratio as "brand-vs-teaching-spend" lens — the analytically richest single signal in this table because it normalizes spend without requiring an FTE denominator (so it survives FTE-NULL rows that the per-FTE columns do not). EDA-measured P99 ≈ 5.0 table-wide; per-form thresholds in BSE-IPF-015a/b/c. Spec §6 Data Contract names as CDE candidate. **The most-load-bearing column on this table** — primary input to the EADA aura composite, primary signal on the standalone marketing-vs-instruction narrative on school comparison UIs, and the only ratio that does not depend on the (sometimes-missing) FTE denominator. |
| 10 | `data_completeness_tier` | string | **true** | **New in consumable** — synthesized from non-null count of 4 independent raw inputs (`instruction_expenses`, `institutional_support_expenses`, `endowment_value`, `total_fte_enrollment > 0`) | **Row-level trust gate for downstream consumers.** Four-valued enum (`high` = 4/4, `medium` = 2-3/4, `low` = 1/4, `insufficient` = 0/4). v1.2 added to spec §6 Data Contract CDE candidate list (renamed from `confidence_tier` in v1.1 to disambiguate from CIP→SOC crosswalk-confidence tiers). Per spec §6 Transformation 2, this column counts **independent raw inputs only** (NOT derived signals — the v1.0 formula counting derived signals was reworked because it inflated F3 rows to misleading-`high` despite structural endowment NULL). EDA-measured distribution `high=74.7% / medium=25.3% / low=0% / insufficient=0%` (CON-IFP-009 P1 ≥70% high). The `should I show this school card?` and `should the EADA fusion accept this row as a clean composite input?` gate. Per-form skew is significant: 100% of F3 rows land at `medium` (none at `high`) by construction — F3 endowment is structurally NULL. CON-IFP-005 P0 enum membership + CON-IFP-006 P0 classification check (recompute and compare). **New consumable-origin CDE flag.** |
| 11 | `endowment_value_provenance` | string | **true** | **New in v1.4** — renamed passthrough from `base.ipeds_finance.endowment_value_flag` per spec §2 Decision A (consumer-clarity rename; bronze + base preserve the IPEDS-vocabulary `flag` name). Sourced from `XF1H02` (F1A) / `XF2H02` (F2); structurally NULL on F3 (no `F3H` family). | **Interpretation-changing CDE for `endowment_value` and `endowment_per_fte`.** Five-code enum on F1A/F2: `R` = Reported by institution; `A` = **Not applicable** (institution has no endowment fund — community colleges, tribal colleges, theological seminaries, system offices — exact `A`↔NULL coupling on `endowment_value` enforced by BSE-IPF-020 P0); `N` = **Imputed using Nearest Neighbor procedure**; `P` = Imputed using prior year's data; `Z` = Imputed using a zero value. **Downstream interpretation guidance (load-bearing, mirrors BT-IPF-ENDOWMENT-PROVENANCE glossary semantics):** consumers running longitudinal endowment analyses must filter to `endowment_value_provenance = 'R'` to limit to institution-reported populated values. Filtering to `R` is operationally close to filtering to `endowment_value IS NOT NULL` because of the `A`↔NULL coupling, but the explicit `R` filter is correct: it drops the small `N`/`P`/`Z` imputed-value rows that *do* carry a populated `endowment_value`. Snapshot benchmarks may use all non-NULL endowment_value rows regardless of provenance; longitudinal trend lines must filter to `R`. Without this column, every consumer of `endowment_value` and `endowment_per_fte` is reading a silent mix of institution-reported, NCES-imputed-by-nearest-neighbor, NCES-imputed-from-prior-year, and NCES-zero-imputed values — the `aura_score` `endowment_per_fte` plank in `consumable.institution_aura` (per `docs/specs/full-pipeline-eada.md` §6 Decision 11) is the most cross-spec-load-bearing consumer of this distinction. CON-IFP-013 P0 passthrough fidelity (0 mismatches vs. `base.ipeds_finance.endowment_value_flag`); domain enforced by RAW-IPF-015 (allowed set `{R, A, P, Z, N}` strict subset of dictionary's 13-code shared lookup; any unobserved code is a Significant escalation per spec §3, no silent allowed-set extension). **Semantic correction history (propagated from spec §3 / §2 Decision H):** the v1.3 EDA §7 narrative inverted the meanings of `A` and `N` (described `A` as "model-imputed" and `N` as "not applicable"). v1.4 v1.2 corrected the semantics against the FY2023 dictionary + FY2023 empirical evidence (every `A`-flagged row has `endowment_value IS NULL`). The longitudinal-filter mechanism (`= 'R'`) is unchanged in mechanism (because of the `A`↔NULL coupling, the operational result is the same), but the rationale phrasing is corrected throughout this document. **New consumable-origin CDE flag (v1.4).** |

**Total CDE flags: 11 of 17 columns** (v1.4 — was 10 of 15 in v1.3; +2 columns added: `endowment_value_provenance` flagged CDE, `source_load_date` NOT flagged).

Breakdown:
- **5 carried forward (re-affirmed) from Bronze:** `unitid`, `total_fte_enrollment`, `instruction_expenses`, `institutional_support_expenses`, `endowment_value` (all five with **expanded rationale at consumable** for the cross-spec EADA aura composite)
- **4 base-derived columns newly tagged at consumable** (these were not the bronze CDE set since they did not exist there): `institutional_support_per_fte`, `instruction_per_fte`, `endowment_per_fte`, `marketing_ratio`
- **2 consumable-origin CDE flags:** `data_completeness_tier` (v1.2 origin), `endowment_value_provenance` (v1.4 origin — interpretation-changing for `endowment_value` and `endowment_per_fte`; renamed from base's `endowment_value_flag`)

---

## Columns Flagged as PII

**None.** Per `governance/pii-scans/raw-ipeds-finance-pii-scan.md` and the canonical IPEDS Finance domain-context entry, all 17 consumable columns (v1.4) are non-PII:

- The 5 base passthrough columns (`unitid`, `total_fte_enrollment`, `instruction_expenses`, `institutional_support_expenses`, `endowment_value`) inherit their Bronze non-PII classification (institution-level federal survey aggregates, public-domain license).
- `institution_name` is an organization name (e.g., "Indiana University-Bloomington", "Stanford University"). The **most-likely false-positive surface** for naive NER scanners (eponymous schools include the donor/founder's surname inside the org name — "Carnegie Mellon University", "Johns Hopkins University", "Wesleyan College") was reviewed in the Bronze PII scan and rejected: field name (`institution_name`) and grain (one per UNITID) are dispositive. Confirmed not PII.
- `report_form` is a 3-value discriminator literal (`F1A` / `F2` / `F3`) — survey-instrument tag, not data about a person.
- `fiscal_year` is calendar metadata (current load: 2023, constant across all 2,675 rows).
- The 4 per-FTE / ratio derivations (`institutional_support_per_fte`, `instruction_per_fte`, `endowment_per_fte`, `marketing_ratio`) are scalar functions of institution-level aggregates. **NOT individual earnings or compensation data** — these are the institution's reported expense / endowment totals divided by the institution's reported FTE count, identical for every notional individual at the institution.
- `data_completeness_tier` is a lossy 4-bucket generalization of a non-null count over four institution-level fields, which *increases* k-anonymity rather than decreasing it.
- `endowment_value_provenance` (v1.4) is a 5-code enum literal (`R / A / P / Z / N`) describing how a per-institution `endowment_value` was sourced. NOT data about a person — it is a methodology tag on an institution-level financial aggregate. Inherits the bronze-passthrough non-PII classification.
- `source_load_date` (v1.4) is an ETL-side load timestamp documenting when the bronze source was loaded. Identical (or nearly so) across all rows in a batch — not a per-person event. Operational metadata.
- `record_id` (`ifp-<hash(unitid)>`) is a pseudonym for an institution, not a person — derived from a non-PII input.
- `promoted_at` is a batch-level ETL operational timestamp, identical across all rows in a batch.

The grain is institution-level (one row per UNITID per fiscal_year). This **structurally precludes** student, employee, donor, or transactional PII surfaces under the v1.4-locked column list. The bronze PII scan's "Future-proofing" recommendation flagged that future column additions like `CHFNM`/`CHFNM2` (officer names from IPEDS HD) WOULD be PII surfaces — none of those columns are present in the v1.4 consumable schema, so this consumable inherits the clean-zero PII posture.

No column receives `is_pii: true`. No sensitivity classification above `public` is required. No RLS, no column masking, no encryption-beyond-baseline.

**0 of 17 columns flagged as PII.**

---

## Columns Evaluated — Not Flagged

| # | Column | Type | is_cde | is_pii | Reason Not Critical / Not Sensitive |
|---|--------|------|--------|--------|-------------------------------------|
| 12 | `record_id` | string | false | false | Deterministic consumable grain surrogate built as `compute_grain_id(row, ['unitid'], prefix='ifp')`. Pure function of `unitid`, so it encodes no additional information — flagging would be redundant with the `unitid` CDE. The `ifp-` prefix is intentionally distinct from base's `ipf-` prefix per spec §6 (zone hash namespaces don't collide). Consumed only by the pipeline's dedup / upsert machinery, not by business consumers, MCP tools, or user-facing displays. Not a decision input. CON-IFP-004 P0 guarantees non-null + uniqueness mechanically. Same precedent as `record_id` non-CDE in `gold-regional-price-parities.md`. |
| 13 | `institution_name` | string | false | false | Display label only at consumable. The authoritative join key is `unitid`; institution name is carried for UI convenience, EDA cross-checks, and operator readability. Mismatched names against IPEDS HD would surface during base-zone DQ (BSE-IPF-* completeness rules) but do not gate any consumable formula or any downstream consumer decision. Same precedent as `institution_name` non-CDE in `raw-eada.md` (Bronze EADA tagging). Confirmed organization name (not personal) per the Bronze PII scan's NER false-positive review. |
| 14 | `report_form` | string | false | false | Provenance discriminator literal — only 3 values in the value space (`F1A` / `F2` / `F3`), tagging the source survey form for operator interpretability and per-form DQ (BSE-IPF-015a/b/c per-form marketing_ratio P99 thresholds; per-form `data_completeness_tier` distribution from the EDA). Useful for downstream segmentation analysis but not a decision input to any consumer-facing surface — the consumer cares about the ratios and the completeness tier, not which GAAP framework produced them. The structural F3-medium-not-high invariant is encoded in `data_completeness_tier` directly, not in `report_form`. |
| 15 | `fiscal_year` | int | false | false | Provenance / cycle-vintage metadata. Pinned per ingest run (current load: 2023, constant across all 2,675 rows). Distinct from BEA RPP's `data_year` (which carried per-record vintage and was flagged CDE in `gold-regional-price-parities.md` for reproducibility): IPEDS Finance `fiscal_year` is a load-level pin (cycle is a runtime parameter per domain-context.md "Cycle vintage" — promoting to FY24 is a parameter change, not a code change), not a row-level fact that varies between rows in a snapshot. Operator value for cycle-vintage tracking but not a per-row decision input to any consumer. If a future spec lands multi-cycle SCD2 (currently out of scope), re-evaluate. |
| 16 | `source_load_date` | date | false | false | **New in v1.4** — restored passthrough from `base.ipeds_finance.source_load_date` per spec §6 Data Contract delta. Documents when the bronze source CSV was loaded — distinct from `fiscal_year` (the IPEDS reporting cycle) and from `promoted_at` (the consumable promote timestamp). NCES revises previously-published vintages (preliminary → revised → final); `source_load_date` lets a downstream consumer compare two cached snapshots and tell which is fresher. **NOT CDE — vintage-observability metadata, not a substantive measure.** It does not change the interpretation of any business metric, does not feed any downstream composite, and does not gate any consumer decision (CON-IFP-016 P1 freshness rule cross-checks it against `promoted_at` for staleness detection but freshness is an operational concern, not a CDE concern). Same precedent as `source_load_date` non-CDE in `silver-base-college-scorecard-institution-cdes.md` ("Pipeline metadata — provenance tracking only"). CON-IFP-015 P0 non-null + CON-IFP-016 P1 within-400-days are the operational guards; neither lifts this column to CDE status. Distinct from `endowment_value_provenance` (which IS CDE because it changes interpretation of the endowment values themselves) — `source_load_date` is observability metadata about the load, not provenance metadata about a measurement. |
| 17 | `promoted_at` | timestamp | false | false | Consumable promotion batch stamp. Identical across all 2,675 rows in a batch. Replaces base's `ingested_at` operational pair with a single Gold-zone timestamp. Useful for operational observability and freshness tracking (CON-IFP-010 P0 non-null) but not a decision input to any downstream consumer. Annual refresh cadence (governed by the IPEDS Data Center publication schedule, ~Sep N+2 for FY N) is the freshness contract, not per-row timestamps. Not a personal date. Same precedent as `promoted_at` non-CDE in every consumable. |

**5 columns not flagged in v1.3** — 1 grain surrogate, 1 display label, 2 provenance metadata fields (`report_form`, `fiscal_year`), 1 batch stamp (`promoted_at`); plus **v1.4 adds 1 vintage-observability metadata column** (`source_load_date`) for a total of **6 columns not flagged out of 17 v1.4 consumable columns**. None feed an analytical payload, a downstream composite, or a consumer-facing decision.

---

## Tag List for Data Contract (for @doc-generator to embed)

When `governance/data-contracts/consumable-ipeds-finance-profile.yaml` is generated, embed the following column-level flags. This fragment preserves column order as defined in spec §6 Consumable Schema.

```yaml
# Fragment — to be merged by @doc-generator into consumable-ipeds-finance-profile.yaml
columns:
  - name: record_id
    type: string
    required: true
    is_cde: false
    cde_rationale: ""
    is_pii: false
    pii_rationale: ""
    description: >
      Deterministic consumable grain surrogate. Derived as
      compute_grain_id(row, ['unitid'], prefix='ifp'). 'ifp-' prefix
      intentionally distinct from base's 'ipf-' prefix (zone hash
      namespaces don't collide). 2,675 distinct values, one per UNITID.

  - name: unitid
    type: long
    required: true
    business_term: BT-IPF-UNITID  # final ID assigned by @bs:data-steward
    is_cde: true
    cde_rationale: >
      Primary key of the consumable table (CON-IFP-002 non-null 100% /
      CON-IFP-003 uniqueness P0). Sole join anchor for cross-spec EADA
      fusion (consumable.institution_aura FULL OUTER JOIN per
      docs/specs/full-pipeline-eada.md §6) and for every consumer
      cross-walk to consumable.career_outcomes (CON-IFP-008 P1 ≥88%
      overlap), consumable.program_career_paths, and
      bronze.college_scorecard_institution. UNITID coercion failures
      orphan rows from the aura composite. IPEDS external standard
      (federal NCES taxonomy). Re-affirmed from Bronze CDE set.
    is_pii: false
    pii_rationale: ""
    description: >
      6-digit IPEDS institutional identifier (federal NCES organization
      ID). Primary key. 100% non-null and unique across 2,675 rows.

  - name: institution_name
    type: string
    required: true
    is_cde: false
    cde_rationale: ""
    is_pii: false
    pii_rationale: >
      Organization name, not personal. Most-likely false-positive surface
      for naive NER scanners (eponymous schools include donor/founder
      surname); Bronze PII scan reviewed and rejected. Confirmed not PII.
    description: >
      Institution legal name from IPEDS HD INSTNM (e.g., "Indiana
      University-Bloomington", "Stanford University"). Display label
      only; unitid is the authoritative key.

  - name: report_form
    type: string
    required: true
    is_cde: false
    cde_rationale: ""
    is_pii: false
    pii_rationale: ""
    description: >
      Source survey form discriminator: 'F1A' (public/GASB) / 'F2'
      (private NFP/FASB) / 'F3' (private for-profit). Operator
      interpretability and per-form DQ (BSE-IPF-015a/b/c).

  - name: fiscal_year
    type: int
    required: true
    is_cde: false
    cde_rationale: ""
    is_pii: false
    pii_rationale: ""
    description: >
      Reporting fiscal-year cycle. Pinned per ingest run; constant
      across all rows in a load (current: 2023). Cycle is a runtime
      parameter — promoting to FY24 is a parameter change, not a code
      change. Re-evaluate if multi-cycle SCD2 is added.

  - name: total_fte_enrollment
    type: double
    required: false
    business_term: BT-IPF-PER-FTE  # FTE definition reference; final ID by @bs:data-steward
    is_cde: true
    cde_rationale: >
      FTE backbone for all four per-FTE derivations on this row AND for
      the EADA cross-source FTE pull-through per
      docs/specs/full-pipeline-eada.md §5 Decision 3. Wrong values
      silently mis-state every per-FTE figure on every school card AND
      every athletic_spend_per_fte on every aura composite. The
      EFIA-not-EFFY-not-EFTOTLT FTE source pin (per domain-context.md)
      is the highest-risk field-selection in this pipeline.
      Re-affirmed from Bronze CDE set.
    is_pii: false
    pii_rationale: ""
    description: >
      12-month full-time-equivalent enrollment from EFIA, computed as
      NULL-safe sum of FTEUG + FTEGD + FTEDPP. Aggregate, not a roster.

  - name: instruction_expenses
    type: double
    required: false
    business_term: BT-IPF-INSTRUCTION-EXPENSES
    is_cde: true
    cde_rationale: >
      Raw dollar passthrough exposed at consumable per spec §6
      Transformation 1 specifically so downstream EADA fusion
      (docs/specs/full-pipeline-eada.md) can compute composite ratios
      without back-joining to base. Numerator of instruction_per_fte;
      denominator of marketing_ratio. Re-affirmed from Bronze CDE set
      with expanded consumable rationale. Sources: F1C011 / F2E011 / F3E011.
    is_pii: false
    pii_rationale: ""
    description: >
      Total annual expenses on direct instruction (faculty salaries,
      instructional materials, departmental research). Institution-level
      GAAP aggregate.

  - name: institutional_support_expenses
    type: double
    required: false
    business_term: BT-IPF-INSTITUTIONAL-SUPPORT-EXPENSES
    is_cde: true
    cde_rationale: >
      Raw dollar passthrough exposed at consumable per spec §6
      Transformation 1 for downstream EADA composite-ratio computation.
      Numerator of institutional_support_per_fte and marketing_ratio.
      Re-affirmed from Bronze CDE set with expanded consumable rationale.
      Sources: F1C071 / F2E061 / F3E03C1 (F3 100% non-null on FY2022/FY2023 —
      pre-2014-15 belief that F3 omits this is REFUTED).
    is_pii: false
    pii_rationale: ""
    description: >
      Total annual expenses on day-to-day operational support
      (executive, fiscal, legal, public relations, fundraising,
      recruiting/marketing, admin computing). The "overhead" line.

  - name: endowment_value
    type: double
    required: false
    business_term: BT-IPF-ENDOWMENT-VALUE
    is_cde: true
    cde_rationale: >
      Raw dollar passthrough exposed at consumable per spec §6
      Transformation 1 for downstream EADA composite-ratio computation.
      Sole numerator of endowment_per_fte (also a direct aura composite
      input per docs/specs/full-pipeline-eada.md §6 Decision 11).
      100% structurally NULL on F3 rows (no F3H family); F1A/F2
      endowment imputation prevalence ≈ 25-31% (NCES bureau-imputed,
      accept-as-real per §2 Decision #8). Re-affirmed from Bronze CDE
      set with expanded consumable rationale. Sources: F1H02 / F2H02 / N/A (F3).
    is_pii: false
    pii_rationale: ""
    description: >
      End-of-year market value of an institution's endowment funds.
      Institution-level balance-sheet aggregate. NULL for 100% of F3 rows
      by design.

  - name: institutional_support_per_fte
    type: double
    required: false
    business_term: BT-IPF-PER-FTE
    is_cde: true
    cde_rationale: >
      Directly student-facing per-student spend figure. Drives the "how
      much does this school spend on administration / overhead per
      student" lens on school comparison surfaces. NULL when either
      operand is missing (no imputation per §2 Decision #8). Spec §6
      Data Contract names as CDE candidate. CON-IFP-007 P0 arithmetic
      invariant denominator (institutional_support_per_fte /
      instruction_per_fte ≈ marketing_ratio within 0.001).
    is_pii: false
    pii_rationale: ""
    description: >
      Institutional support expense per FTE student (USD/FTE). NOT
      individual compensation data — institution-level aggregate divided
      by institution-level FTE count.

  - name: instruction_per_fte
    type: double
    required: false
    business_term: BT-IPF-PER-FTE
    is_cde: true
    cde_rationale: >
      Directly student-facing per-student spend figure. Drives the "how
      much does this school spend on me / on teaching per student"
      headline number — the most analytically interpretable of the four
      per-FTE columns and the one most likely to drive student
      decision-making in a fight-card or pentagon-explainer surface.
      NULL when either operand is missing. Spec §6 Data Contract names
      as CDE candidate. CON-IFP-007 arithmetic invariant denominator.
    is_pii: false
    pii_rationale: ""
    description: >
      Instruction expense per FTE student (USD/FTE). NOT individual
      tuition or earnings data — institution-level aggregate divided by
      institution-level FTE count.

  - name: endowment_per_fte
    type: double
    required: false
    business_term: BT-IPF-PER-FTE
    is_cde: true
    cde_rationale: >
      Direct aura composite input per docs/specs/full-pipeline-eada.md
      §6 Decision 11 — one of three forward-looking aura signals
      ("absolute floor of institutional resource gravity" per
      domain-context.md). Also displayed standalone as a per-student
      endowment figure. NULL on 100% of F3 rows by design AND on any
      F1A/F2 row with FTE missing. Spec §6 Data Contract names as CDE
      candidate. The per-FTE column with the most cross-spec leverage —
      wrong here means wrong twice (standalone display + aura composite).
    is_pii: false
    pii_rationale: ""
    description: >
      Endowment value per FTE student (USD/FTE). NOT individual asset
      data — institution-level balance-sheet value divided by
      institution-level FTE count.

  - name: marketing_ratio
    type: double
    required: false
    business_term: BT-IPF-MARKETING-RATIO
    is_cde: true
    cde_rationale: >
      Direct aura composite input per docs/specs/full-pipeline-eada.md
      §6 Decision 11 — the "brand-spend as a share of operating budget"
      plank. Domain-context.md describes as "brand-vs-teaching-spend"
      lens. The most analytically rich single signal in this table
      because it normalizes spend without an FTE denominator — survives
      FTE-NULL rows the per-FTE columns do not. EDA-measured P99 ≈ 5.0
      table-wide; per-form thresholds in BSE-IPF-015a/b/c. Spec §6 Data
      Contract names as CDE candidate. The most-load-bearing column on
      this table — primary input to EADA aura, primary signal on
      standalone marketing-vs-instruction narrative, FTE-independent.
    is_pii: false
    pii_rationale: ""
    description: >
      Institutional support expenses divided by instruction expenses
      (dimensionless ratio). Higher = relatively more spending on
      administration / marketing / recruiting vs. teaching. Bounds vary
      widely; EDA P99 around 5.0 table-wide.

  - name: data_completeness_tier
    type: string
    required: true
    business_term: BT-IPF-DATA-COMPLETENESS-TIER
    is_cde: true
    cde_rationale: >
      Row-level trust gate for downstream consumers. Four-valued enum
      ('high'=4/4, 'medium'=2-3/4, 'low'=1/4, 'insufficient'=0/4). v1.2
      added to spec §6 Data Contract CDE candidate list (renamed from
      confidence_tier in v1.1). Counts independent raw inputs only (NOT
      derived signals — v1.0 formula was reworked to prevent F3
      misleading-'high' classification). EDA distribution
      high=74.7% / medium=25.3% / low=0% / insufficient=0% (CON-IFP-009
      P1 ≥70% high). The "should I show this school card?" and "should
      EADA fusion accept this row?" gate. Per-form skew significant:
      100% of F3 rows land at 'medium' (none at 'high') by construction.
      CON-IFP-005 P0 enum + CON-IFP-006 P0 classification check.
      New consumable-origin CDE flag.
    is_pii: false
    pii_rationale: ""
    description: >
      Source-data-completeness tier synthesized from non-null count of
      the four independent raw inputs (instruction_expenses,
      institutional_support_expenses, endowment_value, total_fte_enrollment>0).
      Values: 'high' (4/4), 'medium' (2-3/4), 'low' (1/4),
      'insufficient' (0/4). NOT a CIP→SOC crosswalk-confidence tier.

  - name: endowment_value_provenance
    type: string
    required: false
    business_term: BT-IPF-ENDOWMENT-PROVENANCE
    is_cde: true
    cde_rationale: >
      Interpretation-changing CDE for endowment_value and
      endowment_per_fte. Renamed passthrough from base
      (endowment_value_flag) per spec §2 Decision A (consumer-clarity
      rename; bronze + base preserve IPEDS-vocabulary 'flag' name).
      Five-code enum on F1A/F2: R = Reported by institution; A = Not
      applicable (institution has no endowment fund — exact A↔NULL
      coupling on endowment_value enforced by BSE-IPF-020 P0;
      community colleges, tribal colleges, theological seminaries,
      system offices); N = Imputed using Nearest Neighbor procedure;
      P = Imputed using prior year's data; Z = Imputed using a zero
      value. Structurally NULL on F3 (no F3H family). Downstream
      interpretation guidance (load-bearing, mirrors
      BT-IPF-ENDOWMENT-PROVENANCE glossary): consumers running
      longitudinal endowment analyses must filter to
      endowment_value_provenance = 'R' to limit to institution-reported
      populated values. Filtering to R is operationally close to
      filtering to endowment_value IS NOT NULL because of the A↔NULL
      coupling, but the explicit R filter is correct: it drops the
      small N/P/Z imputed-value rows that DO carry a populated
      endowment_value. Snapshot benchmarks may use all non-NULL
      endowment_value rows regardless of provenance. The aura_score
      endowment_per_fte plank in consumable.institution_aura
      (docs/specs/full-pipeline-eada.md §6 Decision 11) is the most
      cross-spec-load-bearing consumer of this distinction.
      CON-IFP-013 P0 passthrough fidelity (0 mismatches vs.
      base.ipeds_finance.endowment_value_flag for same UNITID).
      Domain enforced by RAW-IPF-015 (allowed set {R, A, P, Z, N},
      strict subset of dictionary's 13-code shared lookup; any
      unobserved code is a Significant escalation per spec §3 — no
      silent allowed-set extension). Semantic correction history: v1.3
      EDA §7 narrative inverted A and N meanings; v1.4 v1.2 corrected
      against FY2023 dictionary + empirical evidence. Longitudinal
      filter mechanism (= 'R') unchanged in operational outcome
      (because of A↔NULL coupling) but rationale phrasing corrected.
      New consumable-origin CDE flag (v1.4).
    is_pii: false
    pii_rationale: >
      5-code enum literal describing how a per-institution
      endowment_value was sourced. NOT data about a person —
      methodology tag on an institution-level financial aggregate.
    description: >
      IPEDS-published provenance flag for endowment_value, renamed at
      consumable from base's endowment_value_flag. Source: XF1H02
      (F1A) / XF2H02 (F2). Structurally NULL on F3 (no F3H family).
      Observed FY2023 domain on F1A/F2: {R, A, P, Z, N} — strict
      subset of the IPEDS dictionary's 13-code shared Xvarname lookup.
      Authoritative semantics: R = Reported by institution; A = Not
      applicable (institution has no endowment fund — A↔NULL coupling
      invariant per BSE-IPF-020); N = Imputed using Nearest Neighbor
      procedure; P = Imputed using prior year's data; Z = Imputed
      using a zero value. Filter to 'R' for longitudinal endowment
      analyses.

  - name: source_load_date
    type: date
    required: true
    is_cde: false
    cde_rationale: ""
    is_pii: false
    pii_rationale: ""
    description: >
      Restored passthrough from base.ipeds_finance.source_load_date
      per spec §6 Data Contract delta. Documents when the bronze
      source CSV was loaded — distinct from fiscal_year (the IPEDS
      reporting cycle) and from promoted_at (the consumable promote
      timestamp). NCES revises previously-published vintages
      (preliminary → revised → final); source_load_date lets a
      downstream consumer compare two cached snapshots and tell which
      is fresher. NOT NULL guaranteed (CON-IFP-015 P0; mirrors base's
      NOT NULL guarantee per §2 Decision G). Within 400 days of
      promoted_at (CON-IFP-016 P1 freshness rule). Vintage-
      observability metadata only — NOT CDE (does not change
      interpretation of any business metric, does not feed any
      downstream composite, does not gate any consumer decision).

  - name: promoted_at
    type: timestamp
    required: true
    is_cde: false
    cde_rationale: ""
    is_pii: false
    pii_rationale: ""
    description: >
      Consumable promotion batch timestamp. Identical across all 2,675
      rows in a batch. Operational observability only. Annual refresh
      cadence (~Sep N+2 for FY N) is the freshness contract.
```

---

## Summary

| Metric | v1.3 baseline | v1.4 (this re-tag) |
|--------|---------------|--------------------|
| Columns evaluated | 15 | **17** (+2: +`endowment_value_provenance`, +`source_load_date`) |
| Columns flagged CDE | 10 | **11** (+`endowment_value_provenance`) |
| Columns carried forward from Bronze CDE set (re-affirmed in consumable, expanded rationale) | 5 | 5 (`unitid`, `total_fte_enrollment`, `instruction_expenses`, `institutional_support_expenses`, `endowment_value`) |
| Base-derived columns newly tagged at consumable | 4 | 4 (`institutional_support_per_fte`, `instruction_per_fte`, `endowment_per_fte`, `marketing_ratio`) |
| Consumable-origin CDE flags | 1 (`data_completeness_tier`) | **2** (`data_completeness_tier`, `endowment_value_provenance`) |
| Columns flagged PII | 0 | **0** (unchanged) |
| Columns not flagged | 5 | **6** (+`source_load_date`) — `record_id`, `institution_name`, `report_form`, `fiscal_year`, `source_load_date`, `promoted_at` |
| Regulatory frameworks triggered | None mandatory (informational: §132 HEA / IPEDS public-records regime) | unchanged |
| Sensitivity classification | `public` across all 15 columns | `public` across all 17 columns |
| Grain | Institution-level (one row per UNITID per fiscal_year) — structurally precludes person-level PII | unchanged |

---

## Quality SLO Suggestions for the 11 CDEs (v1.4)

These supplement the existing CON-IFP-* and BSE-IPF-* DQ rules. They are CDE-level acceptable-error-rate suggestions for @bs:dq-rule-writer / data-steward to consider beyond the validity / arithmetic / completeness rules already in `governance/dq-rules/consumable-ipeds-finance-profile.json`.

| # | Column | Suggested SLO | Rationale |
|---|--------|---------------|-----------|
| 1 | `unitid` | 100% non-null + unique (zero error tolerance) | Cross-spec join anchor — any error orphans the row. CON-IFP-002/003 already P0. |
| 2 | `total_fte_enrollment` | ≥99% non-null on F1A+F2 rows; F3 separately tracked | Highest-risk field-selection (EFIA-not-EFFY-not-EFTOTLT pin). Per-FTE columns derive from it; EADA `athletic_spend_per_fte` will join through it. |
| 3 | `instruction_expenses` | ≥99% non-null on all forms; per-form imputation prevalence < 1% reportable | Bronze EDA shows imputation < 0.6% (immaterial). If this drifts above 1% in a future cycle, surface as cycle-anomaly. |
| 4 | `institutional_support_expenses` | ≥99% non-null on all forms (F3E03C1 lock validated) | F3 100% non-null on FY2022/FY2023 must hold across cycles — drift would invalidate the §3 column-code lock. |
| 5 | `endowment_value` | F1A+F2 ≥95% non-null; F3 100% NULL (structural invariant); imputation prevalence reportable per cycle (now directly measurable via `endowment_value_provenance`) | NCES bureau-imputation 25-31% accepted per §2 Decision #8 — track per-cycle drift; flag if `(N + P + Z + A)` share exceeds 35% as upstream methodology change. **v1.4 `endowment_value_provenance` makes this prevalence directly measurable from a single column** rather than inferred from missing-value patterns. |
| 6 | `institutional_support_per_fte` | NULL ↔ (operand NULL or FTE ≤ 0) — 100% conformant | No imputation invariant. Already covered by base BSE-IPF-008/009/010 by construction. |
| 7 | `instruction_per_fte` | NULL ↔ (operand NULL or FTE ≤ 0) — 100% conformant | Same as above. |
| 8 | `endowment_per_fte` | NULL ↔ (endowment_value NULL or FTE ≤ 0) — 100% conformant; F3 100% NULL by structural invariant | Same as above; F3 invariant must be separately monitored. |
| 9 | `marketing_ratio` | ≥95% non-null on F1A+F2; F3 ≥85% non-null; per-form P99 within BSE-IPF-015a/b/c bands; CON-IFP-007 arithmetic check 100% pass | Most-load-bearing column; cross-vintage drift watch on per-form P99 (FY2022→FY2023 drift required band recalibration; expect future cycles to require similar recalibration). |
| 10 | `data_completeness_tier` | Enum 100% conformant; CON-IFP-006 classification check 100% pass; `high` ≥70% (P1); `insufficient` ≤1% (P2 watch-line) | Already CON-IFP-005/006/009 covered. Add P2 watch-line on `insufficient` as drift detector — current load is 0%; any non-zero count signals upstream EFIA/HD pipeline regression. |
| 11 | `endowment_value_provenance` (v1.4) | Domain conformant to `{R, A, P, Z, N}` 100% on F1A/F2; structurally NULL on F3 100%; `A`↔NULL bi-implication on `endowment_value` 100% (BSE-IPF-020 P0); per-form `A`-prevalence within bands F1A 5-15% / F2 12-25% (BSE-IPF-019 P1); CON-IFP-013 passthrough fidelity 100%; appearance of any of the 8 unobserved dictionary codes `{B, C, D, G, H, J, K, L}` is a **Significant escalation** (no silent allowed-set extension per spec §3) | Domain enforcement at raw (RAW-IPF-015 P0); per-form prevalence at base (BSE-IPF-019 P1); semantic-invariant at base (BSE-IPF-020 P0); passthrough fidelity at consumable (CON-IFP-013 P0). Cross-cycle drift watch on `A`-prevalence — a sudden jump (e.g., F1A 9.77% → 25%) signals upstream NCES methodology change (e.g., reclassification of a cohort of community colleges into the no-endowment-fund population). The 5-code `{R, A, P, Z, N}` allowed set is a strict subset of the 13-code dictionary; FY2023+ appearance of any of the 8 unobserved codes requires explicit spec-author sign-off before RAW-IPF-015 is amended. |

---

## CDE density commentary

Consumable v1.4: **65% (11/17)**, down from v1.3 67% (10/15) by 2 percentage points because v1.4 adds 1 CDE column and 1 NOT-CDE column (a 1-1 split widening the denominator faster than the numerator). The +1 CDE / +1 NOT-CDE delta is intentional: the v1.4 schema additions split cleanly between an interpretation-changing column (`endowment_value_provenance`, CDE) and a vintage-observability column (`source_load_date`, NOT-CDE). This split mirrors the consumable's existing CDE/non-CDE dichotomy — CDE columns either carry analytical payload, anchor cross-source joins, gate downstream consumer behavior, or change the interpretation of analytical payload values; non-CDE columns are grain surrogates, display labels, provenance/observability metadata, or batch stamps.

Comparison to **BEA RPP precedent** (87% / 13 of 15) remains: BEA RPP has 4 pre-computed display-ready `adjusted_Nk` columns explicitly tagged as new Gold-origin CDEs (display-ready salary adjustments at fixed national anchors); IPEDS Finance does not pre-compute display-ready figures for consumer surfaces — instead it exposes the raw building blocks (`instruction_expenses`, `institutional_support_expenses`, `endowment_value`) at consumable specifically so the **downstream EADA fusion spec** can compute cross-source composite ratios. This is a different consumable shape (raw-input feeder vs. display-ready terminal) and the higher CDE density on raw passthroughs reflects that.

The 6 non-flagged columns split as: 1 grain surrogate (`record_id`), 1 display label (`institution_name`), 2 provenance metadata fields (`report_form`, `fiscal_year`), 1 vintage-observability metadata field (`source_load_date` — v1.4), 1 batch stamp (`promoted_at`) — a tight non-CDE set (no analytical or composite-feeder columns left untagged).

---

## Non-obvious CDE choices (for review)

1. **The three raw dollar passthroughs (`instruction_expenses`, `institutional_support_expenses`, `endowment_value`) are flagged CDE at consumable** despite already being CDE at Bronze. Rationale: spec §6 Transformation 1 explicitly re-exposes them at consumable for downstream EADA cross-spec composite-ratio computation — this is not a redundant carry, it is a deliberate exposure that creates a NEW downstream-facing surface. The CDE flag must follow that exposure. The rationale field at consumable expands the Bronze rationale ("numerator of marketing_ratio") to cover the cross-spec consumer ("upstream feeder for `consumable.institution_aura` per `docs/specs/full-pipeline-eada.md`").

2. **`data_completeness_tier` is flagged CDE despite being a synthesized derivation, not a raw measurement.** Rationale: the spec §6 Data Contract added it to the CDE candidate list in v1.2 specifically because it gates downstream consumer behavior (frontend "show this card?", EADA fusion "accept this row?"). The synthesized nature is irrelevant to its decision-input role — `cost_tier` in BEA RPP is also a synthesized derivation and is also flagged CDE in `gold-regional-price-parities.md` for the same "drives downstream behavior" reason.

3. **`fiscal_year` is NOT flagged CDE despite the BEA RPP precedent that flagged `data_year` as CDE.** Rationale: BEA `data_year` is per-record (different rows can carry different vintages), making it a row-level provenance fact and a per-record reproducibility anchor. IPEDS Finance `fiscal_year` is pinned per ingest run (constant across all 2,675 rows in the FY2023 load), making it a load-level parameter, not a row-level decision input. The cycle-vintage runtime-parameter clarification in domain-context.md is dispositive: promoting to FY24 is a parameter change, not a code or row-level change. If multi-cycle SCD2 is added in a future spec, re-evaluate. Same precedent as `reporting_year` non-CDE in `raw-eada.md`.

4. **`institution_name` is NOT flagged CDE despite being prominently displayed on every school card.** Rationale: the authoritative join key is `unitid`; `institution_name` is carried for UI convenience and operator readability. A mismatched / corrupted name would degrade UX (display the wrong school name) but would not corrupt analytical results (the analytics key off `unitid` regardless). This is the same precedent as `soc_title` non-CDE in `raw-anthropic-economic-index.md` and `institution_name` non-CDE in `raw-eada.md` — display labels are non-CDE; identifier columns and analytical payload columns are CDE.

5. **`total_fte_enrollment` is flagged CDE despite NULL being the appropriate semantic on rows where EFIA did not report.** Rationale: it is the FTE backbone for all four per-FTE columns AND the cross-source FTE pull-through for EADA's `athletic_spend_per_fte` per `docs/specs/full-pipeline-eada.md` §5 Decision 3. Wrong values (vs. NULL — NULL is the correct, semantically-honest signal that FTE is unknown) corrupt the entire downstream FTE-normalized lens. The CDE flag enforces governance attention on the EFIA-not-EFFY-not-EFTOTLT source pin, which domain-context.md flags as the highest-risk field-selection in this pipeline.

6. **(v1.4) `endowment_value_provenance` is flagged CDE despite being a 5-code enum literal that carries no numeric measurement.** Rationale: CDE evaluates *interpretation-changing* impact, not numeric load-bearing. This column is the load-bearing distinction between "the institution reported their endowment as $X" (`R`) and "NCES nearest-neighbor-imputed the institution's endowment as $X" (`N`) — the *value of `endowment_value`* is identical in both rows, but the analytical treatment differs sharply (longitudinal trend lines must filter to `R`; snapshot benchmarks may include all). Without this column, every consumer of `endowment_value` and `endowment_per_fte` is reading a silent mix of institution-reported, NCES-imputed-by-nearest-neighbor, NCES-imputed-from-prior-year, and NCES-zero-imputed values — and silently treating them as homogeneous. CON-IFP-013 P0 passthrough fidelity ensures the renamed column matches base 1:1; RAW-IPF-015 enforces domain at raw; BSE-IPF-019 P1 monitors per-form `A`-prevalence; BSE-IPF-020 P0 enforces `A`↔NULL coupling. The CDE flag is the governance-layer recognition that this column is the difference between "endowment value: $X" and "endowment value: $X (institution-reported)" — and that the difference matters for any analysis longer than a single-cycle snapshot. Same precedent as `fte_source` CDE in `governance/cde-tagging/base-eada.md` (provenance enum tagged CDE because it changes how downstream consumers interpret the per-FTE values).

7. **(v1.4) `source_load_date` is NOT flagged CDE despite being added at the same time as `endowment_value_provenance`.** Rationale: `source_load_date` is *vintage-observability metadata* — when the bronze CSV was loaded — not provenance metadata about a measurement. It does not change the interpretation of any business metric (the values of `endowment_value`, `marketing_ratio`, etc., are interpreted the same regardless of whether the load happened on Tuesday or Thursday); it does not feed any downstream composite (no `aura_score` plank consumes it); it does not gate any consumer decision (CON-IFP-016 freshness rule cross-checks it against `promoted_at` for staleness detection, but freshness is operational, not analytical). The distinction vs. `endowment_value_provenance` is dispositive: provenance-of-the-measurement (CDE) vs. observability-of-the-load (NOT CDE). Same precedent as `source_load_date` non-CDE in `silver-base-college-scorecard-institution-cdes.md` ("Pipeline metadata — provenance tracking only").

---

## Diverges from spec §6 Data Contract CDE candidates list?

Spec §6 Data Contract (v1.4) names as CDE candidates: `marketing_ratio`, `endowment_per_fte`, `institutional_support_per_fte`, `instruction_per_fte`, `data_completeness_tier`, the 3 raw-dollar passthroughs (`instruction_expenses`, `institutional_support_expenses`, `endowment_value`), `unitid`, `total_fte_enrollment`, **and (v1.4) `endowment_value_provenance`**. v1.4 explicitly notes `source_load_date` is NOT CDE.

**v1.4 alignment:** the v1.4 spec §6 Data Contract row "CDE candidates" already enumerates all 11 columns this file flags (per `ipeds-finance-v1.4.md` §6 — *"`marketing_ratio`, `endowment_per_fte`, `institutional_support_per_fte`, `instruction_per_fte`, `data_completeness_tier`, plus the 3 raw-dollar passthroughs and `unitid` and `total_fte_enrollment` (per v1.3 final cde-tagging artifact), + `endowment_value_provenance` (CDE — changes how `endowment_value` and `endowment_per_fte` should be interpreted; longitudinal consumers must filter to `R`); `source_load_date` is NOT CDE (vintage-observability metadata)"*). The v1.3 baseline of this file flagged 5 columns beyond the v1.3 spec §6 data-contract CDE-candidates list (the 3 raw-dollar passthroughs, `unitid`, `total_fte_enrollment`); v1.4 spec §6 brings the spec list into alignment with this file's flagging.

| Column | v1.4 spec §6 alignment |
|--------|------------------------|
| `unitid` | **Listed** in v1.4 spec §6 CDE candidates (rolled in from v1.3 cde-tagging artifact). Cross-spec join anchor (consumable.institution_aura FULL OUTER JOIN per docs/specs/full-pipeline-eada.md §6); CON-IFP-002/003 P0. Same precedent as `unitid` CDE in `raw-eada.md` and `state_fips` CDE in `gold-regional-price-parities.md`. |
| `total_fte_enrollment` | **Listed** in v1.4 spec §6 CDE candidates. FTE backbone for all four per-FTE derivations on this row AND for EADA cross-source FTE pull-through per docs/specs/full-pipeline-eada.md §5 Decision 3. |
| `instruction_expenses` | **Listed** in v1.4 spec §6 CDE candidates. Per spec §6 Transformation 1, explicitly re-exposed at consumable for downstream EADA composite-ratio computation. |
| `institutional_support_expenses` | **Listed** in v1.4 spec §6 CDE candidates. Re-exposed at consumable per spec §6 Transformation 1 for EADA cross-spec composite ratios. |
| `endowment_value` | **Listed** in v1.4 spec §6 CDE candidates. Re-exposed at consumable per spec §6 Transformation 1; sole numerator of `endowment_per_fte` (spec-listed CDE) which is itself a direct aura composite input per docs/specs/full-pipeline-eada.md §6 Decision 11. |
| `endowment_value_provenance` (v1.4) | **Listed** in v1.4 spec §6 CDE candidates ("changes how `endowment_value` and `endowment_per_fte` should be interpreted"). |

**No divergence between this file and v1.4 spec §6 — the 11 CDE flags exactly match the v1.4 spec §6 CDE candidates list.** v1.4 explicitly notes `source_load_date` is NOT CDE; this file follows the same call. Surface to @bs:governance-reviewer for sign-off.

---

## Downstream reminder

CDE flags do not propagate. When `consumable.institution_aura` lands (per `docs/specs/full-pipeline-eada.md` §6 FULL OUTER JOIN of `base.eada` ⨝ `base.ipeds_finance`), @cde-tagger will write `governance/cde-tagging/consumable-institution-aura.md` and re-evaluate `marketing_ratio`, `endowment_per_fte`, `athletic_spend_per_fte`, `athletic_subsidy_ratio`, and the new `aura_score` against the school-card / school-picker product surface. The tagging pass for the aura table is independent of these consumable flags by the no-propagation rule, but the aura table's CDE rationales should reference back to this file as the IPEDS-side input documentation.

When MCP tools begin exposing IPEDS Finance fields (no current spec has scoped this), each MCP response field will be re-evaluated independently in the serving zone.

---

**Path:** `/Users/jcernauske/code/bright/futureproof-data/governance/cde-tagging/consumable-ipeds-finance-profile.md`
