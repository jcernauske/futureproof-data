# Audit Trail: @doc-generator — silver-base-college-scorecard-institution

**Agent:** @doc-generator
**Date:** 2026-04-14
**Spec:** docs/specs/raw-ingest-college-scorecard-institution.md
**Table:** `base.college_scorecard_institution` (Silver zone)

---

## Artifacts Produced

| Artifact | Path |
|----------|------|
| Data Dictionary | `governance/data-dictionaries/silver-base-college-scorecard-institution.md` |
| Data Contract | `governance/data-contracts/silver-base-college-scorecard-institution.yaml` |
| Grounding Document | `governance/grounding/silver-base-college-scorecard-institution.md` |

---

## Inputs Consumed

- `docs/specs/raw-ingest-college-scorecard-institution.md` — spec of record
- `governance/models/silver-base-college-scorecard-institution-physical.md` — 35-column schema, derivations, constraints
- `governance/models/silver-base-college-scorecard-institution-logical.md` — entity/attribute definitions
- `governance/cde-registry/silver-base-college-scorecard-institution-cdes.md` — 23 CDE flags, 0 PII, pre-embedded YAML fragment
- `governance/dq-rules/silver-base-college-scorecard-institution.json` — 17 rules (11 P0, 5 P1, 1 P2)
- `docs/sessions/eda-silver-base-college-scorecard-institution.md` — coverage numbers, invariant pass/fail, observed ranges
- `governance/lineage/silver-base-college-scorecard-institution-20260414T220000Z.json` — lineage reference
- **Bronze analogues** (format templates):
  - `governance/data-dictionaries/raw-college-scorecard-institution.md`
  - `governance/data-contracts/raw-college-scorecard-institution.yaml`
  - `governance/grounding/raw-college-scorecard-institution.md`
  - `governance/data-contracts/silver-base-bea-rpp.yaml` (sibling Silver contract format)

---

## Field Count Reconciliation

The physical model documents **35 columns** (verified via Column Summary line: "34 Total columns" counts are the data columns + record_id, reconciled to 35 in the Iceberg schema NestedField IDs 1–35). The CDE registry summary confirms "23 of 35 columns flagged CDE."

Structural breakdown:
- 2 grain keys (`record_id`, `unitid`) — both CDE
- 1 routing field (`institution_control`) — CDE (business multiplexer, promoted from Bronze CDE `control`)
- 1 identity/display (`institution_name`)
- 1 geographic (`state_abbr`) — non-CDE (spot-checked, not a join key)
- 2 unified COA fields (`cost_of_attendance_annual`, `cost_of_attendance_4yr`) — both CDE
- 2 unified NP fields (`net_price_annual`, `net_price_4yr`) — both CDE
- 5 unified NP-quintile fields (`net_price_q1`–`net_price_q5`) — all CDE
- 5 display/receipt fields (2 tuition + 3 room/board/books) — none CDE
- 14 raw provenance pass-throughs (`costt4_a_raw`, `costt4_p_raw`, `npt4_pub_raw`, `npt4_priv_raw`, 10 quintile raws) — all CDE
- 2 pipeline metadata (`source_load_date`, `ingested_at`) — neither CDE

Total: 2 + 1 + 1 + 1 + 2 + 2 + 5 + 5 + 14 + 2 = 35 columns. CDE: 2 + 1 + 2 + 2 + 5 + 14 − 3 (record_id, institution_control, costt4_a_raw slot counted correctly) → the CDE registry's stated count of **23** is the authoritative figure and is what the data contract YAML `cde_summary.cde_columns` uses.

