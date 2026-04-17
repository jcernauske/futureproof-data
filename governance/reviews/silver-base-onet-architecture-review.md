# Principal Data Architect Review — silver-base-onet

**Date:** 2026-04-16
**Reviewer:** @principal-data-architect
**Scope:** Silver → Gold transition review (silver-base-onet)
**Domain:** Workforce / career guidance (U.S. labor market — SOC 2018 occupation taxonomy, O*NET Content Model)
**Tables reviewed:** `base.onet_occupations` (798), `base.onet_activity_profiles` (31,734), `base.onet_context_profiles` (44,118), `base.onet_career_transitions` (15,944)

---

## Executive Summary

Silver-base-onet is the most structurally sophisticated Silver transformation in the FutureProof pipeline, and it is built correctly. Four tables, one grain decision (O*NET 8-digit → BLS 6-digit truncation with N:1 aggregation for 76 multi-detail SOCs), clean separation between normalization and business logic, zero orphaned FKs, and 37/37 DQ rules passing against live data. The adversarial audit confirmed every numeric claim against the Iceberg warehouse, and the entity-resolution review confirmed that cross-source SOC alignment against `base.bls_ooh` and `base.karpathy_ai_exposure` is structural and explainable, not defective.

The biggest architectural strength is the deliberate choice to aggregate O*NET's finer `XX-XXXX.XX` grain to BLS's `XX-XXXX` grain at the Silver boundary. That decision pays off across every downstream consumer — crosswalk joins are clean, Gold tables don't need to re-aggregate, and cross-source asymmetries become diagnosable rather than silent.

The biggest concern is governance drift: the spec, glossary, and a subset of DQ rule rationales were written pre-EDA and never reconciled. The adversarial auditor's F-01 (the `Responsibility for Outcomes and Results` → `Impact of Decisions on Co-workers or Company Results` substitution) is a real semantic issue. It gates burnout-dependent Gold work. It does not gate non-burnout Gold work.

---

## 1. Zone Boundary Integrity

**Assessment: STRONG.**

Silver is doing Silver-zone work, and nothing else:

- **Normalization, filtering, typing, deduplication, grain flattening** — all present. `src/silver/onet_transformer.py:58` truncates `XX-XXXX.XX` to `XX-XXXX`. IM-only filtering for activities (line 263); CX/CT-only filtering for context (line 331); self-reference and dedup for transitions (lines 392-404).
- **Multi-detail N:1 aggregation** using unweighted averaging (activities/context) and min-index (transitions) — a modeling decision, not business logic. Lineage preserved via `onet_detail_codes` JSON array.
- **No scoring, no weighting, no business-metric computation.** `is_high_importance` at `importance >= 3.5` is a flag derived from a documented threshold, not a weighted score; `is_burnout_element` is a boolean membership flag, not a burnout score; `relatedness_tier` is a deterministic bucket from `best_index`, not a curated ranking.
- **Task Statements deliberately left in Bronze.** Correct call — Silver adds no value to free-text, and Gold/Gemma consume the text directly. This is the right instinct: do not ingest for ingestion's sake.

One minor architectural smell: `importance_rank` (1-41 per occupation) is a derived ordering that arguably belongs to Gold, since ranks change whenever the importance scale is reweighted. Here it is harmless because the O*NET IM scale is stable and the rank is purely positional within the source data, but if FutureProof ever introduces a custom weighted importance, this rank will need to move. Flagging as a known debt, not a blocker.

**Grade: A-**

---

## 2. Grain & Keys — O*NET 8-digit vs BLS 6-digit Truncation

**Assessment: CORRECT DECISION, CORRECTLY EXECUTED.**

The core architectural choice — truncate O*NET-SOC (`XX-XXXX.XX`, 1,016 codes) to BLS SOC (`XX-XXXX`, 798 derivable) at the Silver boundary — is right. Rationale:

1. **BLS OOH publishes at 6-digit granularity.** `base.bls_ooh` has 832 rows at `XX-XXXX`. If Silver kept O*NET's finer grain, every Gold join would need an ad-hoc rollup, and the rollup rules would leak into Gold.
2. **CIP-SOC crosswalk emits 6-digit SOC.** Keeping finer grain in O*NET Silver would force a crosswalk-time explosion or a pre-Gold aggregation step.
3. **Karpathy AI exposure uses 6-digit SOC.** Same argument.

