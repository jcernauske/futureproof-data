# CDE Registry: gold-career-outcomes-college-scorecard

**Table:** `consumable.career_outcomes` (Gold, Consumable zone)
**Spec (original):** `docs/specs/gold-career-outcomes-college-scorecard.md`
**Spec (enrichment):** `docs/specs/raw-ingest-college-scorecard-institution.md` (§Zone 3 — Gold enrichment)
**Transformer:** `src/gold/college_scorecard_career_outcomes.py`
**Physical model:** `governance/models/gold-career-outcomes-college-scorecard-physical.md`
**Data contract:** `governance/data-contracts/consumable-career-outcomes.yaml`
**Prior CDE review:** `governance/reviews/gold-career-outcomes-college-scorecard-cde-tags.md` (2026-04-06, 11 CDEs)
**Silver ancestor registry:** `governance/cde-registry/silver-base-college-scorecard-institution-cdes.md`
**Date:** 2026-04-16
**Agent:** @cde-tagger
**Zone:** Gold (Consumable)

---

## Domain Context Referenced

- `governance/domain-context.md` — Higher Education Outcomes domain. Aggregated program-level statistics from the U.S. Department of Education College Scorecard (Field of Study file + Institution file). All earnings, debt, and cost figures are cohort-level or institution-level aggregates, not individual records. Zero PII exposure (FERPA suppression applied at source).
- `docs/specs/raw-ingest-college-scorecard-institution.md` §Zone 3 — explicitly flags the two new CDEs (`net_price_annual`, `cost_of_attendance_annual`) and the five new non-CDEs (`net_price_4yr`, `institution_control`, `tuition_in_state`, `tuition_out_of_state`, `room_board_on_campus`) on the enrichment join.
- `docs/specs/roi-formula-cost-of-attendance.md` — Follow-up spec that consumes `net_price_annual` as the ROI denominator. Confirms the criticality rationale carried forward from the Silver registry: this column drives every ROI score and Fight Student Loans outcome for institutions with a UNITID match.
- **Regulatory alignment:** Department of Education Gainful Employment rule methodology informs the debt-to-earnings ratio as a key affordability metric. FERPA governs privacy suppression at source. No BCBS 239 / HIPAA / GDPR / CCPA / GLBA / SOX / PCI exposure. CDE identification follows BCBS 239 principles (columns critical to downstream business processes and management decisions).
- **No-propagation policy:** Silver's 26 CDE flags on `base.college_scorecard_institution` do **not** propagate forward. Each Gold column is re-evaluated against Gold-zone consumer patterns (MCP tools, stat engine, Fight Student Loans, receipts, loan-slider UI).

---

## Table Context: What Changed at Gold

The enrichment spec adds 7 institution-level cost columns to `consumable.career_outcomes` via a LEFT JOIN on `unitid`. Row count is preserved at 69,947. All 7 columns are nullable (unmatched UNITIDs get NULL).

Per spec §Zone 3, 2 of the 7 new columns are flagged CDE and 5 are not. Rationale per column below.

---

## Prior-State CDE Inventory (2026-04-06)

The 2026-04-06 CDE review flagged 11 CDE columns on `consumable.career_outcomes`. All 11 are preserved unchanged on this update. Listing for cross-artifact reconciliation:

| # | Column | is_cde | Source |
|---|--------|--------|--------|
| 1 | `unitid` | **true** | Grain component / join key |
| 2 | `earnings_1yr_median` | **true** | Primary business metric |
| 3 | `earnings_2yr_median` | **true** | Primary business metric |
| 4 | `debt_median` | **true** | Primary business metric |
| 5 | `earnings_1yr_p25` | **true** | Effort slider lower bound (1yr) |
| 6 | `earnings_1yr_p75` | **true** | Effort slider upper bound (1yr) |
| 7 | `earnings_2yr_p25` | **true** | 2yr range lower bound |
| 8 | `earnings_2yr_p75` | **true** | 2yr range upper bound |
| 9 | `debt_p25` | **true** | Debt range lower bound |
| 10 | `debt_p75` | **true** | Debt range upper bound |
| 11 | `debt_to_earnings_annual` | **true** | Gainful-Employment-aligned affordability metric |

---

## New CDE Flags Added on This Update (2026-04-16)

### Columns Flagged as CDE — Institution Enrichment (2)

| # | Column | Type | is_cde | Rationale |
|---|--------|------|--------|-----------|
| 12 | `net_price_annual` | double | **true** | **Becomes the ROI-formula driver in the follow-up spec `roi-formula-cost-of-attendance.md`**, replacing `debt_median` as the denominator input (`ROI = earnings / (net_price × 4 × loan_pct)`). **Directly consumed by MCP `get_school_programs`** as the authoritative per-year-cost-after-aid field exposed to Gemma and the product UI. Every ROI score and Fight Student Loans outcome for a student at a matched-UNITID institution will trace through this single column. Inherits P0 invariants from Silver (`net_price_annual ≤ cost_of_attendance_annual`; range $-10,000 – $80,000 with negative-value allowance for high-aid institutions). BT-111 (Net Price). Highest-criticality column among the 7 enrichment fields. |
| 13 | `cost_of_attendance_annual` | double | **true** | **Upper-bound invariant partner for `net_price_annual`** (GLD-CSI-002: `net_price_annual ≤ cost_of_attendance_annual`). An invariant partner is operationally CDE — violations mean either `net_price_annual` is wrong (silently inflating costs) or `cost_of_attendance_annual` is wrong (silently breaking the sticker-price display). **Primary display field for receipts** on the CareerCard ("Cost of attendance per year: $22,800 sticker / $14,200 after aid"). Also the intended basis for a future `cost_of_attendance_4yr = cost_of_attendance_annual × 4` derivation if/when surfaced at Gold. BT-110 (Cost of Attendance). |

