# Audit Trail: Conceptual Model — silver-base-college-scorecard

**Agent:** @semantic-modeler
**Date:** 2026-04-06
**Mode:** Greenfield
**Stage:** 1 of 3 (Conceptual)
**Status:** PROPOSED — awaiting human approval

---

## Inputs Reviewed

| Input | Path | Key Takeaways |
|-------|------|---------------|
| Spec | docs/specs/silver-base-college-scorecard.md | Grain is unitid x cipcode x credlev. 17 fields in schema. CIP normalization, derived fields (cip_family, small_cohort_flag). md_earn_wne dropped. |
| Business Glossary | governance/business-glossary.json | 17 terms (BT-001 through BT-017), all approved. Full coverage of Silver schema fields. |
| EDA Report | governance/eda/raw-college-scorecard-eda.md | 69,947 rows, 2,559 institutions, 390 CIP codes. Privacy suppression drives 60-64% null rates on outcome fields. md_earn_wne confirmed 100% null. |
| Domain Context | governance/domain-context.md | Not accessible from current path; relied on spec and EDA for domain understanding. |

---

## Entity Identification Rationale

### Why 8 entities (not fewer)?

The source data is a single flat table, so a minimal model could be 1 entity (Program Offering) with all columns as attributes. The 8-entity model was chosen because:

1. **Institution, Academic Program, and Credential Type are distinct reference entities** that exist independently of any particular offering. They have their own identifiers and names. Normalizing them supports future Gold zone joins (e.g., institution-level aggregations).

2. **CIP Family is a classification hierarchy level** above Academic Program. It is derived (first 2 digits of CIP code) but represents a distinct business grouping used in downstream aggregation. Modeling it explicitly captures the hierarchy.

3. **Earnings Outcome and Debt Outcome are optionally present** due to privacy suppression. Making them separate entities with zero-or-one cardinality communicates that these are not guaranteed attributes -- they are conditional measurements governed by FERPA rules.

4. **Completions Measure drives a derived flag** (Small Cohort Flag) that determines whether outcome data is likely suppressed. Separating completions from the offering entity highlights this causal relationship.

### Alternatives Considered

| Alternative | Why Rejected |
|-------------|-------------|
| Single flat entity (Program Offering with all attributes) | Loses the business distinction between the offering itself and its optional outcomes. Does not capture the CIP hierarchy. Too implementation-focused for a conceptual model. |
| Separate entities for 1yr and 2yr earnings | Over-normalized. The two measurements are attributes of the same earnings concept (same entity, different time windows). Splitting them would imply they are fundamentally different business objects. |
| Time dimension entity for source_load_date | Premature. The dataset is a single-load snapshot. A time dimension adds complexity without current business value. Can be added if historical tracking is introduced. |
| Merging Completions into Program Offering | Considered, since completions always exist (one-to-one). Kept separate because completions serve a distinct role: they are the mechanism that determines privacy suppression and data confidence, not just another measure. |

---

## Data Patterns That Drove Decisions

| Pattern | Source | How It Influenced the Model |
|---------|--------|-----------------------------|
| 60-64% null rates on earnings/debt | EDA report | Led to modeling Earnings and Debt as optional entities (zero-or-one) rather than required attributes |
| 100% null on md_earn_wne | EDA report | Confirmed exclusion of this field from the model (dropped per spec) |
| 390 CIP codes in ~47 families | EDA report | Confirmed CIP Family as a meaningful grouping level worth modeling |
| Single credlev value (3) | EDA report | Kept Credential Type as an entity for extensibility despite MVP having only one value |
| Zero duplicate grains | EDA report | Confirmed the unitid x cipcode x credlev grain is naturally unique -- no dedup logic needed in the conceptual model |
| ipedscount1 < 30 correlates with suppression | EDA cross-field analysis | Validated the Small Cohort Flag concept and the causal link from Completions to outcome availability |

---

## Stage Progression

| Stage | Status | Date | Approver |
|-------|--------|------|----------|
| Conceptual (Stage 1) | PROPOSED | 2026-04-06 | Pending |
| Logical (Stage 2) | Not started | — | — |
| Physical (Stage 3) | Not started | — | — |

---

## Next Steps

If the conceptual model is APPROVED:
- Advance to Stage 2 (Logical Model) with entity attributes, keys, data domains, and normalization decisions
- Logical model will reference BT-XXX terms for every attribute

If REJECTED:
- Incorporate feedback and revise the conceptual model before re-proposing
