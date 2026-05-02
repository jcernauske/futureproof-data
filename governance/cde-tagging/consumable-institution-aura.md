# CDE Tagging: `consumable.institution_aura`

**Table:** `consumable.institution_aura` (Gold, Consumable zone)
**Spec:** `docs/specs/full-pipeline-eada.md` §6 Data Contract (post-Option-C amendment 2026-04-30)
**Transformer:** `src/gold/institution_aura.py`
**Data contract:** `governance/data-contracts/consumable-institution-aura.yaml` (pending)
**PII scan:** `governance/pii-scans/consumable-institution-aura-pii-scan.md` (NO PII)
**EDA:** `governance/eda/consumable-institution-aura-eda.md`
**Date:** 2026-05-01
**Agent:** @cde-tagger
**Zone:** Gold (Consumable)

---

## Domain Context Referenced

- `governance/domain-context.md` — Higher Education Institutional Finance + Athletics. Federally mandated public disclosures (IPEDS Finance via NCES; EADA via OPE/Title IX). Institution-level aggregates only.
- `docs/specs/full-pipeline-eada.md` §1, §2 (Decisions 3, 5, 7, 8, 10, 11), §6 Data Contract, §6 Business Glossary Terms, §7 fp-architect issue #2 (CDE candidate addition), §7 fp-architect issue #6 (final candidate list).
- **Regulatory alignment:** Department of Education Title IX gender-equity reporting consumes `athletic_spend_per_fte` and `athletic_subsidy_ratio`. NCES IPEDS Finance reporting consumes `endowment_per_fte` and `marketing_ratio` (institutional support / instruction). Knight Commission per-FTE benchmarks consume `athletic_spend_per_fte` denominated against EADA's `EFTotalCount` — making `athletic_fte_source` a methodological-provenance CDE that downstream consumers must stratify on.
- **Sensitivity tier:** Public (Level 1 per PII scan §Sensitivity Classification). All CDE flags below inherit this tier — no row-level security, no column masking, standard public-data handling.
- **No-propagation policy:** `base.eada` and `base.ipeds_finance` CDE flags do NOT propagate forward. Each Gold column is re-evaluated against the consumable's role as the institution-level brand-gravity signal.

---

## Columns Flagged as CDE (6)