The N:1 aggregation for 76 multi-detail BLS SOCs (verified `multi_detail_flag=true` count = 76) is handled via:

- **Activities/Context:** unweighted average across contributing O*NET detail codes. Acceptable for hackathon; the correct long-term answer is BLS-employment-weighted average, but BLS employment at detail-SOC-level isn't readily available. Spec flagged this as Open Decision #2. No action required now.
- **Transitions:** min-index (best-of) selection across all contributing detail-pair combinations. Semantically sound: "most-similar" should survive the rollup. 2,173 duplicate BLS pairs correctly collapsed to 15,944 unique pairs.
- **Lineage preservation:** Every aggregated row carries `onet_details_averaged` (contributing count) and `onet_detail_codes` (JSON array on the occupation row). A Gold consumer can reverse to raw grain if needed.

**Live-data verification (2026-04-16):**
- `onet_occupations`: 798 rows, 798 distinct `bls_soc_code`, 100% format-valid `^\d{2}-\d{4}$`
- `multi_detail_flag=true`: exactly 76
- `data_completeness_tier`: 774 full + 24 partial + 0 none (matches DQ SLV-ONET-005)
- Zero intra-Silver FK orphans across all 4 tables
- 9 distinct burnout element IDs present, exactly the 9 the transformer enumerates

**Grade: A**

---

## 3. Integration Risks for Gold (SOC Alignment with bls-ooh and karpathy)

**Assessment: ASYMMETRIC BUT STRUCTURALLY SOUND.** Live-data measurements (2026-04-16):

| Alignment | Count | Interpretation |
|-----------|-------|---------------|
| `onet_occupations` ↔ `bls_ooh` intersection | **773** | Clean shared identity |
| ONET SOCs not in BLS OOH | **25** | ONET publishes detail-level occupations where BLS OOH rolls up to parent SOC |
| BLS OOH SOCs not in ONET | **59** | BLS OOH includes catchall/"All Other"/broad residual codes (flagged at BLS OOH ingest); ONET correctly drops these |
| `onet_occupations` ↔ `karpathy` intersection | **372** | Karpathy coverage is a subset, not full SOC space |
| Karpathy SOCs not in ONET | **24** | Karpathy-side taxonomy issues (4-digit aggregates like `19-5000`, plus post-Karpathy SOC 2018 codes) — already flagged on Karpathy ingest via `soc_resolved_method` |

### Implications for Gold zone

1. **Use LEFT JOIN semantics in both directions when unifying ONET ↔ BLS OOH ↔ Karpathy.** INNER JOIN will silently drop 59 BLS SOCs (7%) and 25 ONET SOCs (3%). The existing Gold `consumable.program_career_paths` and `consumable.occupation_profiles` tables need source-coverage flags (`has_onet_data`, `has_bls_ooh_data`, `has_karpathy_data`) surfaced to the MCP layer.
2. **Do NOT attempt to "fix" the asymmetry at Silver.** It is structural: BLS OOH and ONET publish at different roll-up levels of SOC 2018 for deliberate reasons. Forcing symmetry would corrupt at least one source.
3. **Karpathy's 24-row gap is a Karpathy-side issue, not an ONET defect.** If Gold needs fuller Karpathy coverage, the fix is parent-SOC rollup on the Karpathy side (already designed), not ONET expansion.

### Risk to Gold

The existing Gold tables (`consumable.onet_work_profiles` 798 rows; `consumable.career_transitions` 15,944 rows) were built from this Silver and already show the expected row counts. `consumable.occupation_profiles` (832 rows) is correctly keyed off BLS OOH as the broader set, which is the right design — BLS OOH is the market-facts anchor, ONET is the work-content overlay, and the union matters.

**Grade: A-**

---

## 4. Response to F-01 Burnout Finding — Scope of Block

**Assessment: F-01 BLOCKS BURNOUT-DEPENDENT GOLD WORK ONLY. It does NOT block non-burnout Gold work.**

I agree with the adversarial auditor's diagnosis that the substitution of `4.C.3.a.2.a` "Impact of Decisions on Co-workers or Company Results" for the nonexistent spec-proposed "Responsibility for Outcomes and Results" is a material semantic change that lacked distinct human sign-off. The bulk-timestamp approval on all 37 DQ rules (all within an 8ms window) does not meet the Open Decisions gate the spec itself declared.