### Columns Evaluated — Not Flagged — Institution Enrichment (5)

Per spec §Zone 3 explicit guidance:

| # | Column | Type | is_cde | Reason Not Critical |
|---|--------|------|--------|---------------------|
| 14 | `net_price_4yr` | double | false | **Derivable display field** — `net_price_annual × 4`. Pre-materialized for query-performance convenience, but all business criticality lives on `net_price_annual` (the CDE above). Not an independent decision input; an error here can be detected and healed from the CDE partner. |
| 15 | `institution_control` | varchar | false | **Categorical, segmentation/bracket-selection only.** Values: 'Public', 'Private nonprofit', 'Private for-profit'. Used to label the CareerCard and to pick which institution-type bracket to show; the `control`-multiplexer that picks `npt4_pub` vs `npt4_priv` was already consumed at Silver, so the column is informational at Gold rather than load-bearing. Closes the 2026-04-06 insight-report recommendation to surface institution type (previously 100% null). Aligned with the prior CDE review's 2026-04-06 decision. |
| 16 | `tuition_in_state` | double | false | **Display-only.** Tuition is one component of `cost_of_attendance_annual` (already a CDE); surfacing it here improves receipt transparency ("your $22,800 COA breaks down as: $11,200 tuition + …") but it does not drive any stat, boss, or ROI calculation. |
| 17 | `tuition_out_of_state` | double | false | **Display-only.** Same role as `tuition_in_state` — already rolled into `cost_of_attendance_annual`. Receipts only. |
| 18 | `room_board_on_campus` | double | false | **Display-only.** Already rolled into `cost_of_attendance_annual` per the Scorecard COA definition (tuition + fees + books + room & board + living expenses). Receipts only. |

---

## PII Summary

**PII flagged:** 0 of 34 columns.

No change from prior state. All 7 new columns are aggregate institution-level data (public federal source, Level 1 Public classification inherited from Bronze/Silver). No individual-level records. FERPA protections applied upstream by IPEDS before publication. No HIPAA, GDPR, CCPA, GLBA, SOX, or PCI exposure.

---

## Summary

| Metric | Pre-update (2026-04-06) | Post-update (2026-04-16) | Delta |
|--------|-------------------------|--------------------------|-------|
| Columns evaluated | 27 | **34** | +7 (institution enrichment) |
| Columns flagged CDE | 11 | **13** | **+2** (`net_price_annual`, `cost_of_attendance_annual`) |
| Columns flagged PII | 0 | **0** | 0 |
| Columns not flagged | 16 | 21 | +5 (4 display-only cost components + 1 derivable 4yr total) |
| CDE density | 40.7% | 38.2% | −2.5pp (enrichment adds mostly display fields) |
| Regulatory frameworks triggered | None | None | — |
| Sensitivity classification | `public` across all columns | `public` across all columns | — |

### Delta commentary

The +2 CDE delta is exactly what the spec prescribes. `net_price_annual` is the single most important column added to Gold in this spec — it is the ROI denominator in the follow-up formula spec and the anchor of the receipt display. `cost_of_attendance_annual` is its mandatory invariant partner (GLD-CSI-002) and the primary sticker-price field on receipts. The other 5 enrichment columns are correctly left non-CDE per spec: 4 are display components already rolled into COA, and `net_price_4yr` is a derivable convenience field.

### Cross-artifact consistency

| Artifact | CDE count | Aligned? |
|----------|-----------|----------|
| This registry (§Summary, post-update) | **13** | — |
| `governance/data-contracts/consumable-career-outcomes.yaml` `cde_summary.cde_columns` length | **13** (11 pre-existing + 2 new) | yes |
| `governance/data-dictionary.json` → `consumable.career_outcomes` columns where `is_cde: true` | **13** (11 pre-existing + 2 new institution-enrichment entries) | yes |
| `governance/models/gold-career-outcomes-college-scorecard-physical.md` Column Summary | **13** (post doc-generator update) | pending @doc-generator sync |

The physical model's Column Summary will be resynced by @doc-generator as part of this pipeline step. The contract and data-dictionary are updated alongside this registry in the same governance commit.

### Downstream reminder

CDE flags do not propagate. The MCP surface tables (`mcp.futureproof_get_school_programs`, `mcp.futureproof_get_career_paths`) that read from `consumable.career_outcomes` will be re-evaluated on their own contracts when those MCP-zone specs land — expect `net_price_annual` and `cost_of_attendance_annual` to stay CDE on those surfaces (they are the direct consumer exposure point for the ROI denominator), with the 5 display fields potentially CDE or not depending on which ones the MCP tools choose to project.