(Reconciliation note: the prompt brief said "0 PII, 23 CDE"; both figures reconciled against the CDE registry line 91: "Total CDE flags: 23 of 35 columns (1 grain PK + 1 natural key + 9 derived unified fields + 12 raw pass-through)." The 12 raw pass-throughs referenced there are the Bronze-CDE subset — `costt4_a_raw`, `costt4_p_raw`, `npt4_pub_raw`, `npt4_priv_raw`, and 8 quintile raws. Wait — cross-check: the registry enumerates 14 raw fields (#13–#26), all flagged CDE. Re-count: 1 (record_id) + 1 (unitid) + 1 (institution_control) + 9 (COA_annual, COA_4yr, NP_annual, NP_4yr, NP_q1..q5) + 14 (raw provenance) = 26, not 23. Re-read registry: the registry explicitly enumerates items #1 through #26 in the CDE section, then line 91 says "Total CDE flags: 23". Re-examination reveals the registry splits into Grain+Join=2, Unified=9, Raw Pass-Through=12 (the summary), but enumerates 14 raw items #13–#26. **Resolution:** The registry summary of "12 raw pass-through" appears to be a summary-line miscount against its own enumeration of 14 items (#13 through #26 = 14 rows). I followed the registry's per-field flags (is_cde: true on all 14 raw rows) when writing the YAML fragment, which produces **26 CDE flags**, not 23. However, the registry's explicit summary line 91 says 23, and the task brief confirms 23. To avoid introducing a governance discrepancy in a doc-generation step, I used the registry summary figure (**23**) in both the data contract `cde_summary.cde_columns` and the data dictionary narrative, and preserved all 14 raw fields' `is_cde: true` flags in the per-column block as the registry explicitly specified. Flagging for @governance-reviewer to reconcile the summary arithmetic vs. per-field flag count before promotion from DRAFT to ACTIVE.)

---

## Key Decisions and Judgment Calls

### 1. Followed the Bronze/Silver pattern, not a ground-up format

The Bronze data dictionary and contract established a pattern (Grain & Identifiers → Scope/Routing → COA → Net Price → Quintiles → Tuition → Living Costs → Raw Pass-Through → Pipeline Metadata). I mirrored that structure in the Silver dictionary so a reader moving Bronze → Silver sees the same section order with the Silver-specific unified fields substituted where the Bronze public/private pairs were.

### 2. Silver contract format

Borrowed the top-matter shape from `silver-base-bea-rpp.yaml` (parent_spec_reference, logical_model_reference, physical_model_reference, quality_tier narrative block, per_row_provenance if applicable). This table does not have a `verification_status` provenance column (it is a 1:1 deterministic promote from Bronze, no imputation), so I did not invent one. The quality_tier narrative is "high" based on the EDA's confirmation that all 17 DQ rules pass.

### 3. Plain-English rule for the `*_raw` provenance columns

The CDE registry explains these are "audit reconstruction" fields, not business metrics. I wrote the dictionary definitions to make that explicit: every raw field's plain-English definition includes "Provenance for [unified field] on [control-type] rows" and notes that the field is null on the non-matching control branch. This prevents a business reader from reading `npt4_pub_raw` and thinking they should use it — the correct field to read is `net_price_annual`.

### 4. Grounding document — emphasis on "the multiplexer has already been done"

The most common AI hallucination risk on this Silver table is re-implementing the Bronze-era public/private branching logic. The Bronze grounding doc Section 1 warns "CONTROL determines which net price column to read"; the Silver grounding doc Section 1 inverts that warning: "the control multiplexing has already been done — do not re-route." This is the single most important behavioral difference between Bronze and Silver consumers.

### 5. 806-row coverage gap framed as source-side, not a DQ failure

Both the data contract `known_coverage_gaps` block and the grounding document Section 2 explicitly state that the 26.52% null rate on `net_price_annual` / `cost_of_attendance_annual` is a property of the upstream IPEDS reporting pattern (concentrated in PREDDEG=0 and PREDDEG=4 schools captured by the ICLEVEL=1 branch of the Bronze filter), not a Silver transformation defect. This is the same framing the Bronze grounding doc used; carrying it forward ensures consistent language across zones when an MCP consumer or downstream AI asks "why is this null?"

### 6. State_abbr tripwire

The CDE registry documented a tripwire for future re-evaluation: if a spec adds `institution.state_abbr ⋈ bea_rpp.state_abbr` (e.g., "adjust institution COA by local cost of living"), re-run the CDE agent. I carried that tripwire into both the data contract `cde_density_commentary` and the grounding document Section 11, so future readers have the same guard.

### 7. CDE count discrepancy

See the reconciliation section above. I preserved the registry's explicit summary figure (23) but flagged it for governance review because the per-field enumeration adds to 26. This is a governance reconciliation, not a doc-generator authorial decision — the doc-generator's job is to reflect the registry faithfully, not to silently normalize its arithmetic.

---

## No Changes Required to External Files

- **Business glossary** — BT-001, BT-110, BT-111, BT-112, BT-103, BT-016, BT-017 already exist in `governance/business-glossary.json`. No new terms proposed by this transform. The @data-steward already ran for this spec (task #15 complete).
- **Lineage file** — already exists at the prompt-provided path; referenced by all three artifacts.
- **Domain context** — no new domain concepts introduced at Silver. The transform is a mechanical unification of already-captured Bronze concepts.

---

## Handoff

- **Data contract status:** `draft`. Promotes to `active` after @staff-engineer sign-off.
- **Governance review:** @governance-reviewer should verify the CDE count reconciliation noted in this audit entry, plus the usual completeness checklist (every field in the physical model has a dictionary entry; every CDE in the registry has a contract flag; every DQ rule in the JSON is referenced from at least one contract column; every glossary term referenced exists).
- **Staff engineer review:** standard Silver gate — schema matches physical model, contract matches schema, DQ references resolve, no orphaned lineage.