### Architectural scope analysis

The `is_burnout_element` flag is a **localized derived attribute** on `base.onet_context_profiles`. Nothing else in Silver depends on it. Downstream impact is contained:

- **Burnout-dependent Gold consumers:** `consumable.onet_work_profiles` uses `is_burnout_element` to drive the Burnout boss-fight score. `gold-futureproof-engine` Burnout formula inherits it. Any Gold product that filters `WHERE is_burnout_element = TRUE` is downstream of this decision.
- **Non-burnout Gold consumers:** Everything else — HMN stat (activity importance), career branching (transitions), ERN/ROI/GRW (BLS OOH-driven), RES (Karpathy), the full occupation profile surface, `program_career_paths`, `career_outcomes`, `ai_exposure`, the entire CIP→SOC crosswalk path — is unaffected by `is_burnout_element`.

### Verdict on scope

**F-01 does not constitute a blanket silver→gold block.** It is a narrow, scoped block on any new or re-run Gold work that filters on `is_burnout_element`. The existing `consumable.onet_work_profiles` Burnout column may continue to serve until the substitution is either (a) explicitly human-approved with a distinct audit-trail entry, or (b) dropped and re-shipped as an 8-element set. Gold work for non-burnout stats (HMN, ERN, ROI, GRW, RES, career branching, program pathing) can proceed without resolving F-01.

Operationally, I recommend attaching F-01 resolution to the next `gold-futureproof-engine` spec revision or to a dedicated burnout-scoring spec, not to the silver→gold transition gate itself. Gating all of Gold on one semantic substitution is disproportionate.

### Recommended resolution (restating auditor's path)

Log `governance/audit-trail/2026-04-16-burnout-element-substitution-approval.md` with explicit human sign-off before the next Gold burnout-formula change. Co-sign by the spec's Open Decisions reviewer and the Gold Burnout formula owner. Alternative: drop element 9 and ship 8 burnout elements. Either path closes F-01.

**Grade on finding handling: B+** — auditor flagged correctly; scoping judgement (burnout-only block) is mine, not the auditor's, but consistent with the auditor's own "this does NOT block the silver→gold transition outright" language.

---

## 5. Schema Evolution Risk / Contract Readiness

**Assessment: CONTRACTS ARE STRUCTURALLY SOUND BUT STALE ON METADATA.**

### Structural readiness

All four data contracts exist (`base-onet-occupations.yaml`, `base-onet-activity-profiles.yaml`, `base-onet-context-profiles.yaml`, `base-onet-career-transitions.yaml`). Grain declarations, column types, nullability constraints, row-count expectations, and cross-table FK relationships all match the physical Iceberg schema (`src/silver/onet_transformer.py:81-147`) and the DQ rule set. CDE tagging is present on `bls_soc_code` (primary join key) and `data_completeness_tier` (downstream filter condition) with substantive rationale, not boilerplate.

### Schema evolution risk

Low. The Iceberg schemas are well-typed (StringType for IDs, DoubleType for values, BooleanType for flags, DateType/TimestampType for lineage metadata). Field IDs are stable and sequential. Full-replace promote pattern (line 525) means there is no append-only migration risk. O*NET releases annually; SOC 2018 taxonomy is stable through ~2028. The only foreseeable schema change is adding a `relationship_type = "transition"` value if Career Changers/Starters data ever reappears in O*NET — the contract already accommodates this via the non-enum declaration on `relationship_type`.

### Contract staleness risk (tracked to adversarial F-02, F-03, F-04, F-07)

The **business glossary** (BT-059 burnout element list, BT-062 suppress-rate percentages, BT-064 partial-occupation count) and the **spec document itself** (row-count estimates, burnout element IDs, 29-vs-24 drift, 93-vs-69 excluded count) were never updated after the EDA corrected them. The DQ rules, scorecards, transformer code, and Iceberg data all agree with each other; the glossary and spec disagree with all of them.

This is a governance-integrity issue, not a data issue. It matters for Gold because:
- Gold spec authors are instructed to pull numbers from the Silver spec. They will pull wrong numbers.
- A reviewer or regulator reading BT-059 will see a burnout element list that doesn't match the shipped data.