| # | Column | Type | Tier | is_cde | Glossary Candidate | Rationale |
|---|--------|------|------|--------|--------------------|-----------|
| 1 | `aura_score` | int | Public | **true** | **BT-AUR-AURA-SCORE** (proposed §6) | Primary deliverable of the spec — the 1–10 neutral brand-gravity composite that this entire pipeline exists to produce. Versioned `"v1"` (EDA-finalized 2026-04-30 via MAX+MEAN composite, P5/P95 percentile rescale). Used downstream by Stage-2 reveal context, pentagon shape interpretation alongside ERN/ROI, and any future MCP tool surfacing institution-level brand gravity. CON-AUR-010 / CON-AUR-013 / CON-AUR-014 P0 invariants gate validity. |
| 2 | `marketing_ratio` | double | Public | **true** | **BT-AUR-MARKETING-RATIO** (proposed; new BT-AUR-* term — final ID @bs:data-steward) | Aura input #1 (per §2 Decision 11). Direct, non-inverted brand-presence signal — `institutional_support / instruction` from IPEDS Finance. Independent of the FTE methodological mix (no per-FTE denominator). Feeds `aura_score` for all rows where `aura_score_basis ∈ {three_term, two_term_finance_only, two_term_no_endowment, one_term_marketing_only}`. Critical to every aura computation. |
| 3 | `endowment_per_fte` | double | Public | **true** | **BT-AUR-ENDOWMENT-PER-FTE** (proposed; new BT-AUR-* term — final ID @bs:data-steward) | Aura input #2 (per §2 Decision 11). Direct, non-inverted brand-presence signal from IPEDS Finance. Per-FTE denominator is IPEDS-Finance annualized FTE — no methodological mix on this column. Feeds `aura_score` for `aura_score_basis ∈ {three_term, two_term_finance_only}` (~75 rows fall back to `two_term_no_endowment` when endowment is NULL). |
| 4 | `athletic_spend_per_fte` | double | Public | **true** | **BT-AUR-ATHLETIC-SPEND-PER-FTE** (proposed; per §7 fp-architect issue #7 advisory; new BT-AUR-* term — final ID @bs:data-steward) | Aura input #3 (per §2 Decision 11; added to candidate list per §7 fp-architect issue #6 to close the asymmetric exclusion). EADA-side direct brand-presence signal — `total_athletic_expenses / COALESCE(total_fte_enrollment, eada_fte_headcount)`. Feeds `aura_score` for `aura_score_basis ∈ {three_term, two_term_no_endowment}`. **Methodological caveat:** the per-FTE denominator is mixed across rows — see `athletic_fte_source` (CDE #6) for stratification. Knight Commission benchmark-comparable only on the `eada_fte_headcount` stratum. |
| 5 | `athletic_subsidy_ratio` | double | Public | **true** | **BT-EAD-ATHLETIC-SUBSIDY-RATIO** (proposed §6) | **Context-only CDE** — explicitly NOT an aura_score input (per §2 Decision 11) but flagged because it is the primary Title IX / equity-policy signal carried on the consumable. `(total_athletic_expenses - total_athletic_revenue) / total_athletic_expenses`. Independent of the FTE methodological mix (numerator and denominator share units). Critical for downstream consumers asking equity questions about 2-year colleges (NJCAA / CCCAA / NWAC) — exactly the population whose coverage Option-C preserved. Bounded [-3.0, 1.0] per BSE-EAD-007 (silver-EDA-calibrated). |
| 6 | `athletic_fte_source` | string | Public | **true** | **BT-AUR-ATHLETIC-FTE-SOURCE** (proposed; new BT-AUR-* term — final ID @bs:data-steward) | **Methodological-provenance CDE** (added with Option-C amendment 2026-04-30 per §6 Data Contract). 3-value enum: `'ipeds_finance'` (~74.5% — annualized FTE) / `'eada_fte_headcount'` (~25.5% — 12-month headcount, predominantly 2-year colleges) / `'none'`. The two FTE definitions are NOT identical — Knight Commission per-FTE benchmarks align to `eada_fte_headcount`, while internal cross-column consistency with `endowment_per_fte` aligns to `ipeds_finance`. Without this column, downstream consumers cannot tell which methodological regime any given `athletic_spend_per_fte` value sits in. Tagging it CDE is what converts the methodological mix from an implicit assumption into an audited, queryable property — directly fulfilling the §6 EDA item 7 stratification mandate. |

---

## Upstream Lineage

Per §6 transformation rules and the no-propagation policy, gold-zone CDE flags are independent of upstream flags. The lineage references below are documentation only — they do NOT auto-propagate is_cde.

| Gold Column | Upstream Source | Upstream Column |
|-------------|----------------|-----------------|
| `aura_score` | derived | composite of marketing_ratio + endowment_per_fte + athletic_spend_per_fte |
| `marketing_ratio` | `base.ipeds_finance` | `marketing_ratio` (= institutional_support / instruction) |
| `endowment_per_fte` | `base.ipeds_finance` | `endowment_per_fte` |
| `athletic_spend_per_fte` | `base.eada` | `athletic_spend_per_fte` (numerator: `total_athletic_expenses`; denominator: COALESCE per Decision 3) |
| `athletic_subsidy_ratio` | `base.eada` | `athletic_subsidy_ratio` |
| `athletic_fte_source` | `base.eada` | `fte_source` (pass-through) |

Upstream CDE registries to be authored when `base.eada` and `base.ipeds_finance` data contracts land:
- `governance/cde-registry/base-eada-cdes.md` (expected: `total_athletic_expenses`, `total_athletic_revenue`, `athletic_spend_per_fte`, `athletic_subsidy_ratio`, `fte_source`, `eada_fte_headcount`)
- `governance/cde-registry/base-ipeds-finance-cdes.md` (expected: `endowment_per_fte`, `marketing_ratio`, `total_fte_enrollment`, `institutional_support`, `instruction`)

---

## Columns Evaluated — Not Flagged as CDE (13 of 19)

| Column | Reason Not Flagged |
|--------|--------------------|
| `unitid` | Grain / join key. Identifier, not a critical business measure. (Tag at base layer if needed.) |
| `institution_name` | Display label; not a measure. Public per PII scan. |
| `has_ipeds_finance` | Coverage flag — surfaced via `coverage_tier`. Redundant for CDE purposes. |
| `has_eada` | Coverage flag — surfaced via `coverage_tier`. Redundant for CDE purposes. |
| `coverage_tier` | Useful filter for downstream consumers but not a measure feeding regulatory or pentagon outputs. (Steward may revisit if MCP tools surface it.) |
| `institutional_support_per_fte` | Numerator-side context for `marketing_ratio`; the ratio is the aura input, not the raw component. |
| `instruction_per_fte` | Denominator-side context for `marketing_ratio`; same reasoning as above. |
| `total_athletic_expenses` | EADA raw measure; the per-FTE rate (`athletic_spend_per_fte`) is the aura input. |
| `total_athletic_revenue` | EADA raw measure; subsumed by `athletic_subsidy_ratio` for consumer use. |
| `athletic_revenue_per_fte` | Context column — symmetric pair of `athletic_spend_per_fte` but not an aura input and not a primary equity signal (subsidy ratio carries the equity meaning). |
| `aura_score_continuous` | Pre-rounding audit aid for `aura_score`. Tagging the rounded integer suffices; the continuous form is provenance-only. |
| `aura_score_version` | Schema-versioning provenance (`"v1"`). Not a measure. CON-AUR-012 P0 still gates correctness. |
| `aura_score_basis` | 5-value enum recording which input set produced the score. Necessary stratification key (per CON-AUR-030 EDA note) but not itself a measure. Steward may elevate to CDE in a follow-up if downstream stratification proves load-bearing. |

---

## Glossary Cross-References

Three BT-* terms proposed in §6 Business Glossary Terms (final IDs assigned by @bs:data-steward):

- **BT-AUR-AURA-SCORE** → tags `aura_score`
- **BT-AUR-COVERAGE-TIER** → tags `coverage_tier` (not CDE, but glossary-relevant)
- **BT-EAD-ATHLETIC-SUBSIDY-RATIO** → tags `athletic_subsidy_ratio`

Three additional BT-AUR-* terms proposed by this tagging (per §7 fp-architect issue #7 advisory — steward's call on adoption):

- **BT-AUR-MARKETING-RATIO** → tags `marketing_ratio`
- **BT-AUR-ENDOWMENT-PER-FTE** → tags `endowment_per_fte`
- **BT-AUR-ATHLETIC-SPEND-PER-FTE** → tags `athletic_spend_per_fte`
- **BT-AUR-ATHLETIC-FTE-SOURCE** → tags `athletic_fte_source` (methodological-provenance term — should explicitly call out the dual-FTE-definition stratification requirement in its definition)

---

## PII Disposition

Per `governance/pii-scans/consumable-institution-aura-pii-scan.md`: **NO PII DETECTED**. All 6 CDE columns are tier-Public with `is_pii: false`. No row-level security, no column masking required.

---

## Audit Trail Reference

Decision log: `governance/audit-trail/cde-tagging-consumable-institution-aura-2026-05-01.md` (to be written).