**Recommended remediation before Gold work that reads this spec:** add an "EDA Corrections" block to `docs/specs/silver-base-onet.md` pointing to `governance/eda/silver-onet-eda.md` as authoritative, and update BT-059 / BT-062 / BT-064 in the glossary. None of these blocks Gold work, but all should be done in parallel with any new Gold spec.

**Grade: B+** — contracts are accurate to the data; glossary/spec drift is a separate remediable concern.

---

## 6. Top Risks (Principal-level)

1. **Burnout semantic substitution (F-01).** Narrow but real. Blocks re-cast of any Burnout-scored Gold artifact until human sign-off is logged distinctly from the bulk DQ-rule approval. Mitigation: one audit-trail entry, co-signed.
2. **Governance artifact drift (F-02/F-03/F-04/F-07).** Spec and glossary disagree with DQ rules and transformer. Future spec authors will inherit wrong numbers. Mitigation: in-place edits to glossary terms and an EDA-corrections block on the spec.
3. **Unweighted multi-detail averaging for 76 BLS SOCs.** Correct for hackathon, technically inferior to employment-weighted. Not actionable now; flag in the Gold spec for `gold-futureproof-engine` burnout/stat formulas so downstream consumers know the aggregation method.

---

## 7. What I'd Cut

Nothing major. Silver is lean. If I were forced to cut one thing, I'd question whether `importance_rank` belongs in Silver (see §1) — it is the one derived field that has a whiff of Gold leakage. Leave it for now; revisit if an importance reweighting ever enters the design.

---

## 8. What's Missing for Production

1. **F-01 resolution audit-trail entry** (blocker only for burnout-dependent Gold).
2. **Glossary reconciliation** for BT-059, BT-062, BT-064.
3. **Spec EDA-corrections block** or equivalent pointer to the EDA as authoritative.
4. **Source-coverage flags** (`has_onet_data`, `has_bls_ooh_data`, `has_karpathy_data`) should be surfaced on any Gold product that unifies ONET ↔ BLS OOH ↔ Karpathy — the 25/59/24-row asymmetries must not be invisible to the MCP consumer.

---

## 9. Verdict — Silver → Gold Transition

**APPROVED_WITH_CAVEATS.**

The silver-base-onet pipeline produces correct, well-grained, FK-consistent, DQ-verified data that is fit for Gold-zone consumption. Cross-source SOC alignment is structurally sound. The architectural choices (6-digit BLS SOC identity, N:1 multi-detail aggregation with lineage, CX/CT-only context filtering, best-index transition dedup) are all defensible and would survive 10x data volume with no material changes.

### Scope of the caveats

| Caveat | Blocks Gold? |
|--------|-------------|
| F-01 (burnout element substitution lacks distinct human approval) | **Burnout-dependent Gold only.** `consumable.onet_work_profiles` Burnout column, `gold-futureproof-engine` Burnout formula. Must close before re-cast or any new burnout-scored Gold artifact. |
| F-02/F-03/F-04/F-07 (glossary / spec drift) | **No.** Governance documentation debt. Fix in parallel with new Gold spec authoring. |
| F-05 (DQ rule ID gaps) | **No.** Cosmetic. |
| F-06 (chaos recommendations unclosed) | **No.** Adequately controlled. |
| Unweighted multi-detail averaging | **No.** Documented modeling decision. |

### Grade: A-

Ship it. Non-burnout Gold work (HMN, ERN, ROI, GRW, RES, career branching, program pathing, occupation profiles, AI exposure) is cleared to proceed. Burnout-dependent Gold work is gated on F-01 closure — document the human approval for the `4.C.3.a.2.a` substitution in `governance/audit-trail/` and burnout-Gold is unblocked.

This is solid Silver-zone engineering. The numeric facts are reproducible, the grain logic is correct, the FK integrity is clean, the cross-source asymmetries are structural rather than defective, and the one real semantic concern (F-01) is narrow, known, and resolvable with a single audit-trail entry. I would stake my reputation on this Silver output as the foundation for Gold.

---

## User-Deferred Decisions

None in this review — the caveats above are all remediable mechanical actions, not architectural choices requiring user input. The F-01 resolution (human approval vs drop-the-element) is a decision for the burnout-scoring spec owner, not for this transition gate.
